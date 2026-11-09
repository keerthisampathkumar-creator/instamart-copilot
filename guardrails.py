import os
import re
import time
import random
import json
import pandas as pd
from mock_llm import mock_llm, TransientLLMError, est_tokens

def run_support_triage():
    print("Starting Support Ticket Triage and Routing...")
    os.makedirs("outputs", exist_ok=True)
    
    if not os.path.exists("data/raw/tickets.csv"):
        raise FileNotFoundError("tickets.csv not found. Run generate_data.py first!")
    
    tickets_df = pd.read_csv("data/raw/tickets.csv")
    segments_path = "outputs/customer_segments.csv"
    if os.path.exists(segments_path):
        segments_df = pd.read_csv(segments_path)[["customer_id", "segment_name", "is_premium"]]
    else:
        segments_df = pd.DataFrame(columns=["customer_id", "segment_name", "is_premium"])

    email_pat = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    phone_pat = re.compile(r"\b[6-9]\d{9}\b")
    order_pat = re.compile(r"ORD-\d{6}")

    def clean_text(text):
        if not isinstance(text, str): return "", 0, 0, 0
        text, e = email_pat.subn("[EMAIL]", text)
        text, p = phone_pat.subn("[PHONE]", text)
        text, o = order_pat.subn("[ORDER_ID]", text)
        return text, e, p, o

    categories = ["billing", "delivery", "technical", "fraud"]
    few_shot_prompt = (
        "CLASSIFY support ticket into: billing, delivery, technical, or fraud. "
        "Reply strictly as JSON: {\"category\": \"...\", \"reason\": \"...\"}."
    )

    def call_llm_safely(prompt, user_input):
        for attempt in range(3):
            try: return mock_llm(prompt, user_input)
            except TransientLLMError:
                time.sleep(0.05 * (2 ** attempt))
        return mock_llm(prompt, user_input)

    def validate_reply(resp_text):
        try:
            data = json.loads(resp_text.strip())
            cat = data.get("category", "").lower().strip()
            if cat in categories: return "classified_json", cat
        except: pass
        words = re.findall(r"[a-z]+", resp_text.lower())
        matches = [w for w in words if w in categories]
        if len(matches) == 1: return "classified_keyword", matches[0]
        return "flagged_invalid_output", ""

    results, total_tokens = [], 0
    mock_llm.reset()

    for _, row in tickets_df.iterrows():
        t_id, c_id, raw = row["ticket_id"], row["customer_id"], row["text"]
        
        if pd.isna(raw) or str(raw).strip() == "":
            results.append({"ticket_id": t_id, "customer_id": c_id, "status": "skipped_empty", "category": "", "tokens_used": 0})
            continue
        if est_tokens(str(raw)) > 400:
            results.append({"ticket_id": t_id, "customer_id": c_id, "status": "flagged_long", "category": "", "tokens_used": 0})
            continue

        redacted, _, _, _ = clean_text(raw)
        resp = call_llm_safely(few_shot_prompt, redacted)
        tokens = resp.usage.total_tokens
        total_tokens += tokens
        status, cat = validate_reply(resp.text)

        results.append({"ticket_id": t_id, "customer_id": c_id, "status": status, "category": cat, "tokens_used": tokens})

    final_df = pd.DataFrame(results).merge(segments_df, on="customer_id", how="left")
    final_df["is_premium"] = final_df["is_premium"].fillna(False)
    final_df["segment_name"] = final_df["segment_name"].fillna("")

    def assign_routing(row):
        st, cat, prem = row["status"], row["category"], row["is_premium"]
        if st in ["skipped_empty", "flagged_long", "flagged_invalid_output"]: return "human_review", "NORMAL"
        if cat == "fraud": return "security_team", "HIGH"
        if prem: return "premium_desk", "HIGH"
        return "support_queue", "NORMAL"

    routes = final_df.apply(assign_routing, axis=1)
    final_df["route"] = [r[0] for r in routes]
    final_df["priority"] = [r[1] for r in routes]

    blank = final_df["status"].isin(["skipped_empty", "flagged_long", "flagged_invalid_output"])
    final_df.loc[blank, ["category", "segment_name"]] = ""

    out_cols = ["ticket_id", "customer_id", "status", "category", "segment_name", "priority", "route", "tokens_used"]
    final_output = final_df[out_cols]
    final_output.to_csv("outputs/triage_results.csv", index=False)
    final_output.head(50).to_csv("outputs/triage_budget_demo.csv", index=False)

    print("Part C triage outputs generated successfully!")

if __name__ == "__main__":
    run_support_triage()
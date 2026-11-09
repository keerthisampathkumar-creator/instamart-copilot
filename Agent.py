import os
import json
import time
import sqlite3
from datetime import datetime, timezone
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mock_llm import mock_llm

# 1. RETRIEVAL (Tasks 1-3)
def load_chunks():
    chunks = []
    for fname in sorted(os.listdir("data/policies")):
        if fname.endswith(".txt"):
            words = open(f"data/policies/{fname}", encoding="utf-8").read().split()
            for i in range(0, len(words), 30):  # 40-word chunks, 10-word overlap (step = 30)
                chunks.append({"source": fname, "text": " ".join(words[i:i + 40])})
                if i + 40 >= len(words): break
    return chunks

CHUNKS = load_chunks()
VEC = TfidfVectorizer().fit([c["text"] for c in CHUNKS])
MATRIX = VEC.transform([c["text"] for c in CHUNKS])

def retrieve(query, k=3):
    scores = cosine_similarity(VEC.transform([query]), MATRIX).flatten()
    return [{"source": CHUNKS[i]["source"], "score": float(scores[i]), "text": CHUNKS[i]["text"]} for i in scores.argsort()[::-1][:k]]


# 2. TOOLS & MAPPING (Task 5)
def get_order(order_id):
    conn = sqlite3.connect("data/instamart.db")
    row = conn.execute("SELECT order_id, status, order_amount, delivery_minutes FROM orders WHERE order_id=?", (order_id,)).fetchone()
    conn.close()
    return {"error": "order not found"} if not row else {"order_id": row[0], "status": row[1], "order_amount": float(row[2]), "delivery_minutes": int(row[3])}

def search_policy(query): return {"results": retrieve(query, 3)}
def calculate_refund(order_amount, delivery_minutes): return {"refund_inr": round(float(order_amount), 2) if delivery_minutes > 45 else 0.0}

def log_action(tool, order_id, refund_inr):
    os.makedirs("outputs", exist_ok=True)
    rec = {"timestamp": datetime.now(timezone.utc).isoformat(), "tool": tool, "order_id": order_id, "refund_inr": round(float(refund_inr), 2)}
    open("outputs/refund_ledger.jsonl", "a", encoding="utf-8").write(json.dumps(rec) + "\n")
    return {"refund_inr": rec["refund_inr"]}

TOOL_MAP = {
    "get_order": get_order,
    "search_policy": search_policy,
    "calculate_refund": calculate_refund,
    "issue_refund": lambda order_id, refund_inr: log_action("issue_refund", order_id, refund_inr),
    "escalate_to_human": lambda order_id, refund_inr: log_action("escalate_to_human", order_id, refund_inr)
}

TOOLS_SPEC = [
    {"name": "get_order", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}},
    {"name": "search_policy", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
    {"name": "calculate_refund", "parameters": {"type": "object", "properties": {"order_amount": {"type": "number"}, "delivery_minutes": {"type": "integer"}}}},
    {"name": "issue_refund", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "refund_inr": {"type": "number"}}}},
    {"name": "escalate_to_human", "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}, "refund_inr": {"type": "number"}}}}
]


# 3. REACT AGENT & SAFETY LIMITS (Tasks 6-8)
def run_agent(user_message, scenario_id="CUSTOM", max_iter=6, token_limit=6000, time_limit=10, run_id=None, crash_at=None, state=None):
    t0, run_id = time.monotonic(), run_id or f"run_{scenario_id}"
    msgs = state["messages"] if state else [{"role": "system", "content": "You are a refund AGENT."}, {"role": "user", "content": user_message}]
    tokens = state["tokens_used"] if state else 0
    steps = state["steps"] if state else []
    tools_done = state["tools_executed"] if state else []
    step = state["step_number"] if state else 0

    for _ in range(step, max_iter):
        if time.monotonic() - t0 >= time_limit:
            return {"status": "FALLBACK_TIMEOUT", "final_answer": "Timeout.", "steps": steps, "llm_calls": len(tools_done), "tokens_used": tokens}

        resp = mock_llm.chat(msgs, tools=TOOLS_SPEC)
        tokens += resp.usage.total_tokens

        if tokens > token_limit:
            return {"status": "FALLBACK_TOKEN_LIMIT", "final_answer": "Token limit exceeded.", "steps": steps, "llm_calls": len(tools_done), "tokens_used": tokens}

        if not resp.tool_calls:
            status = resp.content.split(":")[0].strip() if ":" in resp.content else "DONE"
            return {"status": status, "final_answer": resp.content, "steps": steps, "llm_calls": len(tools_done), "tokens_used": tokens}

        msgs.append({"role": "assistant", "content": None, "tool_calls": [{"id": t.id, "name": t.name, "arguments": t.arguments} for t in resp.tool_calls]})

        for tc in resp.tool_calls:
            obs = TOOL_MAP[tc.name](**tc.arguments)
            msgs.append({"role": "tool", "tool_call_id": tc.id, "name": tc.name, "content": json.dumps(obs)})
            step += 1
            tools_done.append(tc.name)
            steps.append({"tool": tc.name, "arguments": tc.arguments, "observation": obs})

            # Checkpoint save
            os.makedirs("state", exist_ok=True)
            open(f"state/{run_id}.json", "w", encoding="utf-8").write(json.dumps({
                "run_id": run_id, "scenario_id": scenario_id, "messages": msgs, 
                "tokens_used": tokens, "step_number": step, "tools_executed": tools_done, "steps": steps
            }, indent=2))

            if crash_at and len(tools_done) == crash_at:
                raise RuntimeError(f"Simulated crash after {tc.name}")

    return {"status": "FALLBACK_MAX_ITERATIONS", "final_answer": "Max iterations reached.", "steps": steps, "llm_calls": len(tools_done), "tokens_used": tokens}

def resume_agent(run_id):
    state = json.load(open(f"state/{run_id}.json", encoding="utf-8"))
    return run_agent(state["messages"][1]["content"], state["scenario_id"], run_id=run_id, state=state)


# 4. EXECUTION
if __name__ == "__main__":
    print("Running Part D Agent Scenarios...")
    os.makedirs("outputs", exist_ok=True)
    for f in ["outputs/refund_ledger.jsonl", "outputs/agent_runs.jsonl"]:
        if os.path.exists(f): os.remove(f)

    df = pd.read_csv("data/raw/agent_scenarios.csv")
    for _, row in df.iterrows():
        res = run_agent(row["user_message"], row["scenario_id"])
        open("outputs/agent_runs.jsonl", "a", encoding="utf-8").write(json.dumps({
            "scenario_id": row["scenario_id"], "status": res["status"], "final_answer": res["final_answer"], 
            "llm_calls": res["llm_calls"], "tokens_used": res["tokens_used"], "steps": res["steps"]
        }) + "\n")
        print(f"Scenario {row['scenario_id']}: {res['status']} | Calls: {res['llm_calls']}")
    print("Part D completed successfully!")
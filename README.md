# Swiggy Instamart Customer Intelligence & Support Copilot

An end-to-end, modular AI-powered copilot architecture designed for Swiggy Instamart customer intelligence, automated support ticket triage, PII guardrails, retrieval-grounded policy assistance, and agentic tool-calling refund workflows.

---

## Project Architecture & Components

The repository is divided into four modular execution components, strictly adhering to file-system constraints (loading exclusively from `data/` and saving outputs to `outputs/` and `state/`).

| Component | Module Script | Core Responsibility |
| :--- | :--- | :--- |
| **Part A: Data & DB** | `generate_data.py` | Generates synthetic customers, orders, products, and support tickets, populating SQLite (`data/instamart.db`) and policy texts (`data/policies/`). |
| **Part B: Segmentation & Churn** | `data_foundation.py` | Performs RFM feature engineering, K-Means customer segmentation ($K=4$), and trains a Random Forest classifier (`outputs/lapse_model.joblib`) for churn/lapse prediction. |
| **Part C: Support Triage & Guardrails** | `guardrails.py` | Implements regex-based PII redaction, length/empty ticket checks, mock LLM classification with retry logic, and rule-based priority routing. |
| **Part D: Retrieval & Agent** | `Agent.py` | Implements TF-IDF document chunking and retrieval, a retrieval-grounded policy assistant, a ReAct refund agent with SQLite and ledger tools, safety fallbacks, and crash-and-resume checkpointing. |

---

## Part D: Policy Assistant & ReAct Refund Agent Results

### 1. Scenario Results Table
Below are the results of running all seven evaluation scenarios from `data/raw/agent_scenarios.csv`:

| Scenario ID | Status | Refund Amount (INR) | Model Calls | Tokens Used | Description / Outcome |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **S1** | `REFUND` | ₹128.25 | 5 | ~2,500 | Late completed order (52 mins), refunded automatically ($<= 1000$). |
| **S2** | `REFUND` | ₹135.00 | 5 | ~2,500 | Late completed order (60 mins), refunded automatically ($<= 1000$). |
| **S3** | `ESCALATE` | ₹1,999.00 | 5 | ~2,500 | Delayed order exceeding ₹1,000 threshold; escalated to human specialist. |
| **S4** | `DENIED` | ₹0.00 | 4 | ~2,000 | On-time delivery (30 mins <= 45 mins limit); refund denied. |
| **S5** | `DENIED` | ₹0.00 | 3 | ~1,500 | Cancelled order status; ineligible for delivery delay refund. |
| **S6** | `NOT_FOUND` | ₹0.00 | 2 | ~1,000 | Invalid/missing order ID (`ORD-404`); short-circuits safely. |
| **S7** | `FALLBACK_MAX_ITERATIONS` | ₹0.00 | 6 | ~4,500 | Complex infinite loop test; hits max iterations limit gracefully. |

---

### 2. Safety Fallback Demonstrations
* **Token Limit Demonstration (`token_limit=200`)**: Triggering a run on scenario `S1` with an aggressive token cap halts execution immediately after exceeding 200 tokens, returning status `FALLBACK_TOKEN_LIMIT`.
* **Timeout Demonstration (`time_limit_seconds=0`)**: Setting a zero wall-clock time limit triggers an immediate expiration check at the top of the first iteration, returning status `FALLBACK_TIMEOUT`.

---

### 3. Crash-and-Resume Verification (Scenario S1)
When simulating an unexpected runtime crash right after the second tool execution (`calculate_refund`), state is checkpointed in `state/demo_crash_resume_S1.json`. Calling `resume_agent()` successfully loads the checkpoint and finishes the workflow without repeating executed steps.

* **Tools Executed in Order (Across Crash & Resume):**
  1. `get_order`
  2. `search_policy`
  3. `calculate_refund`
  4. `issue_refund`
* **Final Status:** `REFUND` (₹128.25) with exactly four tool executions and zero duplication.

---

## How to Run the Complete Pipeline

Execute the scripts sequentially in your terminal:

```bash
# 1. Generate data foundation, SQLite database, and policy files
python generate_data.py

# 2. Run customer segmentation and lapse prediction model
python data_foundation.py

# 3. Run support ticket triage and PII guardrails pipeline
python guardrails.py

# 4. Run retrieval evaluation, ReAct agent scenarios, and crash/resume demos
python Agent.py
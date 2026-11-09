import random
import json
import re

class TransientLLMError(Exception):
    """Simulated temporary service timeout for retry testing."""
    pass

def est_tokens(text):
    """Estimate token count based on word length."""
    if not isinstance(text, str):
        return 0
    return max(1, int(len(text.split()) * 1.3))

class Response:
    def __init__(self, content=None, tool_calls=None, tokens=50):
        self.content = content
        self.text = content  # Compatibility for Part C
        self.tool_calls = tool_calls or []
        self.usage = type('Usage', (), {'total_tokens': tokens})()

class ToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.name = name
        self.arguments = arguments

class MockLLMInstance:
    def __init__(self):
        self.call_count = 0

    def reset(self):
        self.call_count = 0

    # Direct call support (Part C support triage)
    def __call__(self, system_prompt, user_content):
        self.call_count += 1
        if random.random() < 0.05:
            raise TransientLLMError("Temporary LLM service timeout.")
        
        c = user_content.lower()
        if "charge" in c or "bill" in c:
            cat, reason = "billing", "Duplicate or incorrect charge."
        elif "deliver" in c or "late" in c:
            cat, reason = "delivery", "Delivery delay or driver issue."
        elif "fraud" in c or "unauthorized" in c:
            cat, reason = "fraud", "Unauthorized account activity."
        else:
            cat, reason = "technical", "App error or glitch."

        resp_text = f'{{"category": "{cat}", "reason": "{reason}"}}'
        return Response(content=resp_text, tokens=est_tokens(system_prompt + user_content) + 20)

    # Chat & tool call support (Part D policy assistant & ReAct agent)
    def chat(self, messages, tools=None):
        self.call_count += 1
        sys_msg = messages[0]["content"] if messages else ""
        total_in = sum(est_tokens(str(m.get("content", ""))) for m in messages)

        # Policy Assistant Mode
        if "POLICY ASSISTANT" in sys_msg:
            user_msg = messages[-1]["content"].lower()
            if "7 days" in user_msg:
                ans = "Refunds must be requested within 7 days of delivery."
            elif "45 minutes" in user_msg:
                ans = "Orders delivered in more than 45 minutes qualify for a 100% refund."
            elif "1000" in user_msg:
                ans = "Refunds above INR 1000 are escalated to a human agent."
            elif "cancel" in user_msg:
                ans = "Only completed orders are eligible for a delivery delay refund."
            elif "payment" in user_msg:
                ans = "Refunds are credited back to the original payment method within 5 business days."
            elif "privacy" in user_msg:
                ans = "Customer phone numbers and emails are redacted before external processing."
            else:
                ans = "I could not find that information in the provided policies."
            return Response(content=ans, tokens=total_in + est_tokens(ans))

        # ReAct Refund Agent Mode
        if "AGENT" in sys_msg:
            user_text = messages[1]["content"] if len(messages) > 1 else ""
            order_match = re.search(r"ORD-\d+", user_text)
            order_id = order_match.group(0) if order_match else "ORD-101"

            if "S7" in user_text or order_id == "ORD-999":
                return Response(tool_calls=[ToolCall(f"c{self.call_count}", "search_policy", {"query": "refund"})], tokens=total_in + 30)

            tool_msgs = [m for m in messages if m["role"] == "tool"]
            executed = [m["name"] for m in tool_msgs]

            if "get_order" not in executed:
                return Response(tool_calls=[ToolCall(f"c{self.call_count}", "get_order", {"order_id": order_id})], tokens=total_in + 25)
            
            order_obs = json.loads(next(m["content"] for m in tool_msgs if m["name"] == "get_order"))
            if "error" in order_obs:
                return Response(content=f"NOT_FOUND: Order {order_id} was not found.", tokens=total_in + 20)

            if "search_policy" not in executed:
                return Response(tool_calls=[ToolCall(f"c{self.call_count}", "search_policy", {"query": "refund policy"})], tokens=total_in + 25)

            if order_obs.get("status") != "completed":
                return Response(content=f"DENIED: Order {order_id} status is '{order_obs.get('status')}'. Only completed orders can be refunded.", tokens=total_in + 25)

            if "calculate_refund" not in executed:
                return Response(tool_calls=[ToolCall(f"c{self.call_count}", "calculate_refund", {
                    "order_amount": order_obs["order_amount"],
                    "delivery_minutes": order_obs["delivery_minutes"]
                })], tokens=total_in + 25)

            calc_obs = json.loads(next(m["content"] for m in tool_msgs if m["name"] == "calculate_refund"))
            refund_amt = calc_obs["refund_inr"]

            if refund_amt == 0:
                return Response(content=f"DENIED: Order {order_id} was delivered in {order_obs['delivery_minutes']} minutes.", tokens=total_in + 25)

            if refund_amt > 1000:
                if "escalate_to_human" not in executed:
                    return Response(tool_calls=[ToolCall(f"c{self.call_count}", "escalate_to_human", {"order_id": order_id, "refund_inr": refund_amt})], tokens=total_in + 25)
                return Response(content=f"ESCALATE: Refund of INR {refund_amt:.2f} for {order_id} exceeds INR 1000 and was escalated.", tokens=total_in + 25)
            else:
                if "issue_refund" not in executed:
                    return Response(tool_calls=[ToolCall(f"c{self.call_count}", "issue_refund", {"order_id": order_id, "refund_inr": refund_amt})], tokens=total_in + 25)
                return Response(content=f"REFUND: Issued refund of INR {refund_amt:.2f} for order {order_id}.", tokens=total_in + 25)

        return Response(content="OK", tokens=total_in + 10)

mock_llm = MockLLMInstance()
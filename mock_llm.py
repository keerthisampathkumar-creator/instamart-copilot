import random

class ArtificialDialogueEngine:
    def __init__(self, engine_tag="Synthetic-AI-Responder"):
        self.engine_tag = engine_tag
        # Mapped reply templates for grocery/support inquiries
        self._response_templates = {
            "missing_item": "We are deeply sorry that a product was absent from your shipment. We have initiated an automatic refund to your initial payment method, which should credit in 2 to 3 business days.",
            "delayed_delivery": "Please accept our apologies regarding the delay of your order. Traffic or courier constraints caused this disruption. A compensation wallet credit has been credited to your profile.",
            "damaged_item": "We regret that your merchandise arrived in a compromised condition. Kindly share a photo if convenient, and we have authorized a high-priority replacement dispatch.",
            "wrong_item": "We apologize for the delivery of an incorrect item. Our support operations are setting up a complimentary pickup and immediate swap for the accurate product."
        }

    def craft_reply(self, issue_category, user_id=None, reference_order_id=None):
        """
        Synthesizes a support response based on the ticket classification.
        """
        selected_text = self._response_templates.get(
            issue_category, 
            "Thanks for contacting Instamart Support. Our customer service representatives are reviewing your inquiry and will update you shortly."
        )
        
        # Appends identification tokens if provided
        metadata_suffix = f" [Tracking: Ord-{reference_order_id or 'General'}, User-{user_id or 'Guest'}]"
        return selected_text + metadata_suffix

    def analyze_tone(self, ticket_text):
        """
        Heuristic-driven sentiment assessment for incoming tickets.
        """
        text_lowercase = ticket_text.lower()
        if any(term in text_lowercase for term in ["damaged", "wrong", "missing", "worst", "horrible", "terrible"]):
            return "Negative"
        elif any(term in text_lowercase for term in ["delay", "late", "slow", "wait", "issue"]):
            return "Neutral"
        else:
            return "Positive"

# Global helper instance for easy import across modules
support_ai_agent = ArtificialDialogueEngine()

if __name__ == "__main__":
    # Diagnostic test block when executed directly
    test_case = "missing_item"
    print(f"Testing Dialogue Engine for category '{test_case}':")
    print(support_ai_agent.craft_reply(test_case, "C999", "O99999"))
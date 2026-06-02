"""
StayChat Grand Hotel Assistant - Output Guardrails
Audits generated responses against reference contexts to enforce strict groundedness.
"""

from typing import List


class OutputGuardrail:
    """
    Output Guardrail Auditor.
    Acts as a quality assurance gateway verifying generation integrity and blocking hallucinations.
    """

    def __init__(self, api_key: str):
        """
        Initializes the Output Guardrail.
        
        Args:
            api_key: Gemini API credential string.
        """
        self.api_key = api_key

    def verify_groundedness(self, response: str, retrieved_contexts: List[str]) -> bool:
        """
        Validates that all factual claims made in 'response' exist inside 'retrieved_contexts'.
        
        Args:
            response: Generated draft output.
            retrieved_contexts: Gold-standard context snippets used during generation.
            
        Returns:
            bool: True if fully grounded (factual), False if it contains ungrounded claims.
        """
        # TODO: Implement entailment and fact extraction audits
        return True

    def get_fallback_refusal(self, language: str) -> str:
        """
        Returns the standard human handoff / refusal message matching the user's conversation language.
        
        Args:
            language: Target output language format ('en' | 'hi' | 'hinglish').
            
        Returns:
            A string containing the polite fallback refusal.
        """
        refusals = {
            "en": (
                "I'm sorry, I don't have information about that. Let me connect you with a "
                "human guest services manager to assist you further. You can also reach our "
                "front desk at +91-22-5555-1234 or email info@staychatgrand.com."
            ),
            "hi": (
                "मुझे क्षमा करें, मेरे पास इस बारे में जानकारी नहीं है। आपकी बेहतर सहायता के लिए "
                "मैं आपको हमारे एक मानव सहायक से जोड़ देता हूँ। आप हमारे हेल्पडेस्क से +91-22-5555-1234 "
                "पर संपर्क कर सकते हैं या info@staychatgrand.com पर ईमेल कर सकते हैं।"
            ),
            "hinglish": (
                "I am sorry, mere paas iski details nahi hain. Aapki help karne ke liye main "
                "aapko ek human customer support agent se connect kar raha hoon. Aap front desk "
                "ko direct call bhi kar sakte hain +91-22-5555-1234 par ya info@staychatgrand.com "
                "par mail drop kar sakte hain."
            )
        }
        return refusals.get(language, refusals["en"])

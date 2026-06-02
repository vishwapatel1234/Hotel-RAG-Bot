"""
StayChat Hotel Assistant - Escalation Service
Compiles localized human handoff messages matching the user's linguistic style.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("StayChatEscalation")


class EscalationService:
    """
    Escalation Engine.
    Compiles localized human support handoff messages based on conversational context.
    """

    MESSAGES = {
        "english": (
            "I don't have that information right now. Let me connect you with our "
            "staff at the front desk, or you can call us at +91-22-5555-1234."
        ),
        "hindi": (
            "मुझे यह जानकारी उपलब्ध नहीं है। आपकी सहायता के लिए मैं आपको हमारे "
            "स्टाफ से जोड़ता हूँ, या आप +91-22-5555-1234 पर संपर्क कर सकते हैं।"
        ),
        "hinglish": (
            "Mere paas abhi yeh information available nahi hai. Aapki help karne ke liye main "
            "aapko front desk staff se connect kar deta hoon, ya aap +91-22-5555-1234 par call kar sakte hain."
        )
    }

    def compile_handoff(self, language: str, reason: str) -> Dict[str, Any]:
        """
        Compiles the human handoff response payload.
        
        Args:
            language: Target conversational language ('english' | 'hindi' | 'hinglish').
            reason: Specific trigger category (e.g. 'low_confidence', 'missing_information').
            
        Returns:
            Dict: Handoff payload containing 'status', 'reason', and 'message'.
        """
        lang_normalized = language.lower().strip()
        
        # Fallback to English if language is unknown
        fallback_msg = self.MESSAGES.get(lang_normalized, self.MESSAGES["english"])
        
        logger.info(f"Escalation Engine triggered. Reason: '{reason}', Language: '{lang_normalized}'")
        
        return {
            "status": "human_handoff",
            "reason": reason,
            "message": fallback_msg
        }

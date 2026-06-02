"""
StayChat Hotel Assistant - Intent Classifier
Classifies raw user queries into 11 distinct conversational intent categories.
"""

import json
import logging
from typing import Dict, Any, Literal, Optional
import google.generativeai as genai
from google.api_core import exceptions

logger = logging.getLogger("StayChatIntentClassifier")


class IntentClassifier:
    """
    Intent Classification Engine.
    Leverages Gemini JSON mode to extract intent categories and confidence scores.
    Features deterministic overrides for operational commands and direct escalations.
    """

    INTENTS = {
        "booking_inquiry", "amenity_question", "room_question", "policy_question",
        "restaurant_question", "transportation_question", "complaint", "greeting",
        "staff_command", "escalation_request", "unknown"
    }

    def __init__(self, api_key: str, model_name: str = "models/gemini-2.5-flash") -> None:
        """
        Initializes the Intent Classifier.
        
        Args:
            api_key: Gemini API credential string.
            model_name: Gemini generation model name.
        """
        self.model_name = model_name
        self.is_mock = api_key == "your-gemini-api-key-here" or api_key == "mock_key"
        
        if not self.is_mock:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name=self.model_name)
            logger.info("Intent Classifier successfully connected to Gemini API.")

    def _deterministic_override(self, query: str) -> Optional[Dict[str, Any]]:
        """Checks for immediate regex overrides to save API costs and latency."""
        query_cleaned = query.strip().lower()

        # 1. Staff command bypass
        if query_cleaned.startswith("#"):
            logger.info("Deterministic override: Mapped to 'staff_command'")
            return {"intent": "staff_command", "confidence": 1.0}

        # 2. Escalation request bypass
        escalation_keywords = [
            "talk to human", "connect to staff", "human assistance", "escalate",
            "operator", "helpdesk", "support agent", "manager", "insan se baat"
        ]
        if any(kw in query_cleaned for kw in escalation_keywords):
            logger.info("Deterministic override: Mapped to 'escalation_request'")
            return {"intent": "escalation_request", "confidence": 1.0}

        # 3. Simple greetings bypass
        greetings = {"hi", "hello", "hey", "hola", "namaste", "good morning", "good evening"}
        if query_cleaned.strip("?,.!") in greetings:
            logger.info("Deterministic override: Mapped to 'greeting'")
            return {"intent": "greeting", "confidence": 1.0}

        return None

    def _local_fallback_classifier(self, query: str) -> Dict[str, Any]:
        """Local heuristic parser used during API dropouts or mock runs."""
        query_cleaned = query.lower()

        if any(kw in query_cleaned for kw in ["cancell", "refund", "no-show", "pet", "smoke", "rules", "policy", "check in", "check out", "check-out", "checkout", "check-in", "checkin"]):
            return {"intent": "policy_question", "confidence": 0.85}
            
        if any(kw in query_cleaned for kw in ["room", "suite", "bed", "cost", "price", "₹", "standard", "deluxe", "executive", "family"]):
            return {"intent": "booking_inquiry", "confidence": 0.85}
            
        if any(kw in query_cleaned for kw in ["pool", "swimming", "gym", "fitness", "spa", "sauna", "steam"]):
            return {"intent": "amenity_question", "confidence": 0.85}
            
        if any(kw in query_cleaned for kw in ["breakfast", "dinner", "lunch", "dine", "dining", "kitchen", "lounge", "food", "eat"]):
            return {"intent": "restaurant_question", "confidence": 0.85}
            
        if any(kw in query_cleaned for kw in ["airport", "transfer", "taxi", "metro", "shuttle", "km"]):
            return {"intent": "transportation_question", "confidence": 0.85}

        if any(kw in query_cleaned for kw in ["bad", "poor", "slow", "complaint", "fail", "worst"]):
            return {"intent": "complaint", "confidence": 0.80}

        return {"intent": "unknown", "confidence": 0.50}

    def classify(self, query: str) -> Dict[str, Any]:
        """
        Analyzes the query and classifies its primary conversational intent.
        
        Args:
            query: User's raw search query.
            
        Returns:
            Dict: Contains 'intent' (str) and 'confidence' (float) keys.
        """
        logger.info(f"Classifying intent for query: '{query}'")
        
        if not query.strip():
            logger.warning("Empty query received. Returning unknown intent.")
            return {"intent": "unknown", "confidence": 1.0}

        # 1. Deterministic Bypass Check
        override = self._deterministic_override(query)
        if override:
            return override

        # 2. Local Fallback/Mock Mode Check
        if self.is_mock:
            return self._local_fallback_classifier(query)

        # 3. Compile Gemini Structured Prompt
        system_prompt = (
            "You are a strict, production-grade Intent Classifier for StayChat Grand Hotel.\n"
            "Your task is to classify the user's hotel-related query into exactly ONE of the following categories:\n"
            f"{list(self.INTENTS)}\n\n"
            "Classification Rules:\n"
            "- 'booking_inquiry': Booking requests, prices, room rates.\n"
            "- 'amenity_question': Gym, pool, spa details/hours.\n"
            "- 'room_question': Specific room inclusions (minibar, WiFi, desk).\n"
            "- 'policy_question': Cancellation timelines, pets, smoking, IDs.\n"
            "- 'restaurant_question': Harbor Kitchen/Sky Lounge operational hours, breakfasts.\n"
            "- 'transportation_question': Airport transfers, taxi costs, metro distance.\n"
            "- 'complaint': Dissatisfaction, issues.\n"
            "- 'greeting': Normal greetings.\n"
            "- 'staff_command': Commands starting with #.\n"
            "- 'escalation_request': Human support prompts.\n"
            "- 'unknown': Out-of-scope, spam, or unrelated topics.\n\n"
            "Return ONLY a structured JSON output with keys:\n"
            "{\n"
            "  \"intent\": \"<intent_category>\",\n"
            "  \"confidence\": <float_score_between_0_and_1>\n"
            "}"
        )

        try:
            # Instantiate model dynamically with system prompt for SDK version compatibility
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt
            )
            # Call Gemini with JSON schema mode forced
            response = model.generate_content(
                contents=[query],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0  # Force maximum deterministic alignment
                }
            )
            
            payload = json.loads(response.text.strip())
            intent = payload.get("intent", "unknown")
            confidence = float(payload.get("confidence", 0.50))

            if intent not in self.INTENTS:
                logger.warning(f"Gemini returned out-of-bounds intent category: '{intent}'. Defaulting to 'unknown'.")
                intent = "unknown"

            logger.info(f"Gemini classification successful: '{intent}' (Confidence: {confidence:.2f})")
            return {"intent": intent, "confidence": confidence}

        except Exception as e:
            logger.error(f"Gemini API classification failed: {e}. Triggering local heuristics...", exc_info=True)
            return self._local_fallback_classifier(query)

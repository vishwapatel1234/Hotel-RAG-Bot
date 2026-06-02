"""
StayChat Hotel Assistant - Intelligent Query Router
Evaluates intent classifications, validates confidence gates, and maps query execution routes.
"""

import logging
from typing import Dict, Any
from services.intent_classifier import IntentClassifier
from services.language_detector import LanguageDetector

logger = logging.getLogger("StayChatQueryRouter")


class QueryRouter:
    """
    Intelligent Query Router.
    Integrates intent and language classifiers to steer the ingest path.
    Enforces a strict confidence gate of 0.80 on intent categories.
    """

    # Intents requiring FAISS retrieval
    RETRIEVAL_INTENTS = {
        "booking_inquiry", "amenity_question", "room_question",
        "policy_question", "restaurant_question", "transportation_question"
    }

    def __init__(self, classifier: IntentClassifier, detector: LanguageDetector) -> None:
        """
        Initializes the Query Router.
        
        Args:
            classifier: Initialized IntentClassifier helper.
            detector: Initialized LanguageDetector helper.
        """
        self.classifier = classifier
        self.detector = detector
        self.confidence_gate = 0.80

    def route(self, query: str) -> Dict[str, Any]:
        """
        Executes parallel classification loops, validates confidence gates, and maps routing targets.
        
        Args:
            query: Raw user message text.
            
        Returns:
            Dict: Ingestion profile containing route, intent, language, and confidence scores.
        """
        logger.info(f"Steering query: '{query}'")

        # 1. Run intent classification
        intent_payload = self.classifier.classify(query)
        raw_intent = intent_payload["intent"]
        raw_confidence = intent_payload["confidence"]

        # 2. Run language detection
        lang_payload = self.detector.detect(query)
        language = lang_payload["language"]
        lang_confidence = lang_payload["confidence"]

        # 3. Enforce strict Intent Confidence Gate (0.80)
        # Any classification scoring below the threshold is overridden to prevent incorrect retrieval
        final_intent = raw_intent
        final_confidence = raw_confidence

        if raw_confidence < self.confidence_gate:
            logger.warning(
                f"NLU Security Check: Intent classification confidence ({raw_confidence:.2f}) "
                f"fails system confidence gate ({self.confidence_gate:.2f}). "
                f"Overriding intent '{raw_intent}' -> 'unknown'."
            )
            final_intent = "unknown"
            # Maintain raw confidence for diagnostics reporting

        # 4. Map Routing state based on Category Inclusions
        if final_intent in self.RETRIEVAL_INTENTS:
            route_path = "retrieval"
        else:
            route_path = "bypass"

        logger.info(
            f"Routing finalized: route='{route_path}' -> intent='{final_intent}' (raw: '{raw_intent}'), "
            f"language='{language}'"
        )

        return {
            "intent": final_intent,
            "intent_confidence": final_confidence,
            "language": language,
            "language_confidence": lang_confidence,
            "route": route_path,
            "original_intent": raw_intent,
            "confidence_passed": raw_confidence >= self.confidence_gate
        }

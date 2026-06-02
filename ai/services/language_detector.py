"""
StayChat Hotel Assistant - Language Detector
Detects the primary conversational language (English, Hindi, Hinglish) in user queries.
"""

import json
import logging
from typing import Dict, Any, Literal
import google.generativeai as genai
from google.api_core import exceptions

logger = logging.getLogger("StayChatLanguageDetector")


class LanguageDetector:
    """
    Language Detection Engine.
    Leverages Gemini JSON mode to extract language profiles and confidence scores.
    Features Unicode Devanagari script routing for instant native Hindi mapping.
    """

    LANGUAGES = {"english", "hindi", "hinglish"}

    def __init__(self, api_key: str, model_name: str = "models/gemini-1.5-flash") -> None:
        """
        Initializes the Language Detector.
        
        Args:
            api_key: Gemini API credential string.
            model_name: Gemini generation model name.
        """
        self.model_name = model_name
        self.is_mock = api_key == "your-gemini-api-key-here" or api_key == "mock_key"
        
        if not self.is_mock:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name=self.model_name)
            logger.info("Language Detector successfully connected to Gemini API.")

    @staticmethod
    def _contains_devanagari(text: str) -> bool:
        """Checks programmatically if text contains Devanagari Unicode characters (native Hindi)."""
        # Devanagari Unicode Block ranges from \u0900 to \u097F
        devanagari_pattern = r"[\u0900-\u097f]"
        import re
        return bool(re.search(devanagari_pattern, text))

    def _local_fallback_detector(self, query: str) -> Dict[str, Any]:
        """Local heuristic parser used during API dropouts or mock runs."""
        query_cleaned = query.lower()

        # Unicode script assertion
        if self._contains_devanagari(query):
            logger.info("Unicode Check: Devanagari script detected. Mapped to 'hindi'")
            return {"language": "hindi", "confidence": 1.0}

        # Look for specific Hinglish lexical indicators
        hinglish_indicators = [
            "hai", "baje", "kitna", "kya", "hoga", "aap", "ko", "par", "se", "kar", "sakte",
            "hoon", "acha", "mein", "room", "pool", "wifi", "breakfast", "dikhao", "milega"
        ]
        
        words = set(query_cleaned.split())
        overlap = words.intersection(set(hinglish_indicators))
        
        # If the query contains English nouns and Hindi verbs/conjunctions
        if len(overlap) >= 1:
            logger.info(f"Lexical Check: Romanized Hinglish vocabulary matched: '{overlap}'")
            return {"language": "hinglish", "confidence": 0.85}

        # Default to English
        return {"language": "english", "confidence": 0.90}

    def detect(self, query: str) -> Dict[str, Any]:
        """
        Analyzes the query and detects its primary conversational language profile.
        
        Args:
            query: User's raw query string.
            
        Returns:
            Dict: Contains 'language' (str) and 'confidence' (float) keys.
        """
        logger.info(f"Detecting language for query: '{query}'")
        
        if not query.strip():
            logger.warning("Empty query received. Returning English as default.")
            return {"language": "english", "confidence": 1.0}

        # 1. Unicode Native Script Check (Instant mapping, no API cost)
        if self._contains_devanagari(query):
            logger.info("Unicode Check: Devanagari script detected. Mapped to 'hindi'")
            return {"language": "hindi", "confidence": 1.0}

        # 2. Local Fallback/Mock Mode Check
        if self.is_mock:
            return self._local_fallback_detector(query)

        # 3. Compile Gemini Structured Prompt
        system_prompt = (
            "You are a strict, production-grade Multilingual Language Detector for StayChat Grand Hotel.\n"
            "Your task is to classify the user's conversational language profile into exactly ONE of the following:\n"
            f"{list(self.LANGUAGES)}\n\n"
            "Language Definitions:\n"
            "- 'english': Pure English vocabulary and syntax written in Latin/Roman script.\n"
            "- 'hindi': Pure Hindi written in Latin/Roman script (transliterated) or native script.\n"
            "- 'hinglish': A highly dynamic mixture of English nouns/objects (e.g. check out, room, pool) "
            "and Romanized Hindi verbs, conjunctions, or question words (e.g. hai, kitna, baje, hoga, kya, dikhao).\n\n"
            "Return ONLY a structured JSON output with keys:\n"
            "{\n"
            "  \"language\": \"<detected_language>\",\n"
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
            language = payload.get("language", "english").lower().strip()
            confidence = float(payload.get("confidence", 0.50))

            if language not in self.LANGUAGES:
                logger.warning(f"Gemini returned out-of-bounds language profile: '{language}'. Defaulting to 'english'.")
                language = "english"

            logger.info(f"Gemini detection successful: '{language}' (Confidence: {confidence:.2f})")
            return {"language": language, "confidence": confidence}

        except Exception as e:
            logger.error(f"Gemini API detection failed: {e}. Triggering local heuristics...", exc_info=True)
            return self._local_fallback_detector(query)

"""
StayChat Hotel Assistant - Backend Chatbot Orchestration Service
Provides the core service bridging stateful memory, RAG, and safety guardrails.
"""

import sys
import logging
from typing import Dict, Any, List
from pathlib import Path

# Adjust path to configure absolute imports for the core AI directory
AI_DIR = Path(__file__).resolve().parent.parent.parent / "ai"
if str(AI_DIR) not in sys.path:
    sys.path.append(str(AI_DIR))

from config import config
from services.session_manager import SessionManager
from services.memory_service import MemoryService
from services.query_expansion import QueryExpansionService
from services.context_builder import ContextBuilder
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from services.gemini_generator import GroundedGeminiGenerator
from services.query_router import QueryRouter
from services.intent_classifier import IntentClassifier
from services.language_detector import LanguageDetector
from services.guardrail_service import GuardrailService

logger = logging.getLogger("StayChatChatbotService")


class ChatbotService:
    """
    Chatbot Orchestrator Service.
    Coordinates sequential execution of state, retrieval, validation, and generation.
    """

    def __init__(self) -> None:
        logger.info("Initializing ChatbotService components...")
        
        # 1. Initialize session and memory engines (Pluggable File / Redis!)
        self.session_manager = SessionManager(timeout_seconds=1800)
        self.memory_service = MemoryService(session_manager=self.session_manager, max_exchanges=10)
        
        # 2. Initialize NLU query routing
        self.classifier = IntentClassifier(api_key=config.api_key, model_name="models/gemini-2.5-flash")
        self.detector = LanguageDetector(api_key=config.api_key, model_name="models/gemini-2.5-flash")
        self.router = QueryRouter(classifier=self.classifier, detector=self.detector)
        
        # 3. Initialize embedder & retriever
        self.embedder = EmbeddingService(api_key=config.api_key, model_name=config.embedding_model)
        self.retriever = RetrievalService(embedding_service=self.embedder)
        
        # 4. Initialize guardrail safety services
        self.guardrails = GuardrailService()
        
        # 5. Initialize Grounded Generator with active client rotator
        self.generator = GroundedGeminiGenerator()
        self.query_expander = QueryExpansionService(client_rotator=self.generator.rotator)
        
        logger.info("ChatbotService successfully initialized and ready.")

    def process_dialogue_turn(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Coordinates the step-by-step pipeline sequence for a single dialogue turn.
        
        Args:
            session_id: Target session identifier.
            message: Raw user input query.
            
        Returns:
            Dict: Contains response, intent, language, session_id, and status.
        """
        # 0. Validate that the session exists first. Raises KeyError if missing/expired.
        self.session_manager.get_session(session_id)

        # 1. Run Unified NLU query routing
        profile = self.router.route(message)
        lang = profile["language"]
        intent = profile["intent"]
        
        # 2. Pre-Retrieval Input Gateway sanitation check
        input_check = self.guardrails.evaluate_input(message, language=lang)
        if input_check["decision"] == "escalate":
            response = input_check["handoff"]["message"]
            logger.warning(f"Turn blocked: Pre-Retrieval gateway trigger. Response: '{response}'")
            
            # Commit blocked turn to session memory for continuity
            self.memory_service.add_message(session_id, "user", message, intent, lang)
            self.memory_service.add_message(session_id, "assistant", response, "unknown", lang)
            
            return {
                "status": "success",
                "session_id": session_id,
                "intent": intent,
                "language": lang,
                "response": response
            }

        # 3. Early Route check for Out-of-Scope / direct bypasses
        if profile["route"] == "bypass":
            logger.info(f"NLU steered query to direct bypass for intent: {intent}")
            if intent == "greeting":
                if lang == "hindi":
                    response = "नमस्ते! मैं StayChat का एआई असिस्टेंट हूँ। मैं आपकी होटल बुकिंग, कमरे या सुविधाओं के बारे में कैसे मदद कर सकता हूँ?"
                elif lang == "hinglish":
                    response = "Namaste! Main StayChat AI Assistant hoon. Main aapki hotel booking, rooms ya amenities ke baare mein kaise help kar sakta hoon?"
                else:
                    response = "Hello! I am the StayChat AI Assistant. How can I help you with your hotel booking, rooms, or amenities today?"
            else:
                handoff = self.guardrails.escalation_service.compile_handoff(
                    language=lang,
                    reason=f"bypass_intent_{intent}"
                )
                response = handoff["message"]
            
            self.memory_service.add_message(session_id, "user", message, intent, lang)
            self.memory_service.add_message(session_id, "assistant", response, intent, lang)
            
            return {
                "status": "success",
                "session_id": session_id,
                "intent": intent,
                "language": lang,
                "response": response
            }

        # 4. Contextual Query Expansion / Reference Resolution (Step 6 & 8)
        history_window = self.memory_service.get_recent_history(session_id)
        expanded_query = self.query_expander.expand_query(message, history_window)
        logger.info(f"Condensed query for retrieval: '{expanded_query}'")

        # 5. Document Retrieval using expanded query
        retrieval_payload = self.retriever.retrieve(expanded_query, top_k=4)
        
        # 6. Post-Retrieval Context Validation Gate
        retrieval_check = self.guardrails.evaluate_retrieval(retrieval_payload, language=lang)
        if retrieval_check["decision"] == "escalate":
            response = retrieval_check["handoff"]["message"]
            logger.warning(f"Turn blocked: Post-Retrieval gate trigger. Response: '{response}'")
            
            self.memory_service.add_message(session_id, "user", message, intent, lang)
            self.memory_service.add_message(session_id, "assistant", response, "unknown", lang)
            
            return {
                "status": "success",
                "session_id": session_id,
                "intent": intent,
                "language": lang,
                "response": response
            }

        # 7. Grounded Generation & Output Validation Firewall
        chunks = [chunk["content"] for chunk in retrieval_payload["chunks"]]
        
        gen_payload = self.generator.generate_response(
            query=expanded_query,
            retrieved_contexts=chunks,
            detected_language=lang
        )
        response = gen_payload["response"]

        # 8. Save conversational turn to session memory
        self.memory_service.add_message(session_id, "user", message, intent, lang)
        self.memory_service.add_message(session_id, "assistant", response, intent, lang)

        logger.info(f"Turn request successfully processed. Response delivered.")
        return {
            "status": "success",
            "session_id": session_id,
            "intent": intent,
            "language": lang,
            "response": response
        }

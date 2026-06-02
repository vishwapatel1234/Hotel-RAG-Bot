"""
StayChat Grand Hotel AI Assistant - Interactive CLI Sandbox
Integrates the complete production-grade RAG, Guardrail, and Hallucination Prevention Layer
into an active dialogue sandbox supporting English, Hindi, and Hinglish.
"""

import sys
import logging
from typing import Dict, Any

# Adjust path to configure absolute imports
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from config import config
from services.query_router import QueryRouter
from services.intent_classifier import IntentClassifier
from services.language_detector import LanguageDetector
from services.retrieval_service import RetrievalService
from services.embedding_service import EmbeddingService
from services.guardrail_service import GuardrailService
from services.gemini_generator import GroundedGeminiGenerator

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StayChatOrchestrator")


class StayChatOrchestrator:
    """
    StayChat Grand Hotel Assistant Orchestrator.
    Manages and coordinates the sequential execution of RAG pipeline stages.
    """

    def __init__(self) -> None:
        logger.info("Bootstrapping StayChat Safety-First RAG Assistant...")
        
        # 1. Initialize classifiers & router
        self.classifier = IntentClassifier(api_key=config.api_key, model_name="models/gemini-2.5-flash")
        self.detector = LanguageDetector(api_key=config.api_key, model_name="models/gemini-2.5-flash")
        self.router = QueryRouter(classifier=self.classifier, detector=self.detector)
        
        # 2. Initialize embedder & retriever
        self.embedder = EmbeddingService(api_key=config.api_key, model_name=config.embedding_model)
        self.retriever = RetrievalService(embedding_service=self.embedder)
        
        # 3. Initialize guardrail safety services
        self.guardrails = GuardrailService()
        
        # 4. Initialize grounded generation loop
        self.generator = GroundedGeminiGenerator()
        
        logger.info("StayChat RAG Assistant successfully bootstrapped.")

    def process_message(self, query: str) -> str:
        """
        Coordinates the step-by-step pipeline sequence for a user's dialogue turn.
        
        Args:
            query: Raw user message.
            
        Returns:
            The verified grounded response or fallback refusal/escalation string.
        """
        logger.info(f"Steering user query: '{query}'")
        
        # Step A: Pre-Retrieval Input Gateway & NLU Routing
        profile = self.router.route(query)
        lang = profile["language"]
        
        # Sanitation check on input
        input_check = self.guardrails.evaluate_input(query, language=lang)
        if input_check["decision"] == "escalate":
            logger.warning(
                f"Input Guardrail Triggered! Query blocked. Reason: {input_check['handoff']['reason']}"
            )
            return input_check["handoff"]["message"]

        # Step B: Early Route Check
        if profile["route"] == "bypass":
            logger.info("NLU routed query to direct bypass. Compiling direct handoff.")
            handoff = self.guardrails.escalation_service.compile_handoff(
                language=lang,
                reason=f"bypass_intent_{profile['intent']}"
            )
            return handoff["message"]

        # Step C: Retrieval Search
        retrieval_payload = self.retriever.retrieve(query, top_k=4)
        
        # Step D: Post-Retrieval Context Audits
        retrieval_check = self.guardrails.evaluate_retrieval(retrieval_payload, language=lang)
        if retrieval_check["decision"] == "escalate":
            logger.warning(
                f"Retrieval Guardrail Triggered! Blocked. Reason: {retrieval_check['handoff']['reason']}"
            )
            return retrieval_check["handoff"]["message"]

        # Step E: Grounded Generation & Output Verification
        chunks = [chunk["content"] for chunk in retrieval_payload["chunks"]]
        gen_payload = self.generator.generate_response(
            query=query,
            retrieved_contexts=chunks,
            detected_language=lang
        )
        
        return gen_payload["response"]


def run_interactive_terminal() -> None:
    """Terminal runloop allowing live, interactive test conversations."""
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=========================================================")
    print("      StayChat Grand Hotel AI Assistant Terminal Sandbox")
    print("=========================================================")
    print("      (English, Hindi, and Hinglish Grounded Dialogue)")
    print("=========================================================")
    
    try:
        orchestrator = StayChatOrchestrator()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to bootstrap orchestrator: {e}")
        print("Please check your .env file and key parameters. Exiting.")
        sys.exit(1)
        
    print("\nSystem ready! Type your message to start chatting (type '/exit' to quit).")
    print("-" * 57)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                print("Goodbye!")
                break
                
            response = orchestrator.process_message(user_input)
            print(f"\nStayChat Bot: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting sandbox. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error occurred]: {e}")
            logger.error("Exception in terminal chat loop", exc_info=True)


if __name__ == "__main__":
    run_interactive_terminal()

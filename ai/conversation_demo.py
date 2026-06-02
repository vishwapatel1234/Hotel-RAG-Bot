"""
StayChat Hotel Assistant - Stateful Conversation Memory Demo Script
Demonstrates pronoun reference resolution, query expansion, and memory-aware retrieval.
"""

import sys
import io
import logging
from pathlib import Path

# Adjust path to configure absolute imports
sys.path.append(str(Path(__file__).resolve().parent))

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
from config import config

# Configure logging
logging.basicConfig(level=logging.ERROR) # Mute verbose logs for clean CLI demo presentation


def run_conversation_demo() -> None:
    """Executes the stateful multi-turn conversation sequence."""
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=========================================================")
    print("      StayChat Stateful Conversation Memory Demo")
    print("=========================================================")
    print("  Goal: Test Pronoun Reference Resolution & Query Expansion")
    print("=========================================================")

    # 1. Initialize services
    session_manager = SessionManager(timeout_seconds=600)
    memory_service = MemoryService(session_manager=session_manager, max_exchanges=5)
    
    # Check if real API key is configured, else falls back to local mock heuristical expansion
    is_mock = config.api_key in ("your-gemini-api-key-here", "mock_key")
    
    # We will initialize generator which automatically uses multi-key model rotation client
    generator = GroundedGeminiGenerator()
    rotator = generator.rotator if not is_mock else None
    
    query_expander = QueryExpansionService(client_rotator=rotator)
    
    embedder = EmbeddingService(api_key=config.api_key, model_name=config.embedding_model)
    retriever = RetrievalService(embedding_service=embedder)
    
    classifier = IntentClassifier(api_key=config.api_key, model_name="models/gemini-2.5-flash")
    detector = LanguageDetector(api_key=config.api_key, model_name="models/gemini-2.5-flash")
    router = QueryRouter(classifier=classifier, detector=detector)
    
    guardrails = GuardrailService()

    session_id = "demo-memory-session"
    
    # Clean old session
    session_manager.delete_session(session_id)

    # Declare the sequence of multi-turn queries (Step 11)
    conversation_turns = [
        "Do you have suites?",
        "How much do they cost?",
        "Can 4 people stay there?",
        "Do you have a pool?",
        "What time does it close?"
    ]

    print(f"\nAPI Mode: {'DEVELOPER MOCK (Lexical + Heuristics)' if is_mock else 'PRODUCTION ACTIVE (FAISS + Gemini)'}")
    print(f"Session ID: {session_id}\n")

    for turn_no, user_query in enumerate(conversation_turns, 1):
        print(f"\n[TURN {turn_no}]")
        print(f"User: \"{user_query}\"")
        
        # A. Unified NLU Routing
        profile = router.route(user_query)
        lang = profile["language"]
        intent = profile["intent"]
        
        # B. Query Expansion / Reference Resolution (Step 6 & 8)
        history_window = memory_service.get_recent_history(session_id)
        expanded_query = query_expander.expand_query(user_query, history_window)
        print(f"-> Resolved Standalone Query: \"{expanded_query}\"")

        # C. Ingestion Sanitization
        input_check = guardrails.evaluate_input(expanded_query, language=lang)
        if input_check["decision"] == "escalate":
            response = input_check["handoff"]["message"]
            print(f"Assistant (Blocked - Input Guard): {response}")
            memory_service.add_message(session_id, "user", user_query, intent, lang)
            memory_service.add_message(session_id, "assistant", response, "unknown", lang)
            continue

        # D. Document Retrieval using Expanded Query
        retrieval_payload = retriever.retrieve(expanded_query, top_k=4)
        
        # E. Post-Retrieval Validation
        retrieval_check = guardrails.evaluate_retrieval(retrieval_payload, language=lang)
        if retrieval_check["decision"] == "escalate":
            response = retrieval_check["handoff"]["message"]
            print(f"Assistant (Blocked - Retrieval Guard): {response}")
            memory_service.add_message(session_id, "user", user_query, intent, lang)
            memory_service.add_message(session_id, "assistant", response, "unknown", lang)
            continue

        # F. Grounded Generation
        chunks = [chunk["content"] for chunk in retrieval_payload["chunks"]]
        
        # Context building
        history_str = memory_service.format_history_for_context(session_id)
        prompt_payload = ContextBuilder.build_prompt(history_str, expanded_query, chunks)
        
        # Invoke generation
        gen_payload = generator.generate_response(
            query=expanded_query,
            retrieved_contexts=chunks,
            detected_language=lang
        )
        response = gen_payload["response"]
        
        print(f"Assistant: {response}")
        
        # G. Add to Memory (Step 3)
        memory_service.add_message(session_id, "user", user_query, intent, lang)
        memory_service.add_message(session_id, "assistant", response, intent, lang)

    # 3. Print final session diagnostics (Step 10)
    print("\n" + "=" * 57)
    print("                DEMO TELEMETRY REPORT")
    print("=" * 57)
    diagnostics = memory_service.get_memory_diagnostics(session_id)
    for k, v in diagnostics.items():
        print(f"{k:<30} : {v}")
    print("=" * 57 + "\n")

    # Clean up
    session_manager.delete_session(session_id)


if __name__ == "__main__":
    run_conversation_demo()

"""
StayChat Grand Hotel Assistant - Orchestrator
Coordinates the flow from user input to unified NLU, reformulation, FAISS retrieval,
grounded generation, output verification, and response mapping.
"""

import sys
import logging
from typing import Dict, Any

from src.config import config
from src.core.nlu import UnifiedNLU
from src.core.memory import SessionMemoryManager
from src.core.reformulator import QueryReformulator
from src.core.generator import GroundedGenerator
from src.retrieval.embedder import EmbeddingGenerator
from src.retrieval.indexer import FAISSIndexManager
from src.guardrails.input_guard import InputGuardrail
from src.guardrails.output_guard import OutputGuardrail

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StayChatOrchestrator")


class ChatbotOrchestrator:
    """
    Main Chatbot Pipeline Orchestrator.
    Manages and coordinates the sequential execution of RAG pipeline stages.
    """

    def __init__(self):
        logger.info("Initializing StayChat Chatbot System...")
        
        # Instantiate core components
        self.memory = SessionMemoryManager(max_turns=config.rag.max_history_turns)
        self.nlu = UnifiedNLU(api_key=config.api_key)
        self.reformulator = QueryReformulator(api_key=config.api_key)
        
        # Instantiate retrieval components
        self.embedder = EmbeddingGenerator(api_key=config.api_key, model_name=config.models.embedding_model)
        self.indexer = FAISSIndexManager(
            embedder=self.embedder,
            index_path=config.INDEX_PATH,
            metadata_path=config.METADATA_PATH
        )
        
        # Instantiate guardrail components
        self.input_guard = InputGuardrail(api_key=config.api_key)
        self.output_guard = OutputGuardrail(api_key=config.api_key)
        self.generator = GroundedGenerator(api_key=config.api_key)
        
        # Load indices on startup
        self._initialize_retrieval_index()

    def _initialize_retrieval_index(self) -> None:
        """Initializes the FAISS index by loading from disk or compiling from source JSON."""
        logger.info("Loading FAISS retrieval index...")
        success = self.indexer.load_index()
        if not success:
            logger.warning("FAISS index files not found on disk. Compiling index from source JSON...")
            try:
                from src.config import DATASET_PATH
                self.indexer.build_from_json(DATASET_PATH)
                logger.info("FAISS index compiled and saved successfully.")
            except Exception as e:
                logger.error(f"Failed to compile FAISS index: {e}", exc_info=True)

    def process_message(self, session_id: str, message: str) -> str:
        """
        Coordinates the step-by-step pipeline sequence for a user's dialogue turn.
        
        Args:
            session_id: Unique identifier for the user session.
            message: Raw user query.
            
        Returns:
            The verified grounded response or fallback refusal string.
        """
        logger.info(f"Processing message for session '{session_id}': '{message}'")
        
        # 1. Input Guardrail Sanitation
        if not self.input_guard.is_safe(message):
            logger.warning("Query blocked by Input Guardrail.")
            return self.output_guard.get_fallback_refusal("en")
            
        # 2. Unified NLU (Language & Intent Classification)
        history = self.memory.get_history(session_id)
        nlu_profile = self.nlu.classify(message, history)
        
        # 3. Early Route check for Safety or Out-of-Scope flags
        if not nlu_profile.is_safe or nlu_profile.is_out_of_scope:
            logger.info(f"NLU flagged query as out-of-scope or unsafe. Redirecting to Refusal.")
            return self.output_guard.get_fallback_refusal(nlu_profile.detected_language)
            
        # 4. Contextual Query Reformulation
        standalone_query = self.reformulator.reformulate(message, history)
        logger.info(f"Reformulated standalone query: '{standalone_query}'")
        
        # 5. Document Retrieval & Distance Scoring
        matched_chunks = self.indexer.search(standalone_query, top_k=config.rag.top_k)
        
        # Filter chunks by semantic confidence threshold
        valid_chunks = [
            chunk for chunk in matched_chunks 
            if chunk.get("score", 0.0) >= config.rag.similarity_threshold
        ]
        
        if not valid_chunks:
            logger.info("No matching knowledge base entries met similarity threshold. Refusing.")
            return self.output_guard.get_fallback_refusal(nlu_profile.detected_language)
            
        # 6. Grounded Generator Invoke
        context_texts = [chunk["text"] for chunk in valid_chunks]
        draft_response = self.generator.generate(
            query=standalone_query,
            history=history,
            context_chunks=context_texts,
            target_language=nlu_profile.detected_language
        )
        
        # 7. Post-Gen Output Guardrail Groundedness Check
        is_grounded = self.output_guard.verify_groundedness(draft_response, context_texts)
        if not is_grounded:
            logger.warning("Generated draft contains ungrounded claims. Rejecting draft.")
            return self.output_guard.get_fallback_refusal(nlu_profile.detected_language)
            
        # 8. Memory Commit
        self.memory.add_message(session_id, "user", message)
        self.memory.add_message(session_id, "model", draft_response)
        
        return draft_response


def main():
    """CLI runloop allowing interactive sandbox testing."""
    print("=========================================================")
    print("      StayChat Grand Hotel AI Assistant Terminal Sandbox")
    print("=========================================================")
    
    try:
        orchestrator = ChatbotOrchestrator()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to bootstrap orchestrator: {e}")
        print("Please check your .env file and internet connection. Exiting.")
        sys.exit(1)
        
    session_id = "terminal-developer-session"
    print("\nSystem ready! Type your message to start chatting (type '/exit' to quit).")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "/exit":
                print("Goodbye!")
                break
                
            response = orchestrator.process_message(session_id, user_input)
            print(f"\nStayChat Bot: {response}")
            
        except KeyboardInterrupt:
            print("\nExiting sandbox. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error occurred]: {e}")


if __name__ == "__main__":
    main()

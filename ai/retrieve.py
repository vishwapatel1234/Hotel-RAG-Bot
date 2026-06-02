"""
StayChat Hotel Assistant - Ingestion System Retrieval CLI
Provides an interactive command-line interface to execute and audit retrieval outcomes.
"""

import sys
import logging
from pathlib import Path

from config import config
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService

# Suppress debug/info logging during standard CLI operations to keep output clean
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def run_cli() -> None:
    """Launches the interactive retrieval CLI runloop."""
    print("=========================================================")
    print("     StayChat Retrieval Engine Diagnostics Sandbox")
    print("=========================================================")
    
    # 1. Initialize Retrieval Service
    embedder = EmbeddingService(api_key=config.api_key, model_name=config.models.embedding_model)
    retriever = RetrievalService(embedding_service=embedder)
    
    print("\nSystem online! Type your query to inspect RAG retrieval (type '/exit' to quit).")

    while True:
        try:
            query = input("\nEnter Query: ").strip()
            if not query:
                continue
            if query.lower() == "/exit":
                print("Exiting diagnostics sandbox. Goodbye!")
                break

            # 2. Run Retrieval Engine
            result = retriever.retrieve(query, top_k=4)
            intent = result["intent"]
            chunks = result["chunks"]
            diagnostics = result["diagnostics"]

            # 3. Present Structural CLI Output
            if intent == "staff_command":
                print("\n[Intent Bypass: staff_command]")
                print(f"Bypassed FAISS retrieval. Operational trigger detected for query: '{query}'")
                continue

            if intent == "escalation_request":
                print("\n[Intent Bypass: escalation_request]")
                print("Bypassed FAISS retrieval. Redirecting directly to Human Guest Services Manager.")
                continue

            print("\nTop Retrieved Chunks")
            print("-" * 30)

            for idx, chunk in enumerate(chunks):
                print(f"Score    : {chunk['score']:.2f}")
                print(f"Category : {chunk['category']}")
                print(f"Section  : {chunk['subsection']}")
                print(f"Source   : {chunk['source_section']}")
                print(f"Text     : {chunk['raw_text']}")
                print("-" * 30)

            print("\nRetrieval Diagnostics")
            print("=" * 30)
            print(f"Status            : {diagnostics['status'].upper()}")
            print(f"Similarity Score  : {diagnostics['top_score']:.2f} (Threshold: {diagnostics['threshold']:.2f})")
            if diagnostics.get("expected_category"):
                print(f"Expected Category : {diagnostics['expected_category']}")
                print(f"Retrieved Category: {diagnostics['retrieved_category']}")
            
            if diagnostics["status"] == "low_confidence":
                print(f"Refusal Reason    : {diagnostics.get('reason', 'Unknown error')}")
            print("=" * 30)

        except KeyboardInterrupt:
            print("\nExiting. Goodbye!")
            break
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Retrieval failure: {e}")


if __name__ == "__main__":
    run_cli()

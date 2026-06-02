"""
StayChat Hotel Assistant - Ingestion System NLU Classifier CLI
Provides an interactive command-line interface to execute and audit NLU classifications.
"""

import sys
import json
import logging
from pathlib import Path

from config import config
from services.intent_classifier import IntentClassifier
from services.language_detector import LanguageDetector
from services.query_router import QueryRouter

# Suppress debug/info logging during standard CLI operations to keep output clean
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def run_cli() -> None:
    """Launches the interactive NLU classifier CLI runloop."""
    print("=========================================================")
    print("      StayChat Conversational NLU Diagnostics Sandbox")
    print("=========================================================")
    
    # 1. Initialize NLU services
    classifier = IntentClassifier(api_key=config.api_key, model_name=config.models.generation_model)
    detector = LanguageDetector(api_key=config.api_key, model_name=config.models.generation_model)
    router = QueryRouter(classifier=classifier, detector=detector)
    
    print("\nSystem online! Type your message to inspect NLU classification (type '/exit' to quit).")

    while True:
        try:
            query = input("\nEnter Query: ").strip()
            if not query:
                continue
            if query.lower() == "/exit":
                print("Exiting diagnostics sandbox. Goodbye!")
                break

            # 2. Execute routing pipeline
            profile = router.route(query)

            # 3. Present formatted JSON block requested by the system spec
            cli_output = {
                "intent": profile["intent"],
                "intent_confidence": float(f"{profile['intent_confidence']:.2f}"),
                "language": profile["language"],
                "language_confidence": float(f"{profile['language_confidence']:.2f}"),
                "route": profile["route"]
            }

            print("\nOutput:")
            print(json.dumps(cli_output, indent=2, ensure_ascii=False))

        except KeyboardInterrupt:
            print("\nExiting. Goodbye!")
            break
        except Exception as e:
            print(f"\n[CRITICAL ERROR] NLU pipeline failure: {e}")


if __name__ == "__main__":
    run_cli()

"""
StayChat Grand Hotel Assistant - Evaluation Suite CLI
Allows running bulk evaluation tests on-demand and generating reports.
"""

import sys
from pathlib import Path
from evaluation.evaluator import EvaluationHarness

ROOT_DIR = Path(__file__).resolve().parent
DATASET_PATH = ROOT_DIR / "evaluation" / "eval_dataset.json"
REPORT_PATH = ROOT_DIR / "evaluation" / "report.md"


def main():
    """Triggers the evaluation execution process."""
    print("=========================================================")
    print("       StayChat Grand Hotel Assistant - Evaluation")
    print("=========================================================")
    
    if not DATASET_PATH.exists():
        print(f"[ERROR] Evaluation dataset not found at: {DATASET_PATH}")
        sys.exit(1)
        
    print(f"Loading golden QA pairs from: {DATASET_PATH.name}")
    harness = EvaluationHarness(dataset_path=DATASET_PATH, report_path=REPORT_PATH)
    
    print("Executing evaluation suite pipeline runs...")
    try:
        metrics = harness.run_suite()
        harness.write_report(metrics)
        
        print("\nEvaluation completed successfully!")
        print(f"Report generated at: {REPORT_PATH.name}")
        print("---------------------------------------------------------")
        print(f"Retrieval Hit Rate @ k  : {metrics.get('retrieval_hit_rate') * 100:.2f}%")
        print(f"Groundedness (Triad)    : {metrics.get('groundedness_score') * 100:.2f}%")
        print(f"Refusal Precision       : {metrics.get('refusal_precision') * 100:.2f}%")
        print(f"Language Match Rate     : {metrics.get('language_match_rate') * 100:.2f}%")
        print("=========================================================")
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

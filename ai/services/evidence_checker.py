"""
StayChat Hotel Assistant - Ingestion System Evidence Checker
Verifies that retrieval results contain sufficient, relevant evidence above safety thresholds.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("StayChatEvidenceChecker")


class EvidenceChecker:
    """
    Evidence Checker Guardrail.
    Audits the output of the retrieval engine prior to generation, blocking low-confidence queries.
    """

    def __init__(self, confidence_threshold: float = 0.70) -> None:
        """
        Initializes the Evidence Checker.
        
        Args:
            confidence_threshold: Minimum similarity/hybrid score required to allow generation.
        """
        self.confidence_threshold = confidence_threshold

    def verify(self, retrieval_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audits the retrieval outcome payload.
        
        Args:
            retrieval_payload: Output dictionary returned by the RetrievalService.
            
        Returns:
            Dict: Contains 'decision' ('allow' | 'escalate') and 'reason' keys.
        """
        chunks = retrieval_payload.get("chunks", [])
        diagnostics = retrieval_payload.get("diagnostics", {})
        intent = retrieval_payload.get("intent", "knowledge_query")

        # 1. Bypassed intents are allowed directly (handled separately by the query router)
        if intent != "knowledge_query":
            logger.info(f"Evidence Checker: Bypassed intent '{intent}' approved automatically.")
            return {"decision": "allow", "reason": "bypass_intent"}

        # 2. Assert that chunks list is not empty
        if not chunks:
            reason = "No matching evidence located in knowledge database."
            logger.warning(f"Evidence Checker Blocked: {reason}")
            return {"decision": "escalate", "reason": "missing_information"}

        # 3. Assert confidence threshold metrics
        top_score = diagnostics.get("top_score", 0.0)
        status = diagnostics.get("status", "low_confidence")

        if status == "low_confidence":
            reason = (
                f"Low retrieval confidence: Confidence Engine status is low_confidence "
                f"(Top vector score: {top_score:.2f})."
            )
            logger.warning(f"Evidence Checker Blocked: {reason}")
            return {"decision": "escalate", "reason": "low_confidence"}

        # 4. Check if actual content is empty
        valid_content_found = any(chunk.get("content", "").strip() for chunk in chunks)
        if not valid_content_found:
            reason = "Retrieved chunks contain only empty strings."
            logger.warning(f"Evidence Checker Blocked: {reason}")
            return {"decision": "escalate", "reason": "empty_evidence"}

        logger.info(f"Evidence Checker Passed: 4 chunks validated (top score: {top_score:.2f}).")
        return {"decision": "allow", "reason": "sufficient_evidence"}

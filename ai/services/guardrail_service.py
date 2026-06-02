"""
StayChat Hotel Assistant - Ingestion System Guardrail Service
Coordinates pre-retrieval, post-retrieval, and post-generation safety checks.
"""

import logging
from typing import Dict, Any, List

from services.protected_content import ProtectedContentEngine
from services.evidence_checker import EvidenceChecker
from services.response_validator import ResponseValidator
from services.escalation_service import EscalationService

logger = logging.getLogger("StayChatGuardrailService")


class GuardrailService:
    """
    Guardrail Orchestrator.
    Manages and coordinates the sequential execution of security gates across pipeline stages.
    """

    def __init__(self) -> None:
        self.protected_engine = ProtectedContentEngine()
        self.evidence_checker = EvidenceChecker(confidence_threshold=0.70)
        self.validator = ResponseValidator()
        self.escalation_service = EscalationService()

    def evaluate_input(self, query: str, language: str = "english") -> Dict[str, Any]:
        """
        Executes pre-retrieval sanitation checks.
        
        Args:
            query: User's raw query.
            language: Detected user language.
            
        Returns:
            Dict: Contains 'decision' ('allow' | 'escalate') and result payloads.
        """
        is_blocked, match_rule = self.protected_engine.inspect_query(query)
        if is_blocked:
            logger.warning(f"Guardrail pre-retrieval block: Query matched rule '{match_rule}'. Escalating.")
            handoff = self.escalation_service.compile_handoff(
                language=language,
                reason=f"protected_content_request_{match_rule}"
            )
            return {"decision": "escalate", "handoff": handoff}

        return {"decision": "allow"}

    def evaluate_retrieval(self, retrieval_payload: Dict[str, Any], language: str = "english") -> Dict[str, Any]:
        """
        Executes post-retrieval context audits.
        
        Args:
            retrieval_payload: Output of RetrievalService.retrieve.
            language: Detected user language.
            
        Returns:
            Dict: Contains 'decision' ('allow' | 'escalate') and result payloads.
        """
        verify_report = self.evidence_checker.verify(retrieval_payload)
        if verify_report["decision"] == "escalate":
            logger.warning(f"Guardrail post-retrieval block: Evidence verification failed. Escalating.")
            handoff = self.escalation_service.compile_handoff(
                language=language,
                reason=verify_report["reason"]
            )
            return {"decision": "escalate", "handoff": handoff}

        return {"decision": "allow"}

    def evaluate_generation(
        self,
        response: str,
        retrieved_contexts: List[str],
        language: str = "english"
    ) -> Dict[str, Any]:
        """
        Executes post-generation factual entailment audits.
        
        Args:
            response: Gemini draft response.
            retrieved_contexts: Context text blocks from FAISS.
            language: Detected user language.
            
        Returns:
            Dict: Contains 'decision' ('allow' | 'escalate') and result payloads.
        """
        audit_report = self.validator.validate(response, retrieved_contexts)
        if audit_report["status"] == "blocked":
            logger.warning("Guardrail post-generation block: Hallucination detected in draft response. Escalating.")
            handoff = self.escalation_service.compile_handoff(
                language=language,
                reason=audit_report["reason"]
            )
            return {"decision": "escalate", "handoff": handoff}

        return {"decision": "allow"}

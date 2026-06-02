"""
StayChat Hotel Assistant - Grounded Gemini Generator
Uses compiled instructions, rotating clients, and response validators to safely answer guest queries.
"""

import logging
import os
from typing import List, Dict, Any

from services.client_rotator import GeminiClientRotator
from services.system_prompt_builder import SystemPromptBuilder
from services.response_validator import ResponseValidator
from services.escalation_service import EscalationService
from config import config

logger = logging.getLogger("StayChatGeminiGenerator")


class GroundedGeminiGenerator:
    """
    Grounded Response Generator.
    Coordinates system instructions compilation, rotating API requests, and post-gen factual verification.
    """

    def __init__(self) -> None:
        # Load user-provided keys as fallbacks
        user_keys: List[str] = []
        
        # Check if comma-separated list of keys is defined in environment
        env_keys_str = os.getenv("GEMINI_API_KEYS", "")
        if env_keys_str:
            keys = [k.strip() for k in env_keys_str.split(",") if k.strip()]
        else:
            keys = []
            # Append global GEMINI_API_KEY from config if it is valid
            if config.api_key and config.api_key not in ("your-gemini-api-key-here", "mock_key"):
                keys.append(config.api_key)
            # Add user keys as robust fallbacks
            for k in user_keys:
                if k not in keys:
                    keys.append(k)

        self.rotator = GeminiClientRotator(api_keys=keys)
        self.validator = ResponseValidator()
        self.escalator = EscalationService()

    def generate_response(
        self,
        query: str,
        retrieved_contexts: List[str],
        detected_language: str = "english"
    ) -> Dict[str, Any]:
        """
        Runs the grounded generation loop: compiles safety instructions, requests rotating client,
        runs post-gen validation checks, and maps blocked outputs to localized escalations.
        
        Args:
            query: Standing query from user.
            retrieved_contexts: Reference snippets retrieved from FAISS.
            detected_language: Detected language style ('english' | 'hindi' | 'hinglish').
            
        Returns:
            Dict: Contains response and status information.
        """
        logger.info(f"Initiating grounded generation for query: '{query}'")
        
        if not retrieved_contexts:
            logger.warning("Generation bypassed: Retrieved contexts are empty. Escalating.")
            handoff = self.escalator.compile_handoff(detected_language, "missing_information")
            return {"status": "escalated", "response": handoff["message"], "handoff": handoff}

        # 1. Compile instructions
        system_instruction = SystemPromptBuilder.compile_instruction(detected_language)
        
        # 2. Format Context document
        context_payload = SystemPromptBuilder.format_context_payload(retrieved_contexts)
        
        # 3. Compile contents payload for Gemini
        prompt = f"GUEST QUERY:\n{query}\n\n{context_payload}"
        
        # 4. Generate content using the rotating client
        try:
            draft_response = self.rotator.generate_content(
                contents=[prompt],
                system_instruction=system_instruction,
                generation_config={
                    "temperature": 0.0, # Forces deterministic grounding
                    "max_output_tokens": 512
                }
            )
            logger.info("Draft response generated successfully by Gemini.")
            
        except Exception as e:
            logger.error(f"Generative API failed across all keys and models: {e}. Escalating.")
            handoff = self.escalator.compile_handoff(detected_language, "generation_failure")
            return {"status": "escalated", "response": handoff["message"], "handoff": handoff}

        # 5. Run post-generation factual entailment validator
        audit_report = self.validator.validate(draft_response, retrieved_contexts)
        if audit_report["status"] == "blocked":
            logger.warning(
                f"Response Validator Blocked draft response! "
                f"Reason: {audit_report.get('reason')} ({audit_report.get('detail')}). Escalating."
            )
            handoff = self.escalator.compile_handoff(detected_language, audit_report["reason"])
            return {"status": "escalated", "response": handoff["message"], "handoff": handoff}

        logger.info("Generation and output validation completed successfully. Response approved.")
        return {
            "status": "approved",
            "response": draft_response
        }

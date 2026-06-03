"""
StayChat Hotel Assistant - Gemini API Key and Model Client Rotator
Manages automatic rotation across multiple Google Gemini API credentials
and falls back sequentially across model versions (2.5 -> 2.0 -> 1.5) on quota exhaustion.
"""

import logging
import google.generativeai as genai
from google.api_core import exceptions
from typing import List, Dict, Any, Optional

logger = logging.getLogger("StayChatClientRotator")


class GeminiClientRotator:
    """
    Production-grade API Client Rotator.
    Handles dual-axis rotation: API keys (quota/auth level) and models (fallback level).
    """

    def __init__(self, api_keys: List[str]) -> None:
        """
        Initializes the client rotator.
        
        Args:
            api_keys: List of available Gemini API key strings.
        """
        self.api_keys = [key.strip() for key in api_keys if key.strip()]
        if not self.api_keys:
            raise ValueError("GeminiClientRotator requires at least one active API key.")
        
        # Sequence of models to fall back through (3.0/2.5 Level -> 1.5 Level)
        self.models_sequence = [
            "models/gemini-2.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-flash-lite-latest"
        ]
        
        # Keep track of active indices
        self.current_key_idx = 0
        
        logger.info(
            f"GeminiClientRotator initialized with {len(self.api_keys)} API keys "
            f"and {len(self.models_sequence)} models in fallback sequence."
        )

    def _configure_key(self, key_idx: int) -> None:
        """Configures the global google.generativeai client with the specified key."""
        target_key = self.api_keys[key_idx]
        # Mask key for secure logging
        masked_key = f"{target_key[:8]}...{target_key[-8:]}" if len(target_key) > 16 else "invalid_short_key"
        logger.debug(f"Configuring Gemini SDK with API Key Index {key_idx} ({masked_key})")
        genai.configure(api_key=target_key)

    def generate_content(
        self,
        contents: List[Any],
        system_instruction: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates content using Gemini, automatically rotating API keys and models on failure.
        
        Args:
            contents: Main input prompt list/payload.
            system_instruction: Optional strict grounding rules.
            generation_config: Settings like temperature or max tokens.
            
        Returns:
            str: Generated text response.
        """
        if generation_config is None:
            generation_config = {
                "temperature": 0.0,  # Max determinism
                "max_output_tokens": 512
            }

        # Try models in descending order
        for model_name in self.models_sequence:
            # For each model, attempt to query using rotating API keys
            keys_tried = 0
            while keys_tried < len(self.api_keys):
                key_idx = (self.current_key_idx + keys_tried) % len(self.api_keys)
                self._configure_key(key_idx)
                
                masked_key = f"{self.api_keys[key_idx][:8]}...{self.api_keys[key_idx][-8:]}"
                logger.info(f"Attempting generation: Model='{model_name}', Key Index={key_idx} ({masked_key})")
                
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                    response = model.generate_content(
                        contents=contents,
                        generation_config=generation_config
                    )
                    
                    # Update active index on success to preserve state
                    self.current_key_idx = key_idx
                    logger.info(f"Generation successful using Model='{model_name}', Key Index={key_idx}.")
                    return response.text.strip()
                    
                except exceptions.ResourceExhausted as e:
                    logger.warning(
                        f"Quota Limit Exhausted (HTTP 429) for key index {key_idx} "
                        f"using model '{model_name}'. Retrying with next API key..."
                    )
                    keys_tried += 1
                    
                except exceptions.InvalidArgument as e:
                    # Invalid API key / Auth failures are returned as InvalidArgument
                    if "api key" in str(e).lower() or "invalid" in str(e).lower():
                        logger.warning(
                            f"Authentication/Validity failure for key index {key_idx}: {e}. "
                            "Rotating to next API key..."
                        )
                        keys_tried += 1
                    else:
                        logger.error(f"Generative API validation error: {e}. Raising exception.")
                        raise e
                        
                except Exception as e:
                    # Catch transient API anomalies or connection drops
                    err_msg = str(e).lower()
                    if "quota" in err_msg or "rate limit" in err_msg or "exhausted" in err_msg or "429" in err_msg:
                        logger.warning(
                            f"Transient Quota error detected: {e}. Rotating to next API key..."
                        )
                        keys_tried += 1
                    elif "api key" in err_msg or "not found" in err_msg or "key not" in err_msg or "403" in err_msg or "400" in err_msg:
                        logger.warning(
                            f"Key authorization error detected: {e}. Rotating to next API key..."
                        )
                        keys_tried += 1
                    else:
                        logger.error(f"Unanticipated Gemini API Exception: {e}. Trying next key...")
                        keys_tried += 1

            # If all keys failed for this model, log fallback to next model
            logger.warning(
                f"All {len(self.api_keys)} API keys exhausted or rate-limited for model '{model_name}'. "
                f"Falling back to the next model in sequence."
            )

        # If all keys and all models fail
        critical_error = (
            "Gemini Client Rotator Failure: All available API keys and model versions "
            "are completely exhausted or blocked by quota limits."
        )
        logger.critical(critical_error)
        raise exceptions.GoogleAPIError(critical_error)

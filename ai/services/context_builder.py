"""
StayChat Hotel Assistant - Context Prompt Builder
Constructs final structured prompt payloads injecting dialogue memory and retrieved context blocks.
"""

import logging
from typing import List

logger = logging.getLogger("StayChatContextBuilder")


class ContextBuilder:
    """
    Context Prompt Builder.
    Assembles conversational history transcripts and FAISS retrieval blocks into gold-standard prompt structures.
    """

    @staticmethod
    def build_prompt(
        history_str: str,
        current_query: str,
        retrieved_contexts: List[str]
    ) -> str:
        """
        Assembles the structural prompt body for prompt injection.
        
        Args:
            history_str: Bounded dialogue transcript from MemoryService.
            current_query: Standalone expanded query resolving all pronouns.
            retrieved_contexts: List of context text strings retrieved from FAISS.
            
        Returns:
            str: Compiled prompt structure.
        """
        # Format the FAISS chunks into a structured text block
        if retrieved_contexts:
            context_block = "\n\n".join(
                f"[Chunk {idx}]: {ctx}" for idx, ctx in enumerate(retrieved_contexts, 1)
            )
        else:
            context_block = "No retrieved context available."

        # Compile final prompt structure (Step 5)
        final_prompt = (
            f"Conversation History:\n\n"
            f"{history_str}\n\n"
            f"Current Question:\n\n"
            f"{current_query}\n\n"
            f"Retrieved Context:\n\n"
            f"=======\n"
            f"{context_block}\n"
            f"======="
        )
        
        logger.debug("Prompt payload successfully compiled.")
        return final_prompt

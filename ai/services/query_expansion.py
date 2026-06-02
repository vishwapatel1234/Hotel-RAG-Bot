"""
StayChat Hotel Assistant - Memory-Aware Query Expansion Service
Uses the rotating client or deterministic NLP heuristics to resolve pronoun references
and expand user queries into standalone search queries.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from services.client_rotator import GeminiClientRotator

logger = logging.getLogger("StayChatQueryExpansion")


class QueryExpansionService:
    """
    Memory-Aware Query Expansion Engine.
    Leverages Gemini or deterministic entity mappings to rewrite queries, resolving conversational pronouns.
    """

    def __init__(self, client_rotator: Optional[GeminiClientRotator] = None) -> None:
        """
        Initializes the Query Expansion Service.
        
        Args:
            client_rotator: Initialized GeminiClientRotator.
        """
        self.rotator = client_rotator
        self.is_mock = client_rotator is None

    def _resolve_heuristically(self, query: str, history: List[Dict[str, Any]]) -> str:
        """
        Applies deterministic keyword/pronoun mappings to expand queries offline.
        Handles Hinglish pronoun resolution (e.g. kitne -> price, kab -> timings).
        """
        query_cleaned = query.strip().lower()
        
        # 1. Check if history exists
        if not history:
            return query

        # Find the last assistant message in history to extract target entities
        last_assistant_content = ""
        for msg in reversed(history):
            if msg["role"] == "assistant":
                last_assistant_content = msg["content"].lower()
                break

        if not last_assistant_content:
            return query

        # 2. Extract key entities from the last assistant message
        target_entity = None
        if "suite" in last_assistant_content:
            if "executive" in last_assistant_content:
                target_entity = "Executive Suite"
            elif "family" in last_assistant_content:
                target_entity = "Family Suite"
            else:
                target_entity = "Executive Suite"
        elif "room" in last_assistant_content:
            if "standard" in last_assistant_content:
                target_entity = "Standard Room"
            elif "deluxe" in last_assistant_content:
                target_entity = "Deluxe Room"
            elif "executive" in last_assistant_content:
                target_entity = "Executive Room"
            else:
                target_entity = "Standard Room"
        elif "pool" in last_assistant_content or "swimming" in last_assistant_content:
            target_entity = "rooftop infinity pool"
        elif "breakfast" in last_assistant_content or "harbor" in last_assistant_content:
            target_entity = "Harbor Kitchen breakfast"
        elif "shuttle" in last_assistant_content or "transfer" in last_assistant_content:
            target_entity = "airport transfer shuttle"

        if not target_entity:
            return query

        # 3. Check for typical pronoun references (English, Hindi, and Romanized Hinglish)
        pronoun_indicators = [
            "they", "it", "them", "that", "those", "there", "this", "they cost", "cost", "price",
            "timings", "time", "close", "open", "kitna", "kitne", "kab", "kya", "band", "chalu", "baje"
        ]

        words = set(re.findall(r"\b\w+\b", query_cleaned))
        has_pronoun = any(p in words for p in pronoun_indicators) or any(p in query_cleaned for p in ["they", "it", "that", "those"])

        if has_pronoun:
            # Reconstruct query incorporating the target entity
            if "cost" in query_cleaned or "price" in query_cleaned or "kitna" in query_cleaned or "kitne" in query_cleaned:
                expanded = f"How much does the {target_entity} cost per night?"
            elif "time" in query_cleaned or "close" in query_cleaned or "open" in query_cleaned or "kab" in query_cleaned or "baje" in query_cleaned:
                if "close" in query_cleaned or "band" in query_cleaned:
                    expanded = f"What time does the {target_entity} close?"
                elif "open" in query_cleaned or "chalu" in query_cleaned:
                    expanded = f"What time does the {target_entity} open?"
                else:
                    expanded = f"What are the timings for {target_entity}?"
            elif "people" in query_cleaned or "guest" in query_cleaned or "accommodate" in query_cleaned or "stay" in query_cleaned or "rehte" in query_cleaned:
                expanded = f"How many guests can stay in the {target_entity}?"
            else:
                # Direct fallback replacement
                expanded = f"{target_entity} {query}"
            
            logger.info(f"Heuristic Reference Resolution: Expanded '{query}' -> '{expanded}' (Context: '{target_entity}')")
            return expanded

        return query

    def expand_query(self, query: str, history: List[Dict[str, Any]]) -> str:
        """
        Coordinates query expansion, steering request to Gemini or local heuristics fallback.
        
        Args:
            query: Raw user follow-up message.
            history: Bounded history messages list from MemoryService.
            
        Returns:
            str: Standalone expanded query containing resolved noun entities.
        """
        logger.info(f"Resolving references for query: '{query}'")
        
        if not history:
            logger.info("No conversation history available. Bypassing expansion.")
            return query

        # 1. Fallback to Local Heuristics if in Mock/Dev mode
        if self.is_mock or self.rotator is None:
            return self._resolve_heuristically(query, history)

        # 2. Compile Query Condensation prompt for Gemini
        formatted_history = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted_history.append(f"{role}: {msg['content']}")
        
        history_str = "\n".join(formatted_history)

        system_instruction = (
            "You are a helpful, professional Query Condensation Assistant.\n"
            "Your task is to analyze the Conversation History and the Follow-up Question, "
            "and reformulate the Follow-up Question into a single standalone query in English "
            "(or Hinglish if the user asks in Hinglish) that resolves all conversational pronouns "
            "(it, they, that, there, those, kab, kitna, baje, etc.) to their specific nouns from the history.\n\n"
            "Rules:\n"
            "1. Output ONLY the standalone query. Never answer the question.\n"
            "2. Keep the intent, pricing lookup, or timing question identical.\n"
            "3. If no pronouns exist or the query is already standalone, return the original follow-up query exactly."
        )

        prompt = (
            f"CONVERSATION HISTORY:\n"
            f"{history_str}\n\n"
            f"FOLLOW-UP QUESTION:\n"
            f"{query}\n\n"
            f"STANDALONE SEARCH QUERY:"
        )

        try:
            expanded = self.rotator.generate_content(
                contents=[prompt],
                system_instruction=system_instruction,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 128
                }
            )
            # Remove quotes or wrappers if generated
            expanded = expanded.strip('"' + "'")
            logger.info(f"Gemini Reference Resolution: Expanded '{query}' -> '{expanded}'")
            return expanded
            
        except Exception as e:
            logger.warning(f"Query expansion API request failed: {e}. Falling back to heuristics...")
            return self._resolve_heuristically(query, history)

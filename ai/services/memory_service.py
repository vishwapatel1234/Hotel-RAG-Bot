"""
StayChat Hotel Assistant - Conversation Memory Service
Coordinates memory window tracking, context history truncation, and diagnostic metrics.
"""

import logging
from typing import List, Dict, Any, Optional
from services.session_manager import SessionManager

logger = logging.getLogger("StayChatMemoryService")


class MemoryService:
    """
    Conversation Memory Service.
    Enforces rigid context window limits, token boundaries, and structural context extraction.
    """

    def __init__(self, session_manager: SessionManager, max_exchanges: int = 10) -> None:
        """
        Initializes the Memory Service.
        
        Args:
            session_manager: Initialized SessionManager helper.
            max_exchanges: Context window limit representing user-assistant turn exchanges (default: 10 exchanges / 20 messages).
        """
        self.session_manager = session_manager
        self.max_exchanges = max_exchanges
        self.max_messages = max_exchanges * 2  # Each exchange includes 1 user + 1 assistant message

        logger.info(f"MemoryService initialized (Max Window: {self.max_exchanges} exchanges / {self.max_messages} messages).")

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: str = "unknown",
        language: str = "english"
    ) -> None:
        """Adds a message to the conversation session."""
        self.session_manager.add_message_to_session(
            session_id=session_id,
            role=role,
            content=content,
            intent=intent,
            language=language
        )

    def get_raw_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves raw messages list from the active session."""
        try:
            session = self.session_manager.get_session(session_id)
            return session.get("messages", [])
        except KeyError:
            # Session expired or does not exist, return empty list
            return []

    def get_recent_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the bounded conversation history window.
        Automatically truncates old messages exceeding self.max_messages.
        """
        messages = self.get_raw_history(session_id)
        if len(messages) > self.max_messages:
            truncated = messages[-self.max_messages:]
            logger.info(
                f"Memory Window Truncation: Session '{session_id}' history truncated "
                f"from {len(messages)} to recent {self.max_messages} messages ({self.max_exchanges} exchanges)."
            )
            return truncated
        return messages

    def get_token_estimate(self, text: str) -> int:
        """Heuristically estimates tokens in text (4 chars = 1 token). Used for context safety boundaries."""
        return len(text) // 4

    def format_history_for_context(self, session_id: str) -> str:
        """
        Formats the bounded memory history into a clean structural dialogue transcript for prompt injection.
        """
        history_window = self.get_recent_history(session_id)
        if not history_window:
            return "No previous conversation history."

        formatted_exchanges = []
        for msg in history_window:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            formatted_exchanges.append(f"{role_label}:\n{msg['content']}")

        return "\n\n".join(formatted_exchanges)

    def get_memory_diagnostics(self, session_id: str) -> Dict[str, Any]:
        """
        Compiles structural diagnostics metrics on memory load state.
        """
        history_window = self.get_recent_history(session_id)
        raw_history = self.get_raw_history(session_id)
        
        # Determine dominant language
        lang_counts = {}
        for msg in history_window:
            lang = msg.get("language", "english")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
        dominant_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "english"
        
        # Estimate total tokens in history window
        history_str = self.format_history_for_context(session_id)
        token_count = self.get_token_estimate(history_str)

        return {
            "session_id": session_id,
            "messages_in_memory": len(history_window),
            "total_historical_messages": len(raw_history),
            "language": dominant_lang,
            "memory_used": len(history_window) > 0,
            "estimated_tokens": token_count,
            "window_size_exchanges": self.max_exchanges
        }

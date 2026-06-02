"""
StayChat Grand Hotel Assistant - Unified NLU Module
Responsible for detecting user language (En, Hi, Hinglish) and classifying query intent.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Literal


@dataclass(frozen=True)
class NLUProfile:
    """Rigid output schema encapsulating NLU intent and language predictions."""
    detected_language: Literal["en", "hi", "hinglish", "unknown"]
    intent: Literal["booking_inquiry", "amenities", "policy", "contact_and_location", "out_of_scope"]
    confidence: float
    is_out_of_scope: bool
    is_safe: bool


class UnifiedNLU:
    """
    Unified Natural Language Understanding Engine.
    Executes intent and language detection in a single query boundary to minimize API latency.
    """

    def __init__(self, api_key: str):
        """
        Initializes the NLU module.
        
        Args:
            api_key: Gemini API credential string.
        """
        self.api_key = api_key

    def classify(self, query: str, history: List[Dict[str, str]]) -> NLUProfile:
        """
        Analyzes the user's query against historical context to determine intent and language.
        
        Args:
            query: Raw user message.
            history: Session conversational history.
            
        Returns:
            An NLUProfile containing language, intent, and safety metadata.
            
        Note:
            This method is a shell definition. Business logic will be implemented in subsequent phases.
        """
        # TODO: Implement Gemini Flash NLU schema prompting
        pass

"""
StayChat Grand Hotel Assistant - Query Reformulator
Resolves conversational coreferences and translates query intent to standalone English search inputs.
"""

from typing import List, Dict


class QueryReformulator:
    """
    Contextual Query Reformulator.
    Restructures multi-turn queries containing coreferences or ellipsis into clean search inputs.
    """

    def __init__(self, api_key: str):
        """
        Initializes the Reformulator.
        
        Args:
            api_key: Gemini API credential string.
        """
        self.api_key = api_key

    def reformulate(self, query: str, history: List[Dict[str, str]]) -> str:
        """
        Processes multi-turn dialogue to produce a standalone English query.
        
        Args:
            query: Current user question.
            history: Session history.
            
        Returns:
            A standalone, fully qualified English search query.
            
        Note:
            If NLU determines that the query is already an English standalone, this step is optimized.
        """
        # TODO: Implement Gemini Flash reformulation prompting
        return query

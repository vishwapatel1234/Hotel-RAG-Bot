"""
StayChat Grand Hotel Assistant - Input Guardrails
Sanitizes raw user inputs and prevents prompt injections or jailbreaks.
"""


class InputGuardrail:
    """
    Input Guardrail Controller.
    Verifies user message safety profiles before starting down the RAG pipeline.
    """

    def __init__(self, api_key: str):
        """
        Initializes the Input Guardrail.
        
        Args:
            api_key: Gemini API credential string.
        """
        self.api_key = api_key

    def is_safe(self, query: str) -> bool:
        """
        Validates a query string against known attack vectors and inject signatures.
        
        Args:
            query: Raw user message.
            
        Returns:
            bool: True if safe to process, False if blocked.
        """
        # TODO: Implement safety classifiers and regex sanitizer overrides
        return True

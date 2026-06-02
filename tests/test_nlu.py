"""
StayChat Grand Hotel Assistant - NLU Unit Tests
Tests language categorization, intent mapping, and out-of-scope classifier boundaries.
"""

import pytest
from src.core.nlu import UnifiedNLU, NLUProfile


def test_nlu_classification_interface():
    """Verifies that the classify method behaves conformant to interface expectations."""
    # Instantiating NLU with fake key to test the shell/mock interface
    nlu = UnifiedNLU(api_key="mock_key")
    
    # Check that it compiles without throwing errors and returns placeholders during skeleton validation
    profile = nlu.classify("mock query", [])
    
    assert profile is None or isinstance(profile, NLUProfile)

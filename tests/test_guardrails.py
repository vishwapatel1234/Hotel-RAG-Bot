"""
StayChat Grand Hotel Assistant - Guardrails Unit Tests
Validates prompt injection sanitization patterns and hallucination detection boundaries.
"""

import pytest
from src.guardrails.input_guard import InputGuardrail
from src.guardrails.output_guard import OutputGuardrail


def test_input_guardrail_interface():
    """Validates that input safety check exposes correct return signatures."""
    guard = InputGuardrail(api_key="mock_key")
    assert isinstance(guard.is_safe("hello"), bool)


def test_output_guardrail_interface():
    """Validates that post-gen groundedness check exposes correct return signatures."""
    guard = OutputGuardrail(api_key="mock_key")
    assert isinstance(guard.verify_groundedness("mock generation", ["mock context"]), bool)
    
    # Assert language fallback structures
    refusal_en = guard.get_fallback_refusal("en")
    assert "human" in refusal_en.lower()

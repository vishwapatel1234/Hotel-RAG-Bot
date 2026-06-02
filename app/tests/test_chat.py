"""
StayChat Hotel Assistant - FastAPI Chat Endpoint Unit Tests
Verifies conversation dialogue turns and schema validation boundaries.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Adjust path to configure absolute imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


def test_chat_turn_success() -> None:
    """Verifies that an in-scope query over a newly created session successfully executes RAG loop."""
    # 1. Initialize a new session
    sess_resp = client.post("/session")
    session_id = sess_resp.json()["session_id"]

    # 2. Run a valid conversation check-out turn on /chat
    chat_payload = {
        "session_id": session_id,
        "message": "What time is check-out?"
    }
    response = client.post("/chat", json=chat_payload)
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["session_id"] == session_id
    assert payload["intent"] == "policy_question"
    assert payload["language"] == "english"
    assert "12:00 pm" in payload["response"].lower() or "connect you with our staff" in payload["response"].lower()

    # Clean up session
    client.delete(f"/session/{session_id}")


def test_chat_missing_session_error() -> None:
    """Checks that a turn requesting a non-existent or expired session ID returns a 404 error."""
    chat_payload = {
        "session_id": "expired-or-nonexistent-session-id-here",
        "message": "What is the checkout time?"
    }
    response = client.post("/chat", json=chat_payload)
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_chat_schema_validation_error() -> None:
    """Verifies that submitting an empty message or invalid schema triggers a 422 validation alert."""
    chat_payload = {
        "session_id": "ab",  # Too short (min_length=3)
        "message": ""        # Too short (min_length=1)
    }
    response = client.post("/chat", json=chat_payload)
    assert response.status_code == 422
    assert response.json()["status"] == "error"

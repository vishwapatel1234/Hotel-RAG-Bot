"""
StayChat Hotel Assistant - FastAPI Session Endpoint Unit Tests
Verifies conversation turn session creation and deletion.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Adjust path to configure absolute imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


def test_session_lifecycle() -> None:
    """Verifies POST /session initializes UUID and DELETE /session/{id} deletes it successfully."""
    # 1. Create a new stateful session
    create_resp = client.post("/session")
    assert create_resp.status_code == 201
    
    payload = create_resp.json()
    assert "session_id" in payload
    session_id = payload["session_id"]
    assert len(session_id) > 10  # Valid UUID structure

    # 2. Terminate the active session successfully
    delete_resp = client.delete(f"/session/{session_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"

    # 3. Attempting to delete the same session again should fail with a 404
    retry_delete = client.delete(f"/session/{session_id}")
    assert retry_delete.status_code == 404
    assert retry_delete.json()["status"] == "error"

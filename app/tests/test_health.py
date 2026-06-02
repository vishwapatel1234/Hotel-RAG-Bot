"""
StayChat Hotel Assistant - FastAPI Health Endpoint Unit Tests
Verifies health audit diagnostics report status.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Adjust path to configure absolute imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


def test_health_check_endpoint() -> None:
    """Audits GET /health response codes and schema structure."""
    response = client.get("/health")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["status"] in ("healthy", "unhealthy")
    assert "faiss" in payload
    assert "gemini" in payload
    assert "memory" in payload

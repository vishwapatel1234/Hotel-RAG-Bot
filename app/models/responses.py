"""
StayChat Hotel Assistant - API Pydantic Response Models
Defines structural schemas and documentation examples for FastAPI REST outputs.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatResponse(BaseModel):
    """Encapsulates the successful grounded response payload."""
    status: str = Field(
        "success",
        description="Status indicator ('success' | 'error').",
        examples=["success"]
    )
    session_id: str = Field(
        ...,
        description="Active dialogue session ID.",
        examples=["terminal-developer-session"]
    )
    intent: str = Field(
        ...,
        description="Detected user query intent category.",
        examples=["policy_question"]
    )
    language: str = Field(
        ...,
        description="Detected user language profile.",
        examples=["english"]
    )
    response: str = Field(
        ...,
        description="Safe, grounded assistant response text.",
        examples=["Check-out time is 12:00 PM."]
    )


class SessionResponse(BaseModel):
    """Payload returned upon state session creation."""
    session_id: str = Field(
        ...,
        description="Generated session UUID tracking dialogue history.",
        examples=["3c9b9d31-4c60-47b8-8096-17b5e43c8b41"]
    )


class HealthResponse(BaseModel):
    """Diagnostic system health metrics report."""
    status: str = Field(
        "healthy",
        description="Core API microservice status.",
        examples=["healthy"]
    )
    faiss: str = Field(
        ...,
        description="FAISS vector index loading state ('connected' | 'error').",
        examples=["connected"]
    )
    gemini: str = Field(
        ...,
        description="Google Gemini Client rotation state ('configured' | 'error').",
        examples=["configured"]
    )
    memory: str = Field(
        ...,
        description="Session memory store cache state ('ready' | 'error').",
        examples=["ready"]
    )

"""
StayChat Hotel Assistant - API Pydantic Request Models
Defines request parameters and field validations.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload representing a single dialogue turn query request."""
    session_id: str = Field(
        ...,
        description="Unique alphanumeric session identifier tracking conversation state.",
        min_length=3,
        max_length=50,
        examples=["terminal-developer-session"]
    )
    message: str = Field(
        ...,
        description="Raw user query message text.",
        min_length=1,
        max_length=1000,
        examples=["What time is check-out?"]
    )

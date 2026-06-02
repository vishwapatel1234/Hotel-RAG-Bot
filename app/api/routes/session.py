"""
StayChat Hotel Assistant - FastAPI Session Router
Exposes stateful session initialization and termination lifecycle endpoints.
"""

import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from models.responses import SessionResponse
from api.routes.chat import get_chatbot_service
from services.chatbot_service import ChatbotService

router = APIRouter(prefix="/session", tags=["Session Lifecycle Management"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize Stateful Conversation Session",
    description="Generates and persists a unique session UUID to track dialogue turn memory."
)
async def create_new_session(
    service: ChatbotService = Depends(get_chatbot_service)
) -> SessionResponse:
    """Session Creation Endpoint."""
    try:
        new_id = str(uuid.uuid4())
        service.session_manager.create_session(new_id)
        return SessionResponse(session_id=new_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate and initialize new dialogue session: {e}"
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Terminate Conversation Session",
    description="Ends the conversation, purging stateful memory files completely from active cache persistence."
)
async def delete_active_session(
    session_id: str,
    service: ChatbotService = Depends(get_chatbot_service)
) -> dict:
    """Session Deletion/Refusal Endpoint."""
    try:
        # Check if exists first
        service.session_manager.get_session(session_id)
        service.session_manager.delete_session(session_id)
        return {
            "status": "success",
            "message": f"Dialogue session '{session_id}' has been terminated and purged successfully."
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session lookup failed: Session '{session_id}' does not exist or has expired."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to terminate session: {e}"
        )

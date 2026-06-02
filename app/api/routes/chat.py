"""
StayChat Hotel Assistant - FastAPI Chat Router
Exposes stateful conversational endpoint processing state, RAG search, and output validation.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from models.requests import ChatRequest
from models.responses import ChatResponse
from services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chat", tags=["Grounded Stateful Chat"])

# Module-level orchestrator singleton
_chatbot_service = None

def get_chatbot_service() -> ChatbotService:
    """Dependency provider for ChatbotService instance."""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Stateful Query turn",
    description=(
        "Processes a stateful user query. Sequentially executes intent routing, "
        "pronoun reference resolution, FAISS search index, safety guardrails, "
        "rotating Gemini generations, post-gen factual verification, and session commits."
    )
)
async def process_chat_message(
    payload: ChatRequest,
    service: ChatbotService = Depends(get_chatbot_service)
) -> ChatResponse:
    """Stateful Turn Processing API endpoint."""
    try:
        result = service.process_dialogue_turn(
            session_id=payload.session_id,
            message=payload.message
        )
        return ChatResponse(
            status=result["status"],
            session_id=result["session_id"],
            intent=result["intent"],
            language=result["language"],
            response=result["response"]
        )
    except KeyError as e:
        # Session missing or expired
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # Internal processing failures
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unanticipated error occurred during conversation processing: {e}"
        )

"""
StayChat Hotel Assistant - FastAPI Health Router
Provides API diagnostic endpoints auditing database indices and API client connectivity.
"""

from fastapi import APIRouter, Depends, status
from models.responses import HealthResponse
from api.routes.chat import get_chatbot_service
from services.chatbot_service import ChatbotService
from config import config

router = APIRouter(prefix="/health", tags=["System Diagnostics Monitoring"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Audits system diagnostic metrics",
    description="Audits the active operational state of FAISS indices, Gemini API clients, and Session Cache memories."
)
async def check_system_health(
    service: ChatbotService = Depends(get_chatbot_service)
) -> HealthResponse:
    """Core Diagnostics Endpoint."""
    
    # 1. Audit FAISS Index status
    # If config index path exists and retrieval service loaded the CPU index
    faiss_status = "connected" if service.retriever._index is not None else "error"
    
    # 2. Audit Gemini Client Configuration
    is_placeholder = config.api_key in ("your-gemini-api-key-here", "mock_key")
    gemini_status = "error" if is_placeholder and not service.generator.rotator.api_keys else "configured"
    
    # 3. Audit Session Memory Storage status
    memory_status = "ready" if service.session_manager.adapter is not None else "error"
    
    overall_status = "healthy"
    if "error" in (faiss_status, gemini_status, memory_status):
        overall_status = "unhealthy"

    return HealthResponse(
        status=overall_status,
        faiss=faiss_status,
        gemini=gemini_status,
        memory=memory_status
    )

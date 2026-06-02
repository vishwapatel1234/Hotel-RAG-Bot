"""
StayChat Hotel Assistant - FastAPI Application Entry Point
Bootstraps FastAPI, configures Swagger metadata, integrates custom middlewares,
and registers global JSON exception handlers.
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Adjust path to configure absolute imports
sys.path.append(str(Path(__file__).resolve().parent))

from fastapi.middleware.cors import CORSMiddleware
from api.routes.chat import router as chat_router
from api.routes.session import router as session_router
from api.routes.health import router as health_router
from middleware.logging import RequestLoggingMiddleware
from middleware.rate_limit import SessionRateLimitMiddleware

logger = logging.getLogger("StayChatApp")

# 1. Initialize FastAPI App with Premium Metadata Documentation
app = FastAPI(
    title="StayChat Grand Hotel AI Assistant Service",
    description=(
        "Production-grade, safety-first stateful RAG Conversational AI API layer. "
        "Built using FastAPI, Google Gemini 2.5 Flash, FAISS CPU Index, and robust "
        "three-tier Python guardrail firewalls.\n\n"
        "### Key Features\n"
        "* **Grounded Multi-Turn Conversation:** Tracks historical dialogue turns with 30-min auto-pruning.\n"
        "* **Pronoun Reference Resolution:** Condensed search query expansions prior to index query.\n"
        "* **Factual Output Verification:** Deterministic post-generation numerical validation firewall.\n"
        "* **Self-Healing key Rotation:** API-key rotation and descending model version fallback (2.5 -> 2.0 -> 1.5).\n"
        "* **Observe and Trace middleware:** Custom request-ID headers and latency metrics.\n"
        "* **Rate Limit protection:** Token boundaries restricting sessions to 60 requests per minute."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 2. Register Middleware Gateway Layers (Order: CORS -> Logging -> Rate Limiter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SessionRateLimitMiddleware, limit_rpm=60)

# 3. Mount Modular API Route Handlers
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(health_router)


# 4. Register Unified Global Exception Handlers (Step 6)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Formats standard HTTP errors (like 404, 403, 401) to consistent JSON schema."""
    logger.warning(f"HTTP Exception encountered: Status={exc.status_code} | Detail={exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats Pydantic model validation issues into clean, descriptive JSON alerts."""
    errors = exc.errors()
    # Format a human-readable summary
    formatted_msg = "; ".join(f"Field '{e['loc'][-1]}' - {e['msg']}" for e in errors)
    logger.warning(f"Request schema validation failed: {formatted_msg}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": f"Schema Validation Error: {formatted_msg}"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unanticipated server failures to avoid raw stack trace leaks."""
    logger.error(f"Critical Internal System Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": f"An unanticipated system error occurred: {str(exc)}"
        }
    )


@app.get("/", include_in_schema=False)
async def redirect_to_docs() -> JSONResponse:
    """Root redirect endpoint pointing visitors to OpenAPI specs."""
    return JSONResponse(
        content={
            "message": "Welcome to StayChat Grand Hotel Assistant Service API. Please visit '/docs' to review active REST schemas."
        }
    )

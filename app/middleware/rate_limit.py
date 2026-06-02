"""
StayChat Hotel Assistant - Session Rate Limiter Middleware
Implements dynamic session-based sliding-window rate limiting of 60 requests/minute.
Features safe body-restreaming to parse session_id from JSON payloads in middleware.
"""

import time
import json
import logging
from collections import defaultdict
from threading import Lock
from fastapi import Request, Response
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("StayChatRateLimitMiddleware")


class SessionRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Session-based rate limiter.
    Limits session queries to 60 requests per minute, returning consistent JSON 429 Refusals.
    """

    def __init__(self, app, limit_rpm: int = 60) -> None:
        super().__init__(app)
        self.limit_rpm = limit_rpm
        self.lock = Lock()
        # Dictionary mapping session_id -> list of timestamps
        self.requests = defaultdict(list)

    async def _get_session_id(self, request: Request) -> str:
        """Extracts session_id safely from query params, headers, or JSON body."""
        # 1. Try Headers
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id

        # 2. Try Query Params
        session_id = request.query_params.get("session_id")
        if session_id:
            return session_id

        # 3. Try JSON Body safely without consuming the downstream body stream (Starlette Bug Mitigation)
        if request.method in ("POST", "PUT", "PATCH") and "application/json" in request.headers.get("content-type", ""):
            try:
                body_bytes = await request.body()
                
                # Re-stream body so downstream handlers can parse it again
                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                request._receive = receive
                
                # Parse JSON
                if body_bytes:
                    payload = json.loads(body_bytes)
                    return payload.get("session_id", "anonymous")
            except Exception as e:
                logger.debug(f"Rate Limiter: Failed to parse JSON body for session tracking: {e}")

        return "anonymous"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bypasses rate limiting for health check and docs assets to avoid false alerts
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # 1. Identify session ID
        session_id = await self._get_session_id(request)
        
        # Skip rate limiting for anonymous requests that don't declare state
        if session_id == "anonymous":
            return await call_next(request)

        now = time.time()
        
        # 2. Enforce Thread-Safe Sliding Window Check
        with self.lock:
            # Fetch past request timestamps for this session
            timestamps = self.requests[session_id]
            
            # Clean timestamps older than 60 seconds
            cutoff = now - 60.0
            timestamps = [t for t in timestamps if t > cutoff]
            
            # Assert rate boundaries
            if len(timestamps) >= self.limit_rpm:
                logger.warning(
                    f"Rate Limit Violated: Session '{session_id}' exceeded limit. "
                    f"Active turns in 60s: {len(timestamps)} >= {self.limit_rpm}."
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "message": (
                            "Rate limit exceeded. Maximum 60 requests per "
                            "minute per session allowed. Please wait before retrying."
                        )
                    }
                )
            
            # Add current turn timestamp and commit back
            timestamps.append(now)
            self.requests[session_id] = timestamps

        return await call_next(request)

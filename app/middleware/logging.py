"""
StayChat Hotel Assistant - Request Logging Middleware
Injects a unique Request-ID, computes response latency, and logs endpoint metadata.
"""

import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("StayChatLoggingMiddleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Standard Starlette request logging middleware.
    Instruments telemetry audits for API paths, latency and Request/Session correlations.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Generate unique request correlation ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 2. Track Session ID from headers or payload if easily accessible
        # (Headers serve as the standard tracing namespace)
        session_id = request.headers.get("X-Session-ID", "anonymous")
        
        # 3. Capture initial timestamps
        start_time = time.time()
        
        # Execute the HTTP request handler chain
        try:
            response = await call_next(request)
        except Exception as e:
            # Catch failures to log them prior to raising global 500
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request Failed: ID={request_id} | Session={session_id} | "
                f"Method={request.method} | Path={request.url.path} | "
                f"Latency={elapsed_ms:.2f}ms | Error={e}"
            )
            raise e
            
        # 4. Compute response latency metrics
        elapsed_ms = (time.time() - start_time) * 1000
        
        # 5. Append request correlation headers to output response
        response.headers["X-Request-ID"] = request_id
        
        # 6. Log detailed structured operational observability metrics (Step 10)
        logger.info(
            f"API Request: ID={request_id} | Session={session_id} | "
            f"Method={request.method} | Path={request.url.path} | "
            f"Status={response.status_code} | Latency={elapsed_ms:.2f}ms"
        )
        
        return response

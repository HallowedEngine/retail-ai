# app/middleware.py
"""Enterprise-grade middleware for rate limiting, logging, and error handling"""

import logging
import time
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and status"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        logger.info(
            f"[REQUEST] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000  # ms

            # Log response
            logger.info(
                f"[RESPONSE] {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Duration: {process_time:.2f}ms"
            )

            # Add custom headers
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            return response

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[ERROR] {request.method} {request.url.path} - "
                f"Duration: {process_time:.2f}ms - Error: {str(e)}",
                exc_info=True
            )
            raise


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit errors"""
    logger.warning(
        f"[RATE_LIMIT] Client {request.client.host if request.client else 'unknown'} "
        f"exceeded rate limit on {request.url.path}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "retry_after": 60
        }
    )


async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(
        f"[UNHANDLED] {request.method} {request.url.path} - {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "path": str(request.url.path)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with logging"""
    logger.warning(
        f"[HTTP_ERROR] {request.method} {request.url.path} - "
        f"Status: {exc.status_code} - Detail: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )

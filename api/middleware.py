#!/usr/bin/env python3
"""
Middleware for observability and telemetry.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.observability import (
    request_id_ctx,
    endpoint_ctx,
    metrics,
    StructuredLogger,
)

logger = StructuredLogger("middleware")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track metrics."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        endpoint = f"{request.method} {request.url.path}"

        # Set context variables
        request_id_ctx.set(request_id)
        endpoint_ctx.set(endpoint)

        # Add request ID to response headers
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {endpoint}",
            metadata={
                "method": request.method,
                "path": str(request.url.path),
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Record metrics
            metrics.record_latency(endpoint, duration_ms, response.status_code)

            # Log response
            logger.info(
                f"Request completed: {endpoint}",
                duration_ms=duration_ms,
                metadata={
                    "status_code": response.status_code,
                }
            )

            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request failed: {endpoint}",
                duration_ms=duration_ms,
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )

            # Re-raise
            raise

        finally:
            # Clear context
            request_id_ctx.set(None)
            endpoint_ctx.set(None)

#!/usr/bin/env python3
"""
Observability and telemetry infrastructure.

Provides structured logging, metrics collection, and error categorization.
"""
import logging
import json
import time
from enum import Enum
from typing import Any, Optional
from datetime import datetime
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from functools import wraps

# Context variables for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
endpoint_ctx: ContextVar[Optional[str]] = ContextVar("endpoint", default=None)


class ErrorCategory(str, Enum):
    """Categorized error types for monitoring."""
    EXTERNAL_API = "external_api"  # USA.gov, Gemini API failures
    DATABASE = "database"  # PostgreSQL, pgvector errors
    VALIDATION = "validation"  # Pydantic, request validation
    NOT_FOUND = "not_found"  # Resource not found
    PARSING = "parsing"  # Decision text parsing failures
    EXTRACTION = "extraction"  # LLM extraction failures
    TIMEOUT = "timeout"  # Operation timeouts
    RATE_LIMIT = "rate_limit"  # Rate limiting errors
    INTERNAL = "internal"  # Unexpected internal errors


@dataclass
class StructuredLog:
    """Structured log entry."""
    timestamp: str
    level: str
    message: str
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    duration_ms: Optional[float] = None
    error_category: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), default=str)


class StructuredLogger:
    """Logger that outputs structured JSON logs."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handler()

    def _setup_handler(self):
        """Setup JSON formatter."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _create_log(self, level: str, message: str, **kwargs) -> StructuredLog:
        """Create structured log entry."""
        return StructuredLog(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            message=message,
            request_id=request_id_ctx.get(),
            endpoint=endpoint_ctx.get(),
            **kwargs
        )

    def info(self, message: str, **kwargs):
        """Log info level."""
        log = self._create_log("INFO", message, **kwargs)
        self.logger.info(log.to_json())

    def warning(self, message: str, **kwargs):
        """Log warning level."""
        log = self._create_log("WARNING", message, **kwargs)
        self.logger.warning(log.to_json())

    def error(self, message: str, error_category: ErrorCategory = ErrorCategory.INTERNAL, **kwargs):
        """Log error level with categorization."""
        log = self._create_log(
            "ERROR",
            message,
            error_category=error_category.value,
            **kwargs
        )
        self.logger.error(log.to_json())

    def debug(self, message: str, **kwargs):
        """Log debug level."""
        log = self._create_log("DEBUG", message, **kwargs)
        self.logger.debug(log.to_json())


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # If already JSON, return as-is
        if isinstance(record.msg, str) and record.msg.startswith("{"):
            return record.msg

        # Otherwise create basic JSON structure
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": str(record.msg),
            "logger": record.name,
        })


@dataclass
class MetricData:
    """Metric data point."""
    name: str
    value: float
    unit: str
    timestamp: str
    tags: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collect and track application metrics."""

    def __init__(self):
        self.metrics: list[MetricData] = []
        self.logger = StructuredLogger("metrics")

    def record_latency(self, endpoint: str, duration_ms: float, status_code: int):
        """Record endpoint latency."""
        metric = MetricData(
            name="api.latency",
            value=duration_ms,
            unit="ms",
            timestamp=datetime.utcnow().isoformat(),
            tags={
                "endpoint": endpoint,
                "status_code": str(status_code),
            }
        )
        self.metrics.append(metric)
        self.logger.info(
            f"API latency: {endpoint}",
            duration_ms=duration_ms,
            metadata={"status_code": status_code}
        )

    def record_token_usage(self, operation: str, tokens: int, model: str = "gemini-2.0-flash"):
        """Record LLM token usage."""
        metric = MetricData(
            name="llm.tokens",
            value=float(tokens),
            unit="tokens",
            timestamp=datetime.utcnow().isoformat(),
            tags={
                "operation": operation,
                "model": model,
            }
        )
        self.metrics.append(metric)
        self.logger.info(
            f"Token usage: {operation}",
            metadata={"tokens": tokens, "model": model}
        )

    def record_error(self, category: ErrorCategory, endpoint: Optional[str] = None):
        """Record error occurrence."""
        metric = MetricData(
            name="api.errors",
            value=1.0,
            unit="count",
            timestamp=datetime.utcnow().isoformat(),
            tags={
                "category": category.value,
                "endpoint": endpoint or "unknown",
            }
        )
        self.metrics.append(metric)

    def record_external_api_call(self, service: str, success: bool, duration_ms: float):
        """Record external API call."""
        metric = MetricData(
            name="external_api.calls",
            value=1.0,
            unit="count",
            timestamp=datetime.utcnow().isoformat(),
            tags={
                "service": service,
                "success": str(success),
            }
        )
        self.metrics.append(metric)

        # Also record latency
        latency_metric = MetricData(
            name="external_api.latency",
            value=duration_ms,
            unit="ms",
            timestamp=datetime.utcnow().isoformat(),
            tags={
                "service": service,
            }
        )
        self.metrics.append(latency_metric)

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        if not self.metrics:
            return {"total_metrics": 0}

        # Calculate aggregates
        latencies = [m.value for m in self.metrics if m.name == "api.latency"]
        tokens = [m.value for m in self.metrics if m.name == "llm.tokens"]
        errors = [m for m in self.metrics if m.name == "api.errors"]

        return {
            "total_metrics": len(self.metrics),
            "latency": {
                "count": len(latencies),
                "avg_ms": sum(latencies) / len(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "min_ms": min(latencies) if latencies else 0,
            },
            "tokens": {
                "total": sum(tokens),
                "count": len(tokens),
            },
            "errors": {
                "total": len(errors),
                "by_category": self._group_errors(errors),
            }
        }

    def _group_errors(self, errors: list[MetricData]) -> dict[str, int]:
        """Group errors by category."""
        groups: dict[str, int] = {}
        for error in errors:
            category = error.tags.get("category", "unknown")
            groups[category] = groups.get(category, 0) + 1
        return groups


# Global instances
metrics = MetricsCollector()


def track_latency(endpoint: str):
    """Decorator to track endpoint latency."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException as e:
                status_code = e.status_code
                raise
            except Exception:
                status_code = 500
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_latency(endpoint, duration_ms, status_code)

        return wrapper
    return decorator


def track_external_call(service: str):
    """Decorator to track external API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_external_api_call(service, success, duration_ms)

        return wrapper
    return decorator

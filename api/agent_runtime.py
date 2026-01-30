#!/usr/bin/env python3
"""
Agent Runtime Wrapper - Thin execution layer for all agents.

Provides:
- Input validation
- Tool-call tracing
- Output confidence scoring
- Retry + fallback logic
"""
import time
import traceback
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

from api.observability import StructuredLogger, ErrorCategory, metrics

logger = StructuredLogger("agent.runtime")

T = TypeVar('T')


class AgentStatus(str, Enum):
    """Agent execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"


@dataclass
class ToolCall:
    """Traced tool call information."""
    tool_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    duration_ms: Optional[float] = None

    def complete(self, success: bool, error: Optional[str] = None):
        """Mark tool call as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        self.error = error


@dataclass
class AgentTrace:
    """Execution trace for an agent run."""
    agent_name: str
    start_time: float
    end_time: Optional[float] = None
    status: AgentStatus = AgentStatus.SUCCESS
    tool_calls: list[ToolCall] = field(default_factory=list)
    retries: int = 0
    error: Optional[str] = None
    confidence: Optional[float] = None
    duration_ms: Optional[float] = None

    def add_tool_call(self, tool_name: str) -> ToolCall:
        """Start tracking a tool call."""
        call = ToolCall(tool_name=tool_name, start_time=time.time())
        self.tool_calls.append(call)
        return call

    def complete(self, status: AgentStatus, error: Optional[str] = None, confidence: Optional[float] = None):
        """Mark agent execution as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "agent_name": self.agent_name,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "tool_calls": len(self.tool_calls),
            "retries": self.retries,
            "confidence": self.confidence,
            "error": self.error,
        }


@dataclass
class AgentResult(Generic[T]):
    """Agent execution result with metadata."""
    data: Optional[T]
    trace: AgentTrace
    confidence: float = 1.0

    @property
    def success(self) -> bool:
        """Check if agent succeeded."""
        return self.trace.status == AgentStatus.SUCCESS and self.data is not None


class AgentRuntime:
    """Runtime wrapper for agent execution."""

    def __init__(
        self,
        agent_name: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        fallback_fn: Optional[Callable] = None,
    ):
        """
        Initialize agent runtime.

        Args:
            agent_name: Name of the agent
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            fallback_fn: Optional fallback function if all retries fail
        """
        self.agent_name = agent_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.fallback_fn = fallback_fn
        self.logger = StructuredLogger(f"agent.{agent_name}")

    def execute(
        self,
        fn: Callable[..., T],
        *args,
        validate_input: Optional[Callable[[Any], bool]] = None,
        calculate_confidence: Optional[Callable[[T], float]] = None,
        **kwargs
    ) -> AgentResult[T]:
        """
        Execute agent with full runtime support.

        Args:
            fn: Function to execute
            *args: Positional arguments
            validate_input: Optional input validator
            calculate_confidence: Optional confidence calculator
            **kwargs: Keyword arguments

        Returns:
            AgentResult with trace and metadata
        """
        trace = AgentTrace(agent_name=self.agent_name, start_time=time.time())

        # Validate input
        if validate_input:
            try:
                if not validate_input(args):
                    self.logger.error(
                        "Input validation failed",
                        error_category=ErrorCategory.VALIDATION,
                        metadata={"agent": self.agent_name}
                    )
                    trace.complete(AgentStatus.FAILED, error="Input validation failed")
                    return AgentResult(data=None, trace=trace, confidence=0.0)
            except Exception as e:
                self.logger.error(
                    f"Input validator crashed: {e}",
                    error_category=ErrorCategory.INTERNAL,
                    metadata={"agent": self.agent_name}
                )
                trace.complete(AgentStatus.FAILED, error=f"Validator error: {e}")
                return AgentResult(data=None, trace=trace, confidence=0.0)

        # Execute with retry logic
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    trace.retries += 1
                    trace.status = AgentStatus.RETRYING
                    self.logger.info(
                        f"Retry attempt {attempt}/{self.max_retries}",
                        metadata={"agent": self.agent_name}
                    )
                    time.sleep(self.retry_delay * attempt)  # Exponential backoff

                # Execute function
                result = fn(*args, **kwargs)

                # Calculate confidence
                confidence = 1.0
                if calculate_confidence:
                    try:
                        confidence = calculate_confidence(result)
                    except Exception as e:
                        self.logger.warning(
                            f"Confidence calculation failed: {e}",
                            metadata={"agent": self.agent_name}
                        )

                # Success
                trace.complete(AgentStatus.SUCCESS, confidence=confidence)
                self.logger.info(
                    "Agent execution successful",
                    metadata={
                        "agent": self.agent_name,
                        "duration_ms": trace.duration_ms,
                        "confidence": confidence,
                        "retries": trace.retries,
                    }
                )

                # Record metrics
                metrics.record_latency(
                    f"agent.{self.agent_name}",
                    trace.duration_ms,
                    200
                )

                return AgentResult(data=result, trace=trace, confidence=confidence)

            except Exception as e:
                last_error = str(e)
                error_trace = traceback.format_exc()

                self.logger.warning(
                    f"Agent execution failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}",
                    metadata={
                        "agent": self.agent_name,
                        "error_trace": error_trace[:500],
                    }
                )

                # Record error
                metrics.record_error(
                    ErrorCategory.INTERNAL,
                    f"agent.{self.agent_name}"
                )

        # All retries failed - try fallback
        if self.fallback_fn:
            try:
                trace.status = AgentStatus.FALLBACK
                self.logger.info(
                    "Using fallback function",
                    metadata={"agent": self.agent_name}
                )
                result = self.fallback_fn(*args, **kwargs)
                trace.complete(AgentStatus.FALLBACK, confidence=0.5)

                return AgentResult(data=result, trace=trace, confidence=0.5)
            except Exception as e:
                self.logger.error(
                    f"Fallback function failed: {e}",
                    error_category=ErrorCategory.INTERNAL,
                    metadata={"agent": self.agent_name}
                )

        # Complete failure
        trace.complete(AgentStatus.FAILED, error=last_error)
        self.logger.error(
            "Agent execution failed after all retries",
            error_category=ErrorCategory.INTERNAL,
            metadata={
                "agent": self.agent_name,
                "retries": trace.retries,
                "last_error": last_error,
            }
        )

        return AgentResult(data=None, trace=trace, confidence=0.0)

    def trace_tool_call(self, tool_name: str, trace: AgentTrace):
        """
        Context manager for tracing tool calls.

        Usage:
            with runtime.trace_tool_call("fetch_data", trace):
                data = fetch_data()
        """
        class ToolCallTracer:
            def __init__(self, tool_name: str, trace: AgentTrace):
                self.tool_call = trace.add_tool_call(tool_name)

            def __enter__(self):
                return self.tool_call

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.tool_call.complete(success=False, error=str(exc_val))
                else:
                    self.tool_call.complete(success=True)
                return False  # Don't suppress exceptions

        return ToolCallTracer(tool_name, trace)


def agent_wrapper(
    agent_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    fallback_fn: Optional[Callable] = None,
):
    """
    Decorator to wrap functions with agent runtime.

    Example:
        @agent_wrapper("my_agent", max_retries=2)
        def my_function(x: int) -> int:
            return x * 2
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., AgentResult[T]]:
        runtime = AgentRuntime(
            agent_name=agent_name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            fallback_fn=fallback_fn,
        )

        @wraps(fn)
        def wrapper(*args, **kwargs) -> AgentResult[T]:
            return runtime.execute(fn, *args, **kwargs)

        return wrapper
    return decorator


# Example confidence calculators
def text_length_confidence(text: str, min_length: int = 100) -> float:
    """Calculate confidence based on text length."""
    if not text:
        return 0.0
    return min(1.0, len(text) / min_length)


def list_size_confidence(items: list, min_size: int = 1) -> float:
    """Calculate confidence based on list size."""
    if not items:
        return 0.0
    return min(1.0, len(items) / max(1, min_size))


def extraction_confidence(result: Any) -> float:
    """Calculate confidence for extraction results."""
    if not result:
        return 0.0

    # Check if result has issues
    if hasattr(result, 'issues'):
        if not result.issues:
            return 0.3  # Low confidence if no issues found

        # Average passage confidence
        confidences = []
        for issue in result.issues:
            if hasattr(issue, 'passages'):
                for passage in issue.passages:
                    if hasattr(passage, 'confidence'):
                        confidences.append(passage.confidence)

        if confidences:
            return sum(confidences) / len(confidences)

    return 0.7  # Default moderate confidence

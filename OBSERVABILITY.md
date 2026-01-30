# Observability & Agent Runtime

Comprehensive telemetry infrastructure for the VA Decision Analysis API.

## Overview

The system includes two layers:
1. **Observability Layer**: Structured logging, metrics collection, error categorization
2. **Agent Runtime Layer**: Execution wrapper with retry logic, tracing, and confidence scoring

## Structured Logging

### Features
- JSON-formatted logs for easy parsing
- Request context tracking (request ID, endpoint)
- Error categorization for monitoring
- Automatic metadata enrichment

### Usage

```python
from api.observability import StructuredLogger, ErrorCategory

logger = StructuredLogger("my_service")

# Info logging
logger.info("Operation completed", metadata={"items": 42})

# Error logging with categorization
logger.error(
    "Failed to fetch decision",
    error_category=ErrorCategory.EXTERNAL_API,
    metadata={"url": decision_url}
)
```

### Log Format

```json
{
  "timestamp": "2024-01-30T12:34:56.789Z",
  "level": "INFO",
  "message": "Request completed: GET /api/v1/search",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "endpoint": "GET /api/v1/search",
  "duration_ms": 245.67,
  "metadata": {
    "status_code": 200
  }
}
```

## Error Categories

Errors are categorized for better monitoring and alerting:

| Category | Description | Examples |
|----------|-------------|----------|
| `EXTERNAL_API` | Third-party API failures | USA.gov timeout, Gemini API error |
| `DATABASE` | Database errors | Connection failed, query timeout |
| `VALIDATION` | Request validation | Missing parameters, invalid format |
| `NOT_FOUND` | Resource not found | Decision doesn't exist |
| `PARSING` | Text parsing failures | Malformed decision text |
| `EXTRACTION` | LLM extraction failures | Gemini timeout, invalid JSON |
| `TIMEOUT` | Operation timeouts | Long-running query |
| `RATE_LIMIT` | Rate limiting | Too many requests |
| `INTERNAL` | Unexpected errors | Bugs, unhandled exceptions |

## Metrics Collection

### Tracked Metrics

1. **API Latency** (`api.latency`)
   - Endpoint-level response times
   - Status code tracking
   - Percentile calculations

2. **Token Usage** (`llm.tokens`)
   - Per-operation token counts
   - Model tracking (Gemini 2.0 Flash)
   - Cost estimation data

3. **External API Calls** (`external_api.calls`, `external_api.latency`)
   - Success/failure rates
   - Service-level latencies
   - Timeout tracking

4. **Errors** (`api.errors`)
   - Category-level error counts
   - Endpoint-level error rates

### Usage

```python
from api.observability import metrics

# Record latency
metrics.record_latency("GET /api/v1/search", 125.5, 200)

# Record token usage
metrics.record_token_usage("entity_extraction", 1523)

# Record error
metrics.record_error(ErrorCategory.EXTERNAL_API, "search")

# Get summary
summary = metrics.get_summary()
# Returns: { "latency": {...}, "tokens": {...}, "errors": {...} }
```

### Metrics Endpoint

Access real-time metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "total_metrics": 1247,
  "latency": {
    "count": 856,
    "avg_ms": 187.3,
    "max_ms": 1523.7,
    "min_ms": 12.4
  },
  "tokens": {
    "total": 45823,
    "count": 23
  },
  "errors": {
    "total": 12,
    "by_category": {
      "external_api": 8,
      "parsing": 3,
      "validation": 1
    }
  }
}
```

## Middleware

The `ObservabilityMiddleware` automatically tracks all requests:

- Generates unique request IDs
- Logs request start/completion
- Records latency metrics
- Adds custom response headers
- Handles errors gracefully

Response headers added:
- `X-Request-ID`: Unique request identifier
- `X-Response-Time`: Response time in milliseconds

## Agent Runtime Wrapper

### Overview

The Agent Runtime provides a thin execution layer for all agent operations with:
- **Input Validation**: Pre-execution checks
- **Tool-Call Tracing**: Track external calls
- **Confidence Scoring**: Output quality metrics
- **Retry Logic**: Automatic retries with exponential backoff
- **Fallback**: Graceful degradation

### Core Components

#### AgentRuntime

```python
from api.agent_runtime import AgentRuntime

runtime = AgentRuntime(
    agent_name="entity_extraction",
    max_retries=3,
    retry_delay=1.0,
    fallback_fn=fallback_handler,
)

result = runtime.execute(
    my_function,
    arg1, arg2,
    validate_input=input_validator,
    calculate_confidence=confidence_scorer,
)

if result.success:
    print(f"Data: {result.data}")
    print(f"Confidence: {result.confidence}")
    print(f"Duration: {result.trace.duration_ms}ms")
```

#### AgentResult

Every agent execution returns an `AgentResult` with:
- `data`: The actual result (or None if failed)
- `trace`: Execution trace with timing and tool calls
- `confidence`: Quality score (0.0 to 1.0)
- `success`: Boolean property

#### AgentTrace

Tracks execution details:
- Start/end times
- Status (SUCCESS, FAILED, RETRYING, FALLBACK)
- Tool calls with individual timings
- Retry count
- Error messages
- Confidence score

### Decorator Usage

```python
from api.agent_runtime import agent_wrapper

@agent_wrapper("my_agent", max_retries=2)
def process_decision(text: str) -> dict:
    # Your logic here
    return {"result": "processed"}

# Returns AgentResult automatically
result = process_decision("some text")
```

### Input Validation

```python
def validate_extraction_input(args: tuple) -> bool:
    """Validate extraction input."""
    if not args or len(args) == 0:
        return False
    text = args[0]
    return isinstance(text, str) and len(text) >= 100

runtime.execute(
    extract_entities,
    decision_text,
    validate_input=validate_extraction_input,
)
```

### Confidence Scoring

```python
def calculate_confidence(result: ExtractionResponse) -> float:
    """Calculate confidence based on extraction quality."""
    if not result.issues:
        return 0.3  # Low confidence

    # Average passage confidence
    confidences = []
    for issue in result.issues:
        for passage in issue.passages:
            confidences.append(passage.confidence)

    return sum(confidences) / len(confidences) if confidences else 0.5

runtime.execute(
    extract_entities,
    text,
    calculate_confidence=calculate_confidence,
)
```

### Tool Call Tracing

```python
from api.agent_runtime import AgentTrace

trace = AgentTrace(agent_name="my_agent", start_time=time.time())

# Trace external API call
with runtime.trace_tool_call("gemini_api", trace):
    response = call_gemini_api(prompt)

# Trace database query
with runtime.trace_tool_call("db_query", trace):
    results = query_database(sql)

# Review trace
for call in trace.tool_calls:
    print(f"{call.tool_name}: {call.duration_ms}ms (success={call.success})")
```

### Retry Logic

Automatic retry with exponential backoff:
- First retry: Immediate
- Second retry: 1s delay
- Third retry: 2s delay
- Fallback: If provided

```python
def fallback_extraction(text: str):
    """Return empty result on failure."""
    return ExtractionResponse(issues=[])

runtime = AgentRuntime(
    agent_name="extraction",
    max_retries=3,
    retry_delay=1.0,
    fallback_fn=fallback_extraction,
)
```

## Integration Examples

### Service Layer Integration

```python
from api.agent_runtime import AgentRuntime, AgentResult
from api.observability import StructuredLogger, ErrorCategory, metrics

logger = StructuredLogger("service.extraction")

extraction_runtime = AgentRuntime(
    agent_name="entity_extraction",
    max_retries=2,
)

def extract_decision_entities(text: str) -> ExtractionResponse:
    """Extract with runtime support."""
    result = extraction_runtime.execute(
        extract_entities,
        text,
        validate_input=lambda args: len(args[0]) >= 100,
        calculate_confidence=extraction_confidence,
    )

    if not result.success:
        logger.error(
            "Extraction failed",
            error_category=ErrorCategory.EXTRACTION,
            metadata=result.trace.to_dict(),
        )
        metrics.record_error(ErrorCategory.EXTRACTION)
        raise HTTPException(500, "Extraction failed")

    # Log success with confidence
    logger.info(
        "Extraction completed",
        metadata={
            "confidence": result.confidence,
            "duration_ms": result.trace.duration_ms,
            "issues_found": len(result.data.issues),
        }
    )

    # Record token usage
    approx_tokens = len(text) // 4
    metrics.record_token_usage("entity_extraction", approx_tokens)

    return result.data
```

### FastAPI Endpoint Integration

```python
@app.post("/api/v1/extract")
async def extract_endpoint(request: ExtractionRequest):
    """Extract with full observability."""
    try:
        response = extract_decision_entities(request.text)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error: {e}",
            error_category=ErrorCategory.INTERNAL,
        )
        raise HTTPException(500, "Internal server error")
```

## Monitoring Best Practices

### 1. Always Log Context
```python
logger.info(
    "Operation started",
    metadata={
        "user_id": user_id,
        "resource": resource_id,
        "params": params,
    }
)
```

### 2. Categorize Errors
```python
try:
    response = external_api.call()
except TimeoutError:
    logger.error("API timeout", error_category=ErrorCategory.TIMEOUT)
except ValueError:
    logger.error("Invalid response", error_category=ErrorCategory.EXTERNAL_API)
```

### 3. Track Metrics Consistently
```python
start = time.time()
try:
    result = operation()
    duration_ms = (time.time() - start) * 1000
    metrics.record_latency("operation", duration_ms, 200)
except Exception:
    duration_ms = (time.time() - start) * 1000
    metrics.record_latency("operation", duration_ms, 500)
    raise
```

### 4. Use Agent Runtime for Critical Paths
```python
# Critical: LLM extraction (expensive, can fail)
extraction_runtime = AgentRuntime(
    agent_name="extraction",
    max_retries=3,
    fallback_fn=empty_result,
)

# Non-critical: Database query (fast, reliable)
# Use regular error handling
```

## Testing Observability

### Unit Tests
```python
def test_structured_logging():
    logger = StructuredLogger("test")
    logger.info("Test message", metadata={"key": "value"})
    # Verify JSON output

def test_metrics_collection():
    metrics = MetricsCollector()
    metrics.record_latency("test", 123.4, 200)
    summary = metrics.get_summary()
    assert summary["latency"]["count"] == 1
```

### Integration Tests
```python
async def test_observability_middleware():
    response = await client.get("/api/v1/health")
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers
```

### Agent Runtime Tests
```python
def test_retry_logic():
    call_count = 0

    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    runtime = AgentRuntime("test", max_retries=3)
    result = runtime.execute(flaky_function)

    assert result.success
    assert result.trace.retries == 2
```

## Future Enhancements

- [ ] Export metrics to Prometheus
- [ ] Distributed tracing with OpenTelemetry
- [ ] Alerting integration (PagerDuty, Slack)
- [ ] Cost tracking for LLM operations
- [ ] Performance profiling dashboard
- [ ] Anomaly detection on metrics

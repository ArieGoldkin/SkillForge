---
name: structured-logging
description: JSON structured logging with correlation IDs
version: 1.0.0
tags: [logging, observability, json, correlation]
size: atomic
domain: devops
---

# Structured Logging

## Log Levels

| Level | Use Case |
|-------|----------|
| ERROR | Unhandled exceptions, failures |
| WARN | Deprecated API, retries |
| INFO | Business events, success |
| DEBUG | Development troubleshooting |

## JSON Format

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# ✅ Good: Structured with context
logger.info("user_action",
    action="purchase",
    user_id=user.id,
    order_id=order.id,
    duration_ms=150
)

# ❌ Bad: String interpolation
logger.info(f"User {user.id} completed purchase")
```

## Correlation IDs

```python
from uuid import uuid4

@app.middleware("http")
async def correlation_middleware(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())

    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path
    )

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

## Output Example

```json
{
  "event": "routing_to_agent",
  "level": "info",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "correlation_id": "abc-123-def",
  "analysis_id": "550e8400-e29b-41d4",
  "agent": "tech_comparator",
  "remaining": 7
}
```

## Log Sampling

```python
import random

def should_sample(level: str, rate: float = 0.1) -> bool:
    if level in ["ERROR", "CRITICAL"]:
        return True  # Always log errors
    return random.random() < rate

# 100% errors, 10% info
if should_sample("INFO", rate=0.1):
    logger.info("request_processed")
```

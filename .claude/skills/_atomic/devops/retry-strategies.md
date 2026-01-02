---
name: retry-strategies
description: Exponential backoff with jitter for transient failures
version: 1.0.0
tags: [resilience, retry, backoff, fault-tolerance]
size: atomic
domain: devops
---

# Retry Strategies

## Exponential Backoff + Jitter

```
Attempt 1: ──▶ X (fail)
            wait: 1s ± 0.5s

Attempt 2: ──▶ X (fail)
            wait: 2s ± 1s

Attempt 3: ──▶ X (fail)
            wait: 4s ± 2s

Attempt 4: ──▶ ✓ (success)
```

**Formula**: `delay = min(base * 2^attempt, max) * jitter`

## Implementation

```python
import asyncio
import random

async def retry_with_backoff(
    func,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_errors: tuple = (ConnectionError, TimeoutError)
):
    for attempt in range(max_attempts):
        try:
            return await func()
        except retryable_errors as e:
            if attempt == max_attempts - 1:
                raise

            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(delay * jitter)
```

## Error Classification

```python
RETRYABLE = {
    # HTTP
    408, 429, 500, 502, 503, 504,
    ConnectionError, TimeoutError,

    # LLM
    "rate_limit_exceeded",
    "model_overloaded",
}

NON_RETRYABLE = {
    400, 401, 403, 404,
    "invalid_api_key",
    "content_policy_violation",
}
```

## Decorator Pattern

```python
from functools import wraps

def with_retry(max_attempts=3, base_delay=1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_attempts=max_attempts,
                base_delay=base_delay
            )
        return wrapper
    return decorator

@with_retry(max_attempts=3)
async def call_api():
    return await external_api()
```

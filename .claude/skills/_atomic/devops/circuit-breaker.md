---
name: circuit-breaker
description: Circuit breaker pattern for cascade failure prevention
version: 1.0.0
tags: [resilience, circuit-breaker, fault-tolerance]
size: atomic
domain: devops
---

# Circuit Breaker

## States

```
CLOSED ──failures >= threshold──▶ OPEN
   ▲                                │
   │ success                  timeout expires
   │                                │
   └────────── HALF_OPEN ◀──────────┘
```

- **CLOSED**: Normal, count failures
- **OPEN**: Reject immediately, return fallback
- **HALF_OPEN**: Allow probe request to test recovery

## Implementation

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_requests: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self._recovery_timeout_expired():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| failure_threshold | 5 | Failures before opening |
| recovery_timeout | 30s | Wait before half-open |
| half_open_requests | 1 | Probes in half-open |

## Usage

```python
breaker = CircuitBreaker(failure_threshold=3)

async def call_external_api():
    if not breaker.can_execute():
        return fallback_response()

    try:
        result = await external_api()
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise
```

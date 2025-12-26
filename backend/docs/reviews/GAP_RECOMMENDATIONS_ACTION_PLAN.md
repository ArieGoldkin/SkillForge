# GAP Integration - Action Plan & Recommendations

**Date:** 2025-12-26
**Status:** ✅ APPROVED FOR PRODUCTION
**Review Document:** `GAP_ARCHITECTURE_REVIEW.md`

---

## Executive Summary

The GAP 2, 3, 5 integration is **architecturally sound** and ready for production deployment. This document provides actionable recommendations to enhance robustness, observability, and maintainability.

**Total Estimated Effort:** ~5 hours for all high-priority items.

---

## High Priority Recommendations

### 1. Add Runtime Protection to Reset Functions (30 min)

**Problem:** Reset functions are exposed in production modules and could be called accidentally.

**Solution:** Add runtime checks to prevent production misuse.

**Implementation:**

```python
# app/core/resilience.py

def reset_resilience_manager() -> None:
    """Reset resilience manager singleton for testing.

    CRITICAL: Only use in test fixtures, never in production code.

    Raises:
        RuntimeError: If called outside test environment
    """
    import sys

    # Check if running in pytest
    if "pytest" not in sys.modules:
        raise RuntimeError(
            "reset_resilience_manager() can only be called during tests. "
            "This function is for test isolation only. "
            "If you need to reset state in production, use proper lifecycle hooks."
        )

    global _resilience_manager
    if _resilience_manager is not None:
        ResilienceManager._circuit_breakers = {}
        ResilienceManager._instance = None
        _resilience_manager = None
        logger.debug("resilience_manager_reset", reason="test_cleanup")
```

**Apply same pattern to:**
- `app/core/bulkhead.py::reset_bulkhead_registry()`
- Any other singleton reset functions

**Test:**
```python
# tests/unit/core/test_resilience_reset_protection.py
def test_reset_resilience_manager_fails_in_production():
    """Verify reset function raises in production environment."""
    import sys

    # Temporarily remove pytest from sys.modules
    pytest_module = sys.modules.pop("pytest", None)

    try:
        with pytest.raises(RuntimeError, match="can only be called during tests"):
            reset_resilience_manager()
    finally:
        # Restore pytest module
        if pytest_module:
            sys.modules["pytest"] = pytest_module
```

**Files to Modify:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/resilience.py` (line 232)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/bulkhead.py` (line 366)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/tests/unit/core/test_resilience_reset_protection.py` (NEW)

---

### 2. Create Reusable G-Eval Mock Utilities (1 hour)

**Problem:** G-Eval mock setup is duplicated across tests with inconsistent patterns.

**Solution:** Centralize mock logic in test utilities.

**Implementation:**

```python
# tests/utils/g_eval_mocks.py (NEW FILE)
"""Reusable G-Eval mock utilities for testing.

This module provides standardized mocks for G-Eval evaluators to ensure
consistency across tests and reduce duplication.

Usage:
    >>> from tests.utils.g_eval_mocks import create_multi_aspect_mock
    >>>
    >>> @pytest.fixture
    >>> def mock_g_eval_success():
    ...     return create_multi_aspect_mock({
    ...         "depth": 0.9,
    ...         "relevance": 0.85,
    ...         "coherence": 0.8,
    ...     })
    >>>
    >>> async def test_quality_gate_pass(base_state, mock_g_eval_success):
    ...     with patch("app.shared.services.g_eval.multi_judge.create_g_eval_evaluator") as mock:
    ...         mock.side_effect = mock_g_eval_success
    ...         result = await quality_gate_node(base_state)
    ...         assert result["quality_gate_passed"] is True
"""

from typing import Any, Callable


class MockEvaluation:
    """Mock Langfuse Evaluation object.

    Mimics the structure of langfuse.Evaluation with value, comment, and metadata.
    """

    def __init__(self, value: float, comment: str = "", metadata: dict | None = None):
        """Initialize mock evaluation.

        Args:
            value: Score value (0.0-1.0)
            comment: Optional comment/reasoning
            metadata: Optional metadata dict
        """
        self.value = value
        self.comment = comment
        self.metadata = metadata or {}


def create_mock_evaluator(
    score: float,
    comment: str = "",
    should_timeout: bool = False,
    should_error: bool = False,
) -> Callable:
    """Create a mock G-Eval evaluator function.

    Args:
        score: Score to return (0.0-1.0)
        comment: Optional comment
        should_timeout: If True, raise TimeoutError
        should_error: If True, raise generic Exception

    Returns:
        Mock evaluator function matching G-Eval signature
    """

    def evaluator(*, input: dict[str, Any], output: str, _expected_output: Any = None):
        if should_timeout:
            raise TimeoutError("Evaluation timed out")
        if should_error:
            raise RuntimeError("Evaluation error")
        return MockEvaluation(value=score, comment=comment or f"{score*10}/10")

    return evaluator


def create_multi_aspect_mock(
    scores: dict[str, float],
    timeout_aspects: list[str] | None = None,
    error_aspects: list[str] | None = None,
) -> Callable:
    """Create a mock for multi-aspect evaluation.

    This is the most common pattern for testing quality gate node.

    Args:
        scores: Map aspect -> score (e.g., {"depth": 0.8, "relevance": 0.9})
        timeout_aspects: List of aspects that should timeout (e.g., ["coherence"])
        error_aspects: List of aspects that should raise errors

    Returns:
        Side effect function for patch("multi_judge.create_g_eval_evaluator")

    Example:
        >>> mock_create = create_multi_aspect_mock(
        ...     scores={"depth": 0.8, "relevance": 0.9, "coherence": 0.85},
        ...     timeout_aspects=["coherence"]
        ... )
        >>> with patch("app.shared.services.g_eval.multi_judge.create_g_eval_evaluator") as mock:
        ...     mock.side_effect = mock_create
        ...     result = await quality_gate_node(state)
        ...     # coherence will timeout, others will succeed
    """
    timeout_aspects = timeout_aspects or []
    error_aspects = error_aspects or []

    def side_effect(*args, **kwargs):
        criterion = kwargs.get("criterion", "")

        if criterion in timeout_aspects:
            return create_mock_evaluator(0.0, should_timeout=True)

        if criterion in error_aspects:
            return create_mock_evaluator(0.0, should_error=True)

        score = scores.get(criterion, 0.5)  # Default to 0.5 if aspect not in scores
        return create_mock_evaluator(score, f"{score*10}/10")

    return side_effect


# Common fixtures for reuse
def mock_g_eval_all_high_scores():
    """Fixture for high-quality evaluation scores (all >= 0.8)."""
    return create_multi_aspect_mock({
        "depth": 0.9,
        "relevance": 0.85,
        "coherence": 0.9,
    })


def mock_g_eval_mixed_scores():
    """Fixture for mixed-quality scores (average ~0.7)."""
    return create_multi_aspect_mock({
        "depth": 0.8,
        "relevance": 0.7,
        "coherence": 0.6,
    })


def mock_g_eval_low_scores():
    """Fixture for low-quality scores (all < 0.6)."""
    return create_multi_aspect_mock({
        "depth": 0.5,
        "relevance": 0.4,
        "coherence": 0.5,
    })
```

**Update existing tests to use utilities:**

```python
# tests/unit/domains/analysis/workflows/nodes/test_quality_gate_node.py

from tests.utils.g_eval_mocks import create_multi_aspect_mock

@pytest.mark.asyncio
async def test_quality_gate_evaluator_timeout(base_state: AnalysisState):
    """Test single evaluator timeout - should use default 0.5 score."""

    # OLD (verbose, duplicated logic):
    # def create_evaluator_side_effect(*args, **kwargs):
    #     criterion = kwargs.get("criterion", "")
    #     def timeout_evaluator(...):
    #         raise TimeoutError(...)
    #     ...

    # NEW (concise, reusable):
    mock_create = create_multi_aspect_mock(
        scores={"depth": 0.8, "coherence": 0.8},
        timeout_aspects=["relevance"],  # Only relevance times out
    )

    with (
        patch("app.shared.services.g_eval.multi_judge.create_g_eval_evaluator") as mock,
        patch("app.shared.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.domains.analysis.workflows.nodes.quality_gate_node.get_current_trace_id") as mock_run_tree,
        patch("app.shared.services.g_eval.multi_judge.logger") as mock_multi_judge_logger,
    ):
        mock_run_tree.return_value = None
        mock.side_effect = mock_create

        result = await quality_gate_node(base_state)

        # Verify relevance got default 0.5 (timeout)
        assert result["quality_scores"]["relevance"]["score"] == 0.5
        assert "error" in result["quality_scores"]["relevance"]["comment"].lower()

        # Verify timeout was logged
        mock_multi_judge_logger.warning.assert_called()
```

**Files to Create:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/tests/utils/g_eval_mocks.py` (NEW - 150 lines)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/tests/utils/__init__.py` (NEW)

**Files to Update:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/tests/unit/domains/analysis/workflows/nodes/test_quality_gate_node.py`
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/tests/unit/domains/analysis/workflows/test_quality_gate_aspect_minimums.py`

---

### 3. Add Prometheus Metrics for Resilience Patterns (2-3 hours)

**Problem:** No metrics for circuit breaker state, bulkhead utilization, or rejection rates.

**Solution:** Add Prometheus metrics integration.

**Implementation:**

```python
# app/core/metrics.py (NEW FILE)
"""Prometheus metrics for resilience patterns.

Exposes circuit breaker state, bulkhead utilization, and rejection rates
for monitoring and alerting.
"""

from prometheus_client import Counter, Gauge, Histogram

# Circuit Breaker Metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    ["breaker_name"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["breaker_name"],
)

circuit_breaker_state_changes = Counter(
    "circuit_breaker_state_changes_total",
    "Total circuit breaker state transitions",
    ["breaker_name", "from_state", "to_state"],
)

# Bulkhead Metrics
bulkhead_active_tasks = Gauge(
    "bulkhead_active_tasks",
    "Number of active tasks in bulkhead",
    ["tier"],
)

bulkhead_queue_depth = Gauge(
    "bulkhead_queue_depth",
    "Number of tasks waiting in queue",
    ["tier"],
)

bulkhead_rejections = Counter(
    "bulkhead_rejections_total",
    "Total bulkhead rejections (queue full)",
    ["tier"],
)

bulkhead_timeouts = Counter(
    "bulkhead_timeouts_total",
    "Total bulkhead timeouts",
    ["tier"],
)

bulkhead_execution_time = Histogram(
    "bulkhead_execution_seconds",
    "Time spent executing in bulkhead",
    ["tier"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)
```

**Update circuit breaker to emit metrics:**

```python
# app/core/circuit_breaker.py

from app.core.metrics import (
    circuit_breaker_failures,
    circuit_breaker_state,
    circuit_breaker_state_changes,
)

class CircuitBreaker:
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging and metrics."""
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = time.monotonic()

        if old_state != new_state:
            logger.warning(
                "circuit_breaker_state_change",
                breaker=self.name,
                from_state=old_state.value,
                to_state=new_state.value,
                failure_count=self._state.failure_count,
            )

            # Emit metrics
            circuit_breaker_state_changes.labels(
                breaker_name=self.name,
                from_state=old_state.value,
                to_state=new_state.value,
            ).inc()

            # Update state gauge (0=CLOSED, 1=HALF_OPEN, 2=OPEN)
            state_value = {"closed": 0, "half_open": 1, "open": 2}[new_state.value]
            circuit_breaker_state.labels(breaker_name=self.name).set(state_value)

    async def _handle_failure(self, exc: Exception) -> None:
        """Handle failed call with metrics."""
        # ... existing logic ...

        # Emit failure metric
        circuit_breaker_failures.labels(breaker_name=self.name).inc()

        # ... rest of existing logic ...
```

**Update bulkhead to emit metrics:**

```python
# app/core/bulkhead.py

from app.core.metrics import (
    bulkhead_active_tasks,
    bulkhead_execution_time,
    bulkhead_queue_depth,
    bulkhead_rejections,
    bulkhead_timeouts,
)

class Bulkhead:
    async def execute(self, fn: Callable[[], Awaitable[T]], timeout: float | None = None) -> T:
        """Execute function within bulkhead constraints with metrics."""
        effective_timeout = timeout or self.timeout
        start_time = time.monotonic()

        # ... existing queue check logic ...

        try:
            # ... existing semaphore acquisition logic ...

            # Update metrics
            bulkhead_active_tasks.labels(tier=self.tier.name).set(self._active)
            bulkhead_queue_depth.labels(tier=self.tier.name).set(self._waiting)

            # Execute with timeout
            try:
                result = await asyncio.wait_for(fn(), timeout=effective_timeout)
                self.stats.successful_calls += 1

                # Record execution time
                duration = time.monotonic() - start_time
                bulkhead_execution_time.labels(tier=self.tier.name).observe(duration)

                return result
            except TimeoutError:
                bulkhead_timeouts.labels(tier=self.tier.name).inc()
                return await self._handle_timeout(effective_timeout)
            # ... rest of existing logic ...

    async def _handle_rejection(self) -> T:
        """Handle queue full situation with metrics."""
        self.stats.rejected_calls += 1
        bulkhead_rejections.labels(tier=self.tier.name).inc()

        # ... rest of existing logic ...
```

**Add metrics endpoint:**

```python
# app/api/v1/metrics.py (NEW FILE)
"""Metrics API endpoint for Prometheus scraping."""

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    This endpoint is scraped by Prometheus to collect metrics for:
    - Circuit breaker state and failures
    - Bulkhead utilization and rejections
    - Request latencies and throughput

    Returns:
        Prometheus-formatted metrics
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**Register in main app:**

```python
# app/main.py

from app.api.v1 import metrics

app.include_router(metrics.router, prefix="/api/v1")
```

**Files to Create:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/metrics.py` (NEW - 80 lines)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/api/v1/metrics.py` (NEW - 20 lines)

**Files to Update:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/circuit_breaker.py` (add metrics emissions)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/bulkhead.py` (add metrics emissions)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/main.py` (register metrics endpoint)
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/pyproject.toml` (add `prometheus-client` dependency)

**Grafana Dashboard (JSON):**

Create a Grafana dashboard template at `docs/monitoring/resilience_dashboard.json` with:
- Circuit breaker state over time (gauge)
- Bulkhead utilization by tier (heatmap)
- Rejection rate by tier (graph)
- P95/P99 execution times by tier (graph)

---

### 4. Add Resilience Status API Endpoint (1 hour)

**Problem:** No real-time visibility into circuit breaker/bulkhead state for debugging.

**Solution:** Add API endpoint to expose resilience status.

**Implementation:**

```python
# app/api/v1/resilience.py (NEW FILE)
"""Resilience status API endpoints for monitoring and debugging."""

from fastapi import APIRouter

from app.core.resilience import get_resilience_manager

router = APIRouter(prefix="/resilience", tags=["Resilience"])


@router.get("/status")
async def get_resilience_status():
    """Get real-time resilience status.

    Returns:
        Dictionary with circuit breaker states and bulkhead utilization

    Example response:
        {
          "circuit_breakers": {
            "llm_api": {
              "state": "closed",
              "failure_count": 0,
              "is_open": false
            }
          },
          "bulkheads": {
            "tier_critical": {
              "name": "tier_critical",
              "tier": "CRITICAL",
              "config": {
                "max_concurrent": 5,
                "queue_size": 10,
                "timeout": 300.0
              },
              "current": {
                "active": 2,
                "queued": 0,
                "utilization": 0.4
              },
              "stats": {
                "total_calls": 1234,
                "successful_calls": 1220,
                "rejected_calls": 0,
                "timed_out_calls": 14
              }
            },
            "tier_standard": { ... },
            "tier_optional": { ... }
          },
          "recommendations": [
            "tier_critical at 80% utilization - consider increasing workers",
            "tier_standard has rejected 5 calls - queue too small"
          ]
        }
    """
    manager = get_resilience_manager()
    status = manager.get_status()

    return {
        "circuit_breakers": status["circuit_breakers"],
        "bulkheads": status["bulkheads"],
        "recommendations": _generate_capacity_recommendations(status),
    }


def _generate_capacity_recommendations(status: dict) -> list[str]:
    """Generate capacity planning recommendations based on status.

    Args:
        status: Current resilience status from ResilienceManager

    Returns:
        List of human-readable recommendations
    """
    recommendations = []

    # Check bulkhead utilization
    for tier_name, bulkhead_status in status["bulkheads"].items():
        current = bulkhead_status["current"]
        stats = bulkhead_status["stats"]
        config = bulkhead_status["config"]

        utilization = current["utilization"]
        rejected = stats["rejected_calls"]
        timed_out = stats["timed_out_calls"]

        # High utilization warning
        if utilization > 0.8:
            recommendations.append(
                f"{tier_name} at {utilization*100:.1f}% utilization - "
                f"consider increasing max_concurrent from {config['max_concurrent']}"
            )

        # Rejection warning
        if rejected > 0:
            recommendations.append(
                f"{tier_name} has rejected {rejected} calls - "
                f"queue size ({config['queue_size']}) may be too small"
            )

        # Timeout warning
        if timed_out > stats["successful_calls"] * 0.1:  # >10% timeout rate
            recommendations.append(
                f"{tier_name} has {timed_out} timeouts ({timed_out/(timed_out+stats['successful_calls'])*100:.1f}%) - "
                f"consider increasing timeout from {config['timeout']}s"
            )

    # Check circuit breaker health
    for breaker_name, breaker_status in status["circuit_breakers"].items():
        if breaker_status["is_open"]:
            recommendations.append(
                f"Circuit breaker '{breaker_name}' is OPEN - "
                f"external service may be down ({breaker_status['failure_count']} failures)"
            )

    if not recommendations:
        recommendations.append("All resilience patterns operating normally")

    return recommendations


@router.post("/reset")
async def reset_resilience_state():
    """Reset all circuit breakers and bulkheads to initial state.

    This is a manual recovery endpoint for emergency situations.

    WARNING: This should only be used in exceptional circumstances.
    Normal recovery happens automatically through circuit breaker timeouts.

    Returns:
        Status message
    """
    manager = get_resilience_manager()

    # Reset all circuit breakers
    for breaker_name in list(manager._circuit_breakers.keys()):
        breaker = manager.get_circuit_breaker(breaker_name)
        breaker.reset()

    return {
        "status": "success",
        "message": "All circuit breakers reset to CLOSED state",
        "warning": "This is a manual override. Consider investigating root cause.",
    }
```

**Register in main app:**

```python
# app/main.py

from app.api.v1 import resilience

app.include_router(resilience.router, prefix="/api/v1")
```

**Files to Create:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/api/v1/resilience.py` (NEW - 150 lines)

**Files to Update:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/main.py` (register router)

---

## Medium Priority Recommendations

### 5. Make Circuit Breaker/Bulkhead Configs Environment-Based (1 hour)

**Files to Update:**
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/config.py`
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/resilience.py`
- `/Users/yonatangross/coding/SkillForge-gap-fixes/backend/app/core/bulkhead.py`

**Add to config.py:**

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=3,
        description="Number of failures before opening circuit breaker",
    )
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = Field(
        default=2,
        description="Number of successes to close circuit from half-open",
    )
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: float = Field(
        default=60.0,
        description="Seconds to wait before attempting recovery",
    )

    # Bulkhead Configuration
    BULKHEAD_CRITICAL_WORKERS: int = Field(default=5, description="Tier 1 max workers")
    BULKHEAD_CRITICAL_QUEUE: int = Field(default=10, description="Tier 1 queue size")
    BULKHEAD_CRITICAL_TIMEOUT: float = Field(default=300.0, description="Tier 1 timeout")

    BULKHEAD_STANDARD_WORKERS: int = Field(default=3, description="Tier 2 max workers")
    BULKHEAD_STANDARD_QUEUE: int = Field(default=5, description="Tier 2 queue size")
    BULKHEAD_STANDARD_TIMEOUT: float = Field(default=120.0, description="Tier 2 timeout")

    BULKHEAD_OPTIONAL_WORKERS: int = Field(default=2, description="Tier 3 max workers")
    BULKHEAD_OPTIONAL_QUEUE: int = Field(default=3, description="Tier 3 queue size")
    BULKHEAD_OPTIONAL_TIMEOUT: float = Field(default=60.0, description="Tier 3 timeout")
```

---

## Low Priority (Future Enhancement)

### 6. Redis-Backed Circuit Breaker for Multi-Instance Deployments (3-4 hours)

**Only implement if deploying multiple backend instances.**

See `GAP_ARCHITECTURE_REVIEW.md` Section "Scalability" for implementation details.

---

## Implementation Order

**Week 1 (Immediate - High Priority):**
1. ✅ Runtime protection for reset functions (30 min)
2. ✅ G-Eval mock utilities (1 hour)
3. ✅ Prometheus metrics (2-3 hours)
4. ✅ Resilience status API (1 hour)

**Week 2 (Medium Priority):**
5. Environment-based configs (1 hour)
6. Grafana dashboard setup (1 hour)

**Future (Low Priority):**
7. Redis-backed circuit breaker (only if needed)

---

## Testing Checklist

After implementing recommendations, verify:

- [ ] All tests pass: `pytest tests/unit/core/ -v`
- [ ] Runtime protection prevents production reset: `test_resilience_reset_protection.py`
- [ ] G-Eval mocks work: `pytest tests/unit/domains/analysis/workflows/nodes/ -k quality_gate -v`
- [ ] Metrics endpoint accessible: `curl http://localhost:8500/api/v1/metrics`
- [ ] Status endpoint returns data: `curl http://localhost:8500/api/v1/resilience/status`
- [ ] Grafana can scrape metrics: Check Prometheus targets
- [ ] Configs respect environment variables: Set `CIRCUIT_BREAKER_FAILURE_THRESHOLD=5` and verify

---

## Approval & Sign-Off

**Architecture Review:** ✅ APPROVED (see `GAP_ARCHITECTURE_REVIEW.md`)
**Production Readiness:** ✅ PASS (with high-priority recommendations)
**Security Review:** ✅ PASS (no critical issues)
**Performance Review:** ✅ PASS (well-optimized)

**Recommended for:**
- ✅ Production deployment (current state)
- ✅ Enhanced with recommendations above

**Reviewer:** Backend System Architect (Claude Opus 4.5)
**Date:** 2025-12-26


# Resilience Patterns Implementation (Issue #533)

**GAP 2: CircuitBreaker + Tier Bulkheads for Multi-Agent Workflow**

## Overview

This implementation adds resilience patterns to prevent cascade failures in the SkillForge multi-agent workflow:

1. **CircuitBreaker**: Fast-fail on repeated LLM API failures
2. **Tier-based Bulkheads**: Resource isolation by agent tier (Tier 1/2/3)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Resilience Layer Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Agent Node                                                     │
│   ┌────────────────────────────────────────────────────┐        │
│   │  1. Abort Check (if workflow aborting)             │        │
│   │  2. execute_with_resilience() wrapper              │        │
│   │     ↓                                               │        │
│   │  ResilienceManager.execute_agent()                 │        │
│   │     ↓                                               │        │
│   │  ┌──────────────────────────────────────┐          │        │
│   │  │  Bulkhead (Tier-based)               │          │        │
│   │  │  - Tier 1: 5 workers, 10 queue       │          │        │
│   │  │  - Tier 2: 3 workers, 5 queue        │          │        │
│   │  │  - Tier 3: 2 workers, 3 queue        │          │        │
│   │  │     ↓                                 │          │        │
│   │  │  ┌────────────────────────────────┐  │          │        │
│   │  │  │  CircuitBreaker (LLM API)      │  │          │        │
│   │  │  │  - State: CLOSED/OPEN/HALF_OPEN│  │          │        │
│   │  │  │  - Failure threshold: 3        │  │          │        │
│   │  │  │  - Recovery timeout: 60s       │  │          │        │
│   │  │  │     ↓                           │  │          │        │
│   │  │  │  invoke_agent()                │  │          │        │
│   │  │  │  - asyncio.timeout wrapper     │  │          │        │
│   │  │  │  - with_fallbacks() chain      │  │          │        │
│   │  │  │  - LLM API call                │  │          │        │
│   │  │  └────────────────────────────────┘  │          │        │
│   │  └──────────────────────────────────────┘          │        │
│   └────────────────────────────────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Files

### New Files

1. **`app/core/bulkhead.py`** (365 lines)
   - `Bulkhead` class: Semaphore-based resource isolation
   - `BulkheadRegistry`: Singleton registry for tier bulkheads
   - `Tier` enum: CRITICAL, STANDARD, OPTIONAL
   - `TIER_DEFAULTS`: Configured limits for each tier

2. **`app/core/resilience.py`** (223 lines)
   - `ResilienceManager`: Unified resilience coordination
   - Maps AgentTier → Bulkhead Tier (1→CRITICAL, 2→STANDARD, 3→OPTIONAL)
   - `execute_agent()`: Wraps agent execution with CB + bulkhead
   - `get_status()`: Observability endpoint for resilience state

3. **`app/domains/analysis/workflows/agents/resilience_wrapper.py`** (113 lines)
   - `execute_with_resilience()`: Convenience wrapper for agent nodes
   - Provides simple interface: `execute_with_resilience(agent_type, tier, fn)`

### Modified Files

4. **`app/domains/analysis/workflows/agents/invocation.py`**
   - Added circuit breaker wrapper around `agent.ainvoke()`
   - Logs circuit breaker state in debug logs
   - Minimal change: 5 lines added to existing flow

## Tier Configuration

| Tier | Workers | Queue | Timeout | Agents |
|------|---------|-------|---------|--------|
| **CRITICAL** (Tier 1) | 5 | 10 | 300s | key_insights, pros_cons, audience_fit, actionable |
| **STANDARD** (Tier 2) | 3 | 5 | 120s | fact_validator, source_credibility, freshness_checker, alternatives_finder |
| **OPTIONAL** (Tier 3) | 2 | 3 | 60s | deep_researcher, community_pulse, knowledge_curator, learning_path_advisor |

## Circuit Breaker Configuration

```python
CircuitBreakerConfig(
    failure_threshold=3,      # LLM APIs can be unstable
    success_threshold=2,       # Successes to close from half-open
    timeout_seconds=60.0,      # Give API time to recover
)
```

## Usage Example

### Current Pattern (Agent Node)
```python
async def key_insights_node(state: AnalysisState) -> dict[str, object]:
    # Abort check
    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    # Run agent (no resilience)
    result = await run_key_insights_with_session(
        content=get_fallback_content(state),
        content_type=content_type,
        analysis_id=str(analysis_id),
        state=state,
    )
    return {"agent_findings": [result]}
```

### New Pattern (With Resilience)
```python
from app.domains.analysis.workflows.agents.resilience_wrapper import execute_with_resilience
from app.domains.analysis.agents.registry import AgentTier

async def key_insights_node(state: AnalysisState) -> dict[str, object]:
    # Abort check
    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    # Run agent with resilience (circuit breaker + tier bulkhead)
    return await execute_with_resilience(
        agent_type="key_insights",
        tier=AgentTier.UNIVERSAL,  # Tier 1
        fn=lambda: run_key_insights_with_session(
            content=get_fallback_content(state),
            content_type=content_type,
            analysis_id=str(analysis_id),
            state=state,
        ),
    )
```

## Failure Scenarios

### Scenario 1: LLM API Rate Limit
1. **First 3 failures**: Circuit breaker tracks failures
2. **4th failure**: Circuit breaker opens (CLOSED → OPEN)
3. **Subsequent requests**: Fail fast with `CircuitBreakerOpenError`, no LLM call
4. **After 60s**: Circuit transitions to HALF_OPEN
5. **Probe request**: If successful, circuit closes (recovery)

### Scenario 2: Tier 3 Agent Overload
1. **Tier 3 bulkhead**: 2 workers, 3 queue slots
2. **5 concurrent requests**: 2 execute, 3 wait in queue
3. **6th request**: `BulkheadFullError` - queue full
4. **Tier 1/2 agents**: Unaffected, isolated by separate bulkheads

### Scenario 3: Cascade Prevention
1. **Tier 3 agent hangs** (slow LLM response)
2. **Bulkhead isolates**: Only Tier 3 workers blocked
3. **Circuit breaker**: Detects timeout, triggers fallback model
4. **Tier 1/2 agents**: Continue normal operation

## Observability

### Circuit Breaker State Logging
```python
logger.warning(
    "circuit_breaker_state_change",
    breaker="llm_api",
    from_state="closed",
    to_state="open",
    failure_count=3,
)
```

### Bulkhead Metrics
```python
logger.warning(
    "bulkhead_rejecting_request",
    bulkhead="tier_standard",
    tier="STANDARD",
    queue_size=5,
    policy="queue",
)
```

### Agent Invocation Logging
```python
logger.debug(
    "agent_invocation_started",
    agent_type="key_insights",
    circuit_state="closed",  # NEW
    timeout_seconds=60,
)
```

### Status Endpoint (Future)
```python
from app.core.resilience import get_resilience_manager

manager = get_resilience_manager()
status = manager.get_status()

# Returns:
# {
#   "circuit_breakers": {
#     "llm_api": {
#       "state": "closed",
#       "failure_count": 1,
#       "is_open": false
#     }
#   },
#   "bulkheads": {
#     "tier_critical": {
#       "current": {"active": 2, "queued": 0, "utilization": 0.4},
#       "stats": {"total_calls": 42, "rejected_calls": 0}
#     }
#   }
# }
```

## Testing Recommendations

### Unit Tests

1. **Circuit Breaker Behavior**
   - Test state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
   - Test failure threshold (3 failures opens circuit)
   - Test recovery timeout (60s before half-open)

2. **Bulkhead Isolation**
   - Test concurrency limits (5/3/2 workers per tier)
   - Test queue behavior (10/5/3 slots per tier)
   - Test tier isolation (Tier 3 failure doesn't block Tier 1)

3. **Integration**
   - Test `execute_with_resilience()` with mock agent
   - Test circuit breaker + bulkhead coordination
   - Test graceful error handling

### Integration Tests

1. **LLM API Failure Simulation**
   - Mock LLM API to return errors
   - Verify circuit breaker opens after 3 failures
   - Verify subsequent requests fail fast

2. **Agent Overload Simulation**
   - Launch 10 concurrent Tier 3 agents
   - Verify 2 execute, 3 queue, 5 rejected
   - Verify Tier 1 agents unaffected

## Concerns & Follow-ups

### Current Implementation

✅ **Implemented:**
- Circuit breaker wired into LLM invocation layer
- Tier-based bulkheads with singleton registry
- Graceful error handling and logging
- Type-safe with full linting/type checking

⚠️ **Not Implemented (Out of Scope for GAP 2):**
- Agent node integration (minimal example provided, not wired to all agents)
- Resilience status API endpoint
- Metrics collection (Prometheus/Langfuse integration)
- Dynamic circuit breaker configuration per model
- Bulkhead metrics persistence

### Recommendations

1. **Wire one agent as proof-of-concept**
   - Start with `key_insights_node.py` (Tier 1, high-volume)
   - Measure impact on latency and failure rate
   - Validate logging output

2. **Add observability**
   - Create `/api/v1/resilience/status` endpoint
   - Expose circuit breaker and bulkhead metrics
   - Add to health check dashboard

3. **Gradual rollout**
   - Wire Tier 1 agents first (critical path)
   - Monitor for 1-2 weeks
   - Wire Tier 2/3 agents after validation

4. **Tune configuration**
   - Adjust tier limits based on production load
   - Consider separate circuit breakers per LLM provider
   - Add adaptive thresholds (sliding window)

## References

- Issue #533: https://github.com/ArieGoldkin/SkillForge/issues/533
- Resilience Patterns Skill: `.claude/skills/resilience-patterns/`
- Circuit Breaker Template: `.claude/skills/resilience-patterns/templates/circuit-breaker.py`
- Bulkhead Template: `.claude/skills/resilience-patterns/templates/bulkhead.py`
- Martin Fowler: Circuit Breaker Pattern
- Microsoft Azure: Bulkhead Pattern

## Changelog

**2025-12-25 - GAP 2 Implementation**
- ✅ Created `app/core/bulkhead.py` (Tier-based resource isolation)
- ✅ Created `app/core/resilience.py` (Unified resilience manager)
- ✅ Created `app/domains/analysis/workflows/agents/resilience_wrapper.py` (Agent helper)
- ✅ Modified `app/domains/analysis/workflows/agents/invocation.py` (Circuit breaker integration)
- ✅ All linting and type checks pass
- ✅ Minimal, practical implementation (no gold-plating)

**Next Steps:**
- [ ] Wire resilience to 1-2 agent nodes as proof-of-concept
- [ ] Add unit tests for circuit breaker and bulkhead
- [ ] Create observability endpoint (`/api/v1/resilience/status`)
- [ ] Measure impact on latency and error rates
- [ ] Document rollout plan for all agents

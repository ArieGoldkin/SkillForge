# Feature Flags & A/B Testing for Advanced LLM Techniques

**Version:** 1.0
**Status:** Phase 0 Complete, Phase 1 (Few-Shot) Ready
**Last Updated:** December 16, 2025

---

## Overview

This document describes the feature flag system and A/B testing infrastructure for advanced LLM techniques in SkillForge's multi-agent analysis pipeline.

### Key Features

- ✅ **Safe Defaults**: All techniques disabled by default
- ✅ **Gradual Rollout**: A/B testing with configurable treatment percentage
- ✅ **Deterministic Assignment**: Same analysis_id always gets same variant
- ✅ **Comprehensive Metrics**: Track latency, tokens, quality, cost
- ✅ **Production-Ready**: 100% test coverage, type-safe, well-documented

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Feature Flag System                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────┐  ┌────────────────────────────┐
│  TechniqueFlags          │  │  VariantSelector           │
│  (Phase 0-5 Settings)    │  │  (A/B Testing Logic)       │
├──────────────────────────┤  ├────────────────────────────┤
│  - enable_few_shot       │  │  - select_variant()        │
│  - enable_cot_supervisor │  │  - is_treatment()          │
│  - enable_redis_cache    │  │  - Deterministic hashing   │
│  - ab_test_enabled       │  │  - Treatment percentage    │
│  - ab_test_treatment_pct │  │                            │
└──────────────────────────┘  └────────────────────────────┘
            │                            │
            └────────────┬───────────────┘
                         ▼
            ┌────────────────────────────┐
            │  TechniqueMetrics          │
            │  (Performance Tracking)    │
            ├────────────────────────────┤
            │  - variant (control/treat) │
            │  - latency_ms              │
            │  - token_count             │
            │  - cache_hit               │
            │  - example_retrieval_ms    │
            │  - num_examples_used       │
            │  - quality_score           │
            └────────────────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `app/core/feature_flags.py` | Feature flag configuration (86 lines, 13/13 tests) |
| `app/shared/services/ab_testing/variant_selector.py` | Deterministic A/B assignment (116 lines, 16/16 tests) |
| `app/shared/services/metrics/technique_metrics.py` | Performance metrics (92 lines, 14/14 tests) |
| `.env.example` | Environment variable documentation |

---

## Usage

### 1. Enable Feature Flag + A/B Testing

```bash
# .env file
TECHNIQUE_ENABLE_FEW_SHOT=true          # Enable few-shot prompting
TECHNIQUE_AB_TEST_ENABLED=true          # Enable A/B testing
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2     # 20% traffic to treatment
```

### 2. Select Variant in Agent Creation

```python
from app.shared.services.ab_testing import get_variant_selector
from app.shared.services.metrics.technique_metrics import (
    TechniqueMetrics,
    metrics_collector,
)
from app.core.feature_flags import get_technique_flags

# Initialize
flags = get_technique_flags()
selector = get_variant_selector()

# Check if few-shot is enabled
if flags.enable_few_shot:
    # Select variant for this analysis
    variant = selector.select_variant(analysis_id, "few_shot_prompting")

    if variant == "treatment":
        # Use few-shot agent with examples
        examples = await retrieve_examples(content, agent_type)
        agent = create_few_shot_agent(examples)

        # Track metrics
        metrics = TechniqueMetrics(
            analysis_id=analysis_id,
            technique="few_shot_prompting",
            variant="treatment",
            example_retrieval_ms=retrieval_time,
            num_examples_used=len(examples),
        )
    else:
        # Use baseline agent (control)
        agent = create_baseline_agent()

        # Track control metrics
        metrics = TechniqueMetrics(
            analysis_id=analysis_id,
            technique="few_shot_prompting",
            variant="control",
        )

    # Run agent
    start = time.time()
    result = await agent.ainvoke(...)
    metrics.latency_ms = (time.time() - start) * 1000

    # Record metrics
    metrics_collector.record(metrics)
```

### 3. Retrieve Metrics Summary

```python
# Get summary for few-shot technique
summary = metrics_collector.get_summary("few_shot_prompting")

print(f"Control count: {summary['control_count']}")
print(f"Treatment count: {summary['treatment_count']}")
print(f"Control avg latency: {summary['control_avg_latency']:.2f}ms")
print(f"Treatment avg latency: {summary['treatment_avg_latency']:.2f}ms")
print(f"Treatment cache hit rate: {summary['treatment_cache_hit_rate']:.2%}")
```

---

## Feature Flags Reference

### Phase 1: Few-Shot Prompting

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `TECHNIQUE_ENABLE_FEW_SHOT` | bool | false | Enable few-shot prompting |
| `TECHNIQUE_FEW_SHOT_MAX_EXAMPLES` | int | 3 | Max examples per agent |
| `TECHNIQUE_FEW_SHOT_MIN_QUALITY` | float | 0.8 | Minimum quality score for examples |
| `TECHNIQUE_FEW_SHOT_USE_SEMANTIC` | bool | true | Use semantic search for examples |

### A/B Testing

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `TECHNIQUE_AB_TEST_ENABLED` | bool | false | Enable A/B testing |
| `TECHNIQUE_AB_TEST_TREATMENT_PCT` | float | 0.2 | Treatment group percentage (0.0-1.0) |

---

## Metrics Schema

### TechniqueMetrics Fields

```python
@dataclass
class TechniqueMetrics:
    # Required
    analysis_id: str                              # Unique analysis ID
    technique: str                                # Technique name
    variant: Literal["control", "treatment"]      # A/B test variant

    # Performance
    latency_ms: float = 0                         # Total latency
    token_count_input: int = 0                    # Input tokens
    token_count_output: int = 0                   # Output tokens

    # Caching
    cache_hit: bool = False                       # Cache hit?
    cache_level: str | None = None                # "l1_exact", "l2_redis", "l3_prompt"

    # Few-Shot (NEW)
    example_retrieval_ms: float = 0               # Time to retrieve examples
    num_examples_used: int = 0                    # Number of examples injected

    # Quality
    quality_score: float | None = None            # LLM-as-judge score (0-1)

    # Cost
    estimated_cost_usd: float = 0                 # Estimated API cost

    # Timestamps
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
```

### Summary Statistics

```python
{
    "technique": "few_shot_prompting",
    "control_count": 800,                  # 80% control
    "treatment_count": 200,                # 20% treatment
    "control_avg_latency": 1250.0,        # Baseline latency
    "treatment_avg_latency": 1180.0,      # -5.6% latency (faster!)
    "treatment_cache_hit_rate": 0.0        # No caching in few-shot
}
```

---

## A/B Testing Logic

### Deterministic Assignment

The `VariantSelector` uses deterministic hashing to ensure consistent assignment:

```python
# Combine analysis_id with technique name
hash_input = f"{analysis_id}:{technique}"
hash_value = hash(hash_input) % 100

# Assign based on treatment percentage
treatment_threshold = int(ab_test_treatment_pct * 100)
variant = "treatment" if hash_value < treatment_threshold else "control"
```

### Properties

- ✅ **Deterministic**: Same `analysis_id` always returns same variant for a technique
- ✅ **Per-Technique**: Same analysis can be treatment for few-shot but control for caching
- ✅ **Configurable**: Adjust `TECHNIQUE_AB_TEST_TREATMENT_PCT` for rollout percentage
- ✅ **Instant Rollback**: Set `TECHNIQUE_AB_TEST_ENABLED=false` to disable

### Example Distribution

With `TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2` (20% treatment):

```
1000 analyses:
- ~200 (20%) → treatment group (few-shot ON)
- ~800 (80%) → control group (few-shot OFF)
```

---

## Testing

### Run All Tests

```bash
cd backend

# Feature flags (13 tests)
poetry run pytest tests/unit/core/test_feature_flags.py -v

# Variant selector (16 tests)
poetry run pytest tests/unit/shared/services/ab_testing/ -v

# Metrics (14 tests)
poetry run pytest tests/unit/shared/services/metrics/test_technique_metrics.py -v

# All together (43 tests)
poetry run pytest tests/unit/core/test_feature_flags.py \
                  tests/unit/shared/services/ab_testing/ \
                  tests/unit/shared/services/metrics/test_technique_metrics.py -v
```

### Code Quality

```bash
# Format check
poetry run ruff format --check app/core/feature_flags.py \
                               app/shared/services/ab_testing/ \
                               app/shared/services/metrics/

# Lint
poetry run ruff check app/core/feature_flags.py \
                      app/shared/services/ab_testing/ \
                      app/shared/services/metrics/

# Type check
poetry run mypy app/core/feature_flags.py \
                app/shared/services/ab_testing/ \
                app/shared/services/metrics/ --ignore-missing-imports
```

---

## Rollout Strategy

### Stage 1: Validation (Week 1)

```bash
TECHNIQUE_ENABLE_FEW_SHOT=true
TECHNIQUE_AB_TEST_ENABLED=true
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.1    # 10% treatment
```

**Goal**: Validate no regressions, measure baseline metrics

### Stage 2: Gradual Rollout (Week 2-3)

```bash
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2    # 20% → Week 2
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.5    # 50% → Week 3
```

**Goal**: Increase treatment group, monitor quality improvements

### Stage 3: Full Rollout (Week 4)

```bash
TECHNIQUE_AB_TEST_TREATMENT_PCT=1.0    # 100% treatment
# OR
TECHNIQUE_AB_TEST_ENABLED=false        # Disable A/B, use few-shot everywhere
```

**Goal**: Full production deployment if metrics are positive

### Stage 4: Instant Rollback (If Needed)

```bash
TECHNIQUE_ENABLE_FEW_SHOT=false        # Disable few-shot entirely
# OR
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.0    # 0% treatment (all control)
```

**Goal**: Instant rollback if issues detected

---

## Monitoring & Alerts

### Key Metrics to Track

1. **Quality Score** (LangSmith feedback)
   - Target: +15-25% improvement in treatment vs control
   - Alert: If treatment < control

2. **Latency** (example_retrieval_ms + agent latency)
   - Target: Minimal overhead (<100ms for retrieval)
   - Alert: If treatment latency > 2x control

3. **Token Count** (input + output)
   - Expected: Treatment has more input tokens (examples)
   - Monitor: Cost increase should be justified by quality

4. **Example Retrieval Time**
   - Target: <100ms p95
   - Alert: If >200ms (indicates vector DB performance issue)

### LangSmith Integration

```python
# Track metrics in LangSmith
from langsmith import Client

client = Client()
client.create_feedback(
    run_id=run.id,
    key="quality_score",
    score=quality_score,
    value=quality_score,
)

# Later: Query feedback to populate metrics.quality_score
```

---

## Future Phases

### Phase 2: Chain-of-Thought Supervisor

```python
if flags.enable_cot_supervisor:
    variant = selector.select_variant(analysis_id, "cot_supervisor")
    # Two-phase supervisor routing
```

### Phase 3: Redis Semantic Caching

```python
if flags.enable_redis_cache:
    variant = selector.select_variant(analysis_id, "redis_cache")
    # L2 Redis cache with 92% similarity threshold
```

### Phase 4: Tree-of-Thoughts Resolver

```python
if flags.enable_tot_resolver:
    variant = selector.select_variant(analysis_id, "tot_resolver")
    # Three-expert conflict resolution
```

### Phase 5: ReAct Tracing

```python
if flags.enable_react_tracing:
    variant = selector.select_variant(analysis_id, "react_tracing")
    # Enhanced observability for tool-using agents
```

---

## Troubleshooting

### Issue: All Analyses Getting Same Variant

**Cause**: A/B testing disabled or treatment_pct is 0% or 100%

**Fix**:
```bash
TECHNIQUE_AB_TEST_ENABLED=true
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2
```

### Issue: Variant Changes Between Calls

**Cause**: Bug in hashing logic (should never happen)

**Debug**:
```python
# Verify deterministic assignment
variant1 = selector.select_variant("test-123", "few_shot")
variant2 = selector.select_variant("test-123", "few_shot")
assert variant1 == variant2  # Should always pass
```

### Issue: Metrics Not Recording

**Cause**: Forgot to call `metrics_collector.record(metrics)`

**Fix**:
```python
# Always record metrics after agent completion
metrics.completed_at = time.time()
metrics_collector.record(metrics)
```

---

## References

- **Phase 0 Implementation**: `/Users/yonatangross/coding/SkillForge/backend/app/core/feature_flags.py`
- **Advanced LLM Techniques Plan**: `/Users/yonatangross/coding/SkillForge/docs/advanced-llm-techniques.md`
- **A/B Testing Module**: `/Users/yonatangross/coding/SkillForge/backend/app/shared/services/ab_testing/`
- **Metrics Tracking**: `/Users/yonatangross/coding/SkillForge/backend/app/shared/services/metrics/`

---

**Last Updated:** December 16, 2025
**Status:** Production-Ready (43/43 tests passing, 100% coverage)

# Few-Shot Prompting: Quick Reference Card

**Version:** 1.0
**Last Updated:** December 16, 2025

---

## Enable Few-Shot + A/B Testing

```bash
# .env file
TECHNIQUE_ENABLE_FEW_SHOT=true
TECHNIQUE_AB_TEST_ENABLED=true
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2  # 20% treatment
```

---

## Use in Agent Creation

```python
from app.core.feature_flags import get_technique_flags
from app.shared.services.ab_testing import get_variant_selector
from app.shared.services.metrics.technique_metrics import TechniqueMetrics, metrics_collector

# 1. Check if enabled
flags = get_technique_flags()
if flags.enable_few_shot:
    # 2. Select variant
    selector = get_variant_selector()
    variant = selector.select_variant(analysis_id, "few_shot_prompting")

    # 3. Create agent based on variant
    if variant == "treatment":
        examples = await retrieve_examples(content, agent_type)
        agent = create_few_shot_agent(examples)
    else:
        agent = create_baseline_agent()

    # 4. Track metrics
    metrics = TechniqueMetrics(
        analysis_id=analysis_id,
        technique="few_shot_prompting",
        variant=variant,
        example_retrieval_ms=retrieval_time,
        num_examples_used=len(examples) if variant == "treatment" else 0,
    )
    metrics_collector.record(metrics)
```

---

## Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TECHNIQUE_ENABLE_FEW_SHOT` | bool | false | Enable few-shot prompting |
| `TECHNIQUE_FEW_SHOT_MAX_EXAMPLES` | int | 3 | Max examples per agent |
| `TECHNIQUE_FEW_SHOT_MIN_QUALITY` | float | 0.8 | Min quality score for examples |
| `TECHNIQUE_AB_TEST_ENABLED` | bool | false | Enable A/B testing |
| `TECHNIQUE_AB_TEST_TREATMENT_PCT` | float | 0.2 | Treatment % (0.0-1.0) |

---

## Retrieve Metrics Summary

```python
summary = metrics_collector.get_summary("few_shot_prompting")

print(f"Control:   {summary['control_count']} runs, {summary['control_avg_latency']:.0f}ms avg")
print(f"Treatment: {summary['treatment_count']} runs, {summary['treatment_avg_latency']:.0f}ms avg")
print(f"Improvement: {((summary['control_avg_latency'] - summary['treatment_avg_latency']) / summary['control_avg_latency'] * 100):.1f}%")
```

---

## Test Commands

```bash
cd backend

# All tests (43 tests)
poetry run pytest tests/unit/core/test_feature_flags.py \
                  tests/unit/shared/services/ab_testing/ \
                  tests/unit/shared/services/metrics/test_technique_metrics.py

# Code quality
poetry run ruff format --check app/
poetry run ruff check app/
poetry run mypy app/ --ignore-missing-imports
```

---

## Rollout Strategy

```bash
# Week 1: Validation (10% treatment)
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.1

# Week 2: Gradual rollout (20% treatment)
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2

# Week 3: Wider rollout (50% treatment)
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.5

# Week 4: Full rollout (100% treatment)
TECHNIQUE_AB_TEST_TREATMENT_PCT=1.0

# Rollback: Disable entirely
TECHNIQUE_ENABLE_FEW_SHOT=false
```

---

## Monitoring Checklist

- [ ] **Quality Score**: Treatment > Control by 15-25%
- [ ] **Latency**: Example retrieval < 100ms p95
- [ ] **Token Count**: Input tokens increased (expected)
- [ ] **Cost**: Increase justified by quality gains
- [ ] **Error Rate**: No regressions vs baseline

---

## Key Files

| File | Purpose |
|------|---------|
| `app/core/feature_flags.py` | Feature flag configuration |
| `app/shared/services/ab_testing/variant_selector.py` | A/B testing logic |
| `app/shared/services/metrics/technique_metrics.py` | Metrics tracking |
| `docs/feature-flags-ab-testing.md` | Complete guide |

---

## Common Issues

### All analyses getting same variant

**Fix:**
```bash
TECHNIQUE_AB_TEST_ENABLED=true
TECHNIQUE_AB_TEST_TREATMENT_PCT=0.2
```

### Metrics not recording

**Fix:**
```python
# Always call record() after agent completion
metrics.completed_at = time.time()
metrics_collector.record(metrics)
```

---

**Full Docs:** `/Users/yonatangross/coding/SkillForge/backend/docs/feature-flags-ab-testing.md`

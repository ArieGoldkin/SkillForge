# G-Eval Optimization Summary

**Analysis Date:** 2025-12-17  
**Phase 2 Results:** CoT +11.7%, Few-Shot -4.5% (Target: 15-25%)  
**Full Analysis:** `/backend/docs/g-eval-optimization-analysis.md`

---

## Critical Issues Identified

### 1. No Caching (70-80% cost waste)
- **File:** `/backend/app/shared/services/g_eval/scorer.py:165-216`
- **Issue:** Every G-Eval criterion call makes fresh LLM request
- **Impact:** 15 LLM calls per comparison, no reuse across criteria

### 2. Poor Few-Shot Selection (-4.5% negative improvement)
- **File:** `/backend/scripts/compare_quality_g_eval.py:277-281`
- **Issue:** Uses first 2 examples without quality filtering or diversity check
- **Impact:** Few-shot variant performs WORSE than control

### 3. Rubric Calibration Variance (σ ~20%)
- **File:** `/backend/app/shared/services/g_eval/rubrics.py`
- **Issue:** `learning_path` shows -27.9% CoT improvement (uses default rubrics)
- **Impact:** Inconsistent performance across agent types

### 4. Sequential Variant Generation (3x slower)
- **File:** `/backend/scripts/compare_quality_g_eval.py:197-205`
- **Issue:** Control → Few-Shot → CoT runs sequentially
- **Impact:** ~45s per example vs ~15s with parallelization

### 5. No Token/Cost Tracking
- **File:** N/A (not implemented)
- **Issue:** No visibility into token usage or cost optimization
- **Impact:** Cannot optimize cost-quality trade-offs

---

## Recommended Quick Wins (Phase 1: 1-2 days)

### 1. Add Token Tracking
**Create:** `/backend/app/shared/services/g_eval/cost_tracker.py`  
**Modify:** `/backend/app/shared/services/g_eval/scorer.py`  
**Lines:** Add `TokenUsage` tracking to `_score_criterion` after line 205

```python
# After line 205 in scorer.py
if hasattr(response, "usage_metadata"):
    usage = TokenUsage(
        input_tokens=response.usage_metadata.get("input_tokens", 0),
        output_tokens=response.usage_metadata.get("output_tokens", 0),
    )
    get_cost_tracker().add_usage(usage)
```

**Expected:** Immediate cost visibility, baseline metrics for optimization

---

### 2. Parallelize Variant Generation
**File:** `/backend/scripts/compare_quality_g_eval.py:197-205`  
**Replace sequential awaits with:**

```python
# BEFORE (sequential):
control_output = await run_variant(example, "control")
few_shot_output = await run_variant(example, "few_shot", few_shot_examples)
cot_output = await run_variant(example, "cot")

# AFTER (parallel):
control_output, few_shot_output, cot_output = await asyncio.gather(
    run_variant(example, "control"),
    run_variant(example, "few_shot", few_shot_examples),
    run_variant(example, "cot"),
)
```

**Expected:** 3x faster test execution (~15s vs ~45s per example)

---

### 3. Audit Rubric Coverage
**Create:** `/backend/scripts/audit_rubric_coverage.py` (full code in analysis doc)  
**Run:**
```bash
cd /Users/yonatangross/coding/SkillForge/backend
poetry run python scripts/audit_rubric_coverage.py
```

**Expected Output:**
```
G-Eval Rubric Coverage Audit
============================================================
tech_comparator               ✅ FULL
security_auditor              ✅ FULL
implementation_planner        ✅ FULL
research_analyst              ✅ FULL
performance_analyst           ⚠️  PARTIAL (1/4 default)
learning_path                 ❌ MISSING (uses all defaults)
code_reviewer                 ✅ FULL
```

**Action:** Add specialized rubrics for flagged agents (see Section 3 in analysis doc)

---

### 4. Fix Few-Shot Selection
**Create:** `/backend/app/shared/services/prompts/few_shot_selector.py`  
**Modify:** `/backend/scripts/compare_quality_g_eval.py:277-281`  

**Replace:**
```python
# BEFORE (no filtering):
few_shot_examples = [
    {"input_summary": ex.input_summary, "output_example": ex.output_example}
    for ex in examples[:2]
]

# AFTER (quality + diversity filtering):
from app.shared.services.prompts.few_shot_selector import (
    FewShotExample, select_diverse_examples
)

few_shot_candidates = [
    FewShotExample(
        input_summary=ex.input_summary,
        input_content=ex.input_content_preview,
        output_example=ex.output_example,
        quality_score=ex.quality_score,
        agent_type=ex.agent_type,
    )
    for ex in examples
]

selected_examples = select_diverse_examples(
    few_shot_candidates,
    target_count=2,
    min_quality=0.85,  # High-quality only
)
```

**Expected:** +10-15% improvement in few-shot variant (from -4.5% to +5-10%)

---

## Medium-Term Optimizations (Phase 2: 2-3 days)

### 1. Implement Response-Level Caching
**File:** `/backend/app/shared/services/g_eval/scorer.py:219-299`  
**Add to `g_eval_score` function:**

```python
# Add before line 245 (criteria evaluation)
if use_cache:
    cache_key = _compute_cache_key(input_content, output, agent_type, eval_criteria)
    if cache_key in _g_eval_cache:
        logger.info("g_eval_cache_hit", cache_key=cache_key[:16])
        return _g_eval_cache[cache_key]
```

**Expected:** 100% savings on repeated evaluations (golden dataset tests)

---

### 2. Add Anthropic Prompt Caching
**File:** `/backend/app/shared/services/g_eval/scorer.py:165-216`  
**Modify `_score_criterion` to use cache_control:**

```python
# Replace lines 199-202
messages = [
    SystemMessage(
        content=system_prompt,
        additional_kwargs={"cache_control": {"type": "ephemeral"}}
    ),
    HumanMessage(
        content=user_prompt,
        additional_kwargs={"cache_control": {"type": "ephemeral"}}
    ),
]
```

**Expected:** 70-80% token cost reduction (write → read tokens)

---

## Longer-Term Enhancements (Phase 3-4: 1-2 weeks)

### 1. Add Specialized Rubrics for All Agents
**File:** `/backend/app/shared/services/g_eval/rubrics.py:68-318`  
**Add entries to `AGENT_RUBRICS` dict for:**
- `learning_path` (full example in analysis doc Section 3)
- Any other agents flagged by audit script

**Expected:** Reduced variance (σ from ~20% to <5%), better CoT alignment

---

### 2. Statistical Validation Framework
**File:** `/backend/scripts/compare_quality_g_eval.py`  
**Add:** Confidence intervals, significance testing (scipy.stats)  
**See:** Section 7 in analysis doc for full implementation

**Expected:** Statistically rigorous claims about improvements

---

### 3. Ablation Study Framework
**Create:** `/backend/scripts/ablation_study.py`  
**Purpose:** Isolate impact of individual optimizations  
**See:** Section 7 in analysis doc for configuration structure

**Expected:** Data-driven prioritization of optimizations

---

## File Change Summary

### New Files to Create
```
/backend/app/shared/services/g_eval/cost_tracker.py
/backend/app/shared/services/prompts/few_shot_selector.py
/backend/scripts/audit_rubric_coverage.py
/backend/scripts/ablation_study.py  (optional, Phase 4)
/backend/tests/unit/services/g_eval/test_scorer_cache.py
/backend/tests/unit/services/g_eval/test_cost_tracker.py
/backend/tests/unit/services/g_eval/test_few_shot_selector.py
```

### Files to Modify
```
/backend/app/shared/services/g_eval/scorer.py
  - Add token tracking (lines 205-210)
  - Add response caching (lines 245-250)
  - Add prompt caching (lines 199-202)

/backend/app/shared/services/g_eval/rubrics.py
  - Add specialized rubrics for learning_path, others

/backend/app/shared/services/g_eval/__init__.py
  - Export cost_tracker functions

/backend/scripts/compare_quality_g_eval.py
  - Parallelize variant generation (lines 197-205)
  - Fix few-shot selection (lines 277-281)
  - Add cost reporting (end of run_g_eval_comparison)
  - Add statistical validation (summary section)
```

---

## Expected Cumulative Impact

| Phase | Improvement | Cost Reduction | Speed | Duration |
|-------|-------------|----------------|-------|----------|
| Baseline | +11.7% CoT, -4.5% FS | - | - | - |
| Phase 1 | +15-20% | 0% (tracking only) | 3x faster | 1-2 days |
| Phase 2 | +15-25% | 70-80% | 3x faster | 2-3 days |
| Phase 3 | +20-30% | 70-80% | 3x faster | 3-4 days |

**Total Expected Improvement:** 15-30% quality, 70-80% cost reduction, 3x speed

---

## Next Steps

1. **Review full analysis:** Read `/backend/docs/g-eval-optimization-analysis.md`
2. **Run rubric audit:** `poetry run python scripts/audit_rubric_coverage.py`
3. **Implement Phase 1:** Token tracking + parallelization (quick wins)
4. **Validate improvements:** Re-run comparison with optimizations
5. **Iterate:** Add caching → enhanced rubrics → ablation studies

---

## Reference Files

- **Full Analysis:** `/backend/docs/g-eval-optimization-analysis.md`
- **Phase 2 Report:** `/backend/docs/phase2-g-eval-comparison-report.md`
- **G-Eval Scorer:** `/backend/app/shared/services/g_eval/scorer.py`
- **Rubrics:** `/backend/app/shared/services/g_eval/rubrics.py`
- **Comparison Script:** `/backend/scripts/compare_quality_g_eval.py`
- **CoT Prompts:** `/backend/app/shared/services/prompts/chain_of_thought.py`

---

**For questions or implementation guidance, refer to the full analysis document.**

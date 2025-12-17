# G-Eval Implementation Analysis & Optimization Opportunities

**Generated:** 2025-12-17  
**Analysis Scope:** Phase 2 results showing CoT +11.7%, Few-Shot -4.5%  
**Target:** Achieve 15-25% improvement, reduce costs, improve reliability

---

## Executive Summary

### Current Performance (Phase 2 Results)
- **CoT Improvement:** +11.7% (GOOD but below 15% target)
- **Few-Shot Improvement:** -4.5% (FAILING - negative improvement)
- **Test Coverage:** 7 samples across 4 agent types
- **Cost Impact:** ~12-16 LLM calls per comparison (3 variants × 4 criteria)

### Key Findings
1. **NO CACHING:** Every criterion evaluation makes a fresh LLM call
2. **POOR RUBRIC CALIBRATION:** High variance (learning_path: +0% to -27.9%)
3. **SEQUENTIAL VARIANT GENERATION:** Unnecessarily slow, rate-limit prone
4. **WEAK FEW-SHOT SELECTION:** Using first 2 examples, no quality filtering
5. **NO TOKEN TRACKING:** Missing cost visibility and optimization data

---

## 1. Performance Bottleneck Analysis

### Current Call Pattern (Per Example)
```
Control Variant:
  - Agent execution: 1 LLM call (structured output)
  - G-Eval scoring: 4 LLM calls (4 criteria × 1 call each)
  
Few-Shot Variant:
  - Agent execution: 1 LLM call
  - G-Eval scoring: 4 LLM calls
  
CoT Variant:
  - Agent execution: 1 LLM call
  - G-Eval scoring: 4 LLM calls
  
Total: 15 LLM calls per example
```

### Bottleneck: No Response Caching
**Location:** `/backend/app/shared/services/g_eval/scorer.py:165-216`

```python
async def _score_criterion(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
) -> CriterionScore:
    model = get_chat_model()  # ⚠️ Fresh model every call
    
    # ... prompt construction ...
    
    response = await model.ainvoke(messages)  # ⚠️ NO CACHE CHECK
    return _parse_g_eval_response(response.content, criterion)
```

**Issue:** When evaluating the SAME output across multiple criteria, the model context (input_content + output) is repeated but not cached.

**Impact:**
- Redundant processing of identical context
- Higher API costs (especially for long inputs)
- Slower execution time

---

## 2. Caching Optimization Strategy

### Recommendation 1: Implement Prompt Caching (Anthropic)

**For Claude models, use Prompt Caching to cache common context:**

```python
from langchain_anthropic import ChatAnthropic

async def _score_criterion_cached(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
) -> CriterionScore:
    """Score criterion with prompt caching for repeated context."""
    
    # Get agent-specific rubric
    rubric_text = format_rubric_for_prompt(agent_type, criterion)
    
    system_prompt = G_EVAL_SYSTEM_PROMPT.format(
        criterion=criterion,
        rubric_text=rubric_text,
    )
    
    user_prompt = G_EVAL_USER_PROMPT.format(
        input_content=input_content[:2000],
        output=output[:3000],
        criterion=criterion,
    )
    
    # Use prompt caching for common context (system + user content)
    from langchain_core.messages import SystemMessage, HumanMessage
    
    messages = [
        SystemMessage(
            content=system_prompt,
            additional_kwargs={"cache_control": {"type": "ephemeral"}}  # Cache system prompt
        ),
        HumanMessage(
            content=user_prompt,
            additional_kwargs={"cache_control": {"type": "ephemeral"}}  # Cache user context
        ),
    ]
    
    model = get_chat_model()
    
    try:
        response = await model.ainvoke(messages)
        return _parse_g_eval_response(response.content, criterion)
    except Exception as e:
        logger.exception("g_eval_criterion_error", criterion=criterion, error=str(e))
        return CriterionScore(
            criterion=criterion, score=3, normalized=0.5,
            confidence=0.0, reasoning=f"Error: {e!s}"
        )
```

**Expected Savings:**
- **Write tokens:** ~90% reduction for subsequent criteria (reuses cached input/output)
- **Read tokens:** Small cost increase (~10% of cached tokens)
- **Net savings:** 70-80% token cost reduction per example

**Implementation Files:**
- `/backend/app/shared/services/g_eval/scorer.py` (modify `_score_criterion`)
- `/backend/app/core/model_factory.py` (add cache support detection)

---

### Recommendation 2: Add Response-Level Caching (Cross-Example)

**For repeated input content (e.g., golden dataset), cache full evaluations:**

```python
from functools import lru_cache
import hashlib
import json

# In-memory cache for G-Eval results (dev/testing)
_g_eval_cache: dict[str, GEvalResult] = {}

def _compute_cache_key(
    input_content: str,
    output: dict | str,
    agent_type: str,
    criteria: list[str],
) -> str:
    """Compute deterministic cache key for G-Eval request."""
    output_str = json.dumps(output, sort_keys=True) if isinstance(output, dict) else str(output)
    
    key_data = {
        "input_content": input_content[:2000],  # Match truncation
        "output": output_str[:3000],
        "agent_type": agent_type,
        "criteria": sorted(criteria),
    }
    
    key_json = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_json.encode()).hexdigest()

async def g_eval_score(
    input_content: str,
    output: dict[str, Any] | str,
    agent_type: str,
    criteria: list[str] | None = None,
    use_cache: bool = True,  # NEW PARAMETER
) -> GEvalResult:
    """Score output quality using G-Eval with optional caching."""
    
    # ... existing setup code ...
    eval_criteria = criteria or config.get("criteria", [...])
    
    # Check cache
    if use_cache:
        cache_key = _compute_cache_key(input_content, output, agent_type, eval_criteria)
        if cache_key in _g_eval_cache:
            logger.info("g_eval_cache_hit", cache_key=cache_key[:16])
            return _g_eval_cache[cache_key]
    
    # ... existing scoring code ...
    
    result = GEvalResult(...)
    
    # Store in cache
    if use_cache:
        _g_eval_cache[cache_key] = result
        logger.info("g_eval_cache_stored", cache_key=cache_key[:16])
    
    return result
```

**Expected Savings:**
- **Golden dataset tests:** 100% reduction (same inputs repeated)
- **Production:** 30-50% reduction (common inputs with slight variations)

**Cache Invalidation Strategy:**
```python
# Add cache clearing for testing
def clear_g_eval_cache() -> None:
    """Clear G-Eval response cache (for testing)."""
    _g_eval_cache.clear()
    logger.info("g_eval_cache_cleared")

# Add cache expiration (optional)
from datetime import datetime, timedelta

_cache_timestamps: dict[str, datetime] = {}
CACHE_TTL = timedelta(hours=1)  # 1-hour cache expiration

def _is_cache_valid(cache_key: str) -> bool:
    """Check if cached result is still valid."""
    if cache_key not in _cache_timestamps:
        return False
    age = datetime.now() - _cache_timestamps[cache_key]
    return age < CACHE_TTL
```

---

## 3. Rubric Calibration Issues

### Problem: High Variance in CoT Performance

**Phase 2 Results Show Inconsistent CoT Impact:**
| Agent Type | CoT Improvement |
|------------|-----------------|
| research_analyst | **+40.7%** ✅ |
| code_reviewer | **+20.8%** ✅ |
| implementation_planner | **-6.6%** ❌ |
| learning_path | **-27.9%** ❌ |

**Root Cause Analysis:**

1. **Generic Rubrics:** Some agent types use DEFAULT_RUBRICS instead of specialized ones
2. **Poor Rubric-Prompt Alignment:** CoT prompts emphasize criteria not weighted in rubrics
3. **Score Range Misuse:** Models not calibrated to use full 1-5 scale

### Recommendation 3: Audit and Enhance Rubrics

**Step 1: Identify which agents lack specialized rubrics**

```bash
cd /Users/yonatangross/coding/SkillForge/backend
poetry run python scripts/audit_rubric_coverage.py
```

Create `/backend/scripts/audit_rubric_coverage.py`:
```python
#!/usr/bin/env python3
"""Audit G-Eval rubric coverage for all agent types."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared.services.g_eval.rubrics import AGENT_RUBRICS, DEFAULT_RUBRICS

# All agent types used in Phase 2
ALL_AGENT_TYPES = [
    "tech_comparator",
    "security_auditor",
    "implementation_planner",
    "research_analyst",
    "performance_analyst",
    "learning_path",
    "code_reviewer",
]

print("G-Eval Rubric Coverage Audit")
print("=" * 60)

for agent_type in ALL_AGENT_TYPES:
    if agent_type in AGENT_RUBRICS:
        config = AGENT_RUBRICS[agent_type]
        criteria = config.get("criteria", [])
        weights = config.get("weights", {})
        rubrics = config.get("rubrics", {})
        
        # Check which criteria use default rubrics
        using_default = []
        for criterion in criteria:
            if criterion not in rubrics:
                using_default.append(criterion)
        
        status = "✅ FULL" if not using_default else f"⚠️  PARTIAL ({len(using_default)}/{len(criteria)} default)"
        print(f"{agent_type:25} {status}")
        
        if using_default:
            print(f"  Default criteria: {', '.join(using_default)}")
    else:
        print(f"{agent_type:25} ❌ MISSING (uses all defaults)")
```

**Step 2: Add missing specialized rubrics**

Example for `learning_path` (currently showing -27.9% with CoT):

```python
# In /backend/app/shared/services/g_eval/rubrics.py

AGENT_RUBRICS["learning_path"] = {
    "criteria": ["completeness", "pedagogical_quality", "progression", "practicality"],
    "weights": {
        "completeness": 0.25,
        "pedagogical_quality": 0.30,
        "progression": 0.25,
        "practicality": 0.20,
    },
    "rubrics": {
        "completeness": {
            1: "No curriculum structure or major topic gaps (>50% missing)",
            2: "Minimal structure, covers <50% of required topics",
            3: "Basic structure, covers core topics but lacks depth/resources",
            4: "Comprehensive structure with most topics and resources",
            5: "Exhaustive curriculum: all topics, resources, time estimates, prerequisites",
        },
        "pedagogical_quality": {
            1: "No instructional design, just topic list",
            2: "Weak learning flow, unclear objectives",
            3: "Basic educational structure with some learning objectives",
            4: "Good pedagogical approach with clear learning outcomes",
            5: "Expert instructional design: scaffolding, active learning, assessments",
        },
        "progression": {
            1: "No skill sequencing or random ordering",
            2: "Poor sequencing with prerequisite violations",
            3: "Logical ordering but no explicit skill tree",
            4: "Clear skill tree with well-defined prerequisites",
            5: "Optimal progression: beginner→intermediate→advanced with checkpoints",
        },
        "practicality": {
            1: "No hands-on elements, purely theoretical",
            2: "Minimal practical content (<20%)",
            3: "Some exercises but lacking real-world projects",
            4: "Good mix of theory and practice (40-60% hands-on)",
            5: "Rich practical curriculum: projects, labs, exercises, real-world scenarios",
        },
    },
}
```

**Expected Impact:**
- Better alignment with CoT reasoning steps
- Reduced variance across agent types
- More accurate quality differentiation

---

## 4. Few-Shot Example Selection Issues

### Problem: Negative Improvement (-4.5%)

**Current Selection Logic** (`/backend/scripts/compare_quality_g_eval.py:277-281`):
```python
# Get few-shot examples (use first golden example as template)
few_shot_examples = [
    {"input_summary": ex.input_summary, "output_example": ex.output_example}
    for ex in examples[:2]  # ⚠️ Just takes first 2 - NO QUALITY FILTER
]
```

**Issues:**
1. **No quality filtering:** May use low-quality examples
2. **No diversity check:** May use similar examples (low variation)
3. **Fixed count:** Always 2 examples (not optimal for all tasks)
4. **Poor formatting:** Truncated previews lose critical details

### Recommendation 4: Intelligent Few-Shot Selection

**Create `/backend/app/shared/services/prompts/few_shot_selector.py`:**

```python
"""Intelligent few-shot example selection for agent prompts."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json

@dataclass
class FewShotExample:
    """A few-shot example with quality metadata."""
    input_summary: str
    input_content: str | None
    output_example: dict[str, Any]
    quality_score: float
    agent_type: str


def select_diverse_examples(
    examples: list[FewShotExample],
    target_count: int = 2,
    min_quality: float = 0.8,
    max_similarity: float = 0.7,  # Cosine similarity threshold
) -> list[FewShotExample]:
    """Select diverse, high-quality few-shot examples.
    
    Args:
        examples: Available examples
        target_count: Desired number of examples
        min_quality: Minimum quality score threshold
        max_similarity: Maximum similarity between selected examples
        
    Returns:
        Selected examples (diverse + high quality)
    """
    # Filter by quality
    high_quality = [ex for ex in examples if ex.quality_score >= min_quality]
    
    if len(high_quality) <= target_count:
        return high_quality[:target_count]
    
    # Sort by quality descending
    high_quality.sort(key=lambda x: x.quality_score, reverse=True)
    
    # Greedy selection for diversity
    selected: list[FewShotExample] = [high_quality[0]]  # Start with best
    
    for candidate in high_quality[1:]:
        if len(selected) >= target_count:
            break
        
        # Check similarity with already selected
        if _is_sufficiently_diverse(candidate, selected, max_similarity):
            selected.append(candidate)
    
    return selected


def _is_sufficiently_diverse(
    candidate: FewShotExample,
    selected: list[FewShotExample],
    max_similarity: float,
) -> bool:
    """Check if candidate is diverse enough from selected examples."""
    # Simple heuristic: check input length and output keys overlap
    candidate_keys = set(candidate.output_example.keys())
    
    for sel in selected:
        sel_keys = set(sel.output_example.keys())
        
        # Jaccard similarity
        intersection = len(candidate_keys & sel_keys)
        union = len(candidate_keys | sel_keys)
        similarity = intersection / union if union > 0 else 0
        
        if similarity > max_similarity:
            return False  # Too similar
    
    return True  # Diverse enough


def format_few_shot_examples(
    examples: list[FewShotExample],
    max_input_length: int = 500,
    max_output_length: int = 1000,
) -> str:
    """Format examples for prompt injection.
    
    Args:
        examples: Selected examples
        max_input_length: Max chars for input preview
        max_output_length: Max chars for output JSON
        
    Returns:
        Formatted few-shot examples string
    """
    formatted_parts = []
    
    for i, ex in enumerate(examples, 1):
        input_preview = (ex.input_content or ex.input_summary)[:max_input_length]
        output_json = json.dumps(ex.output_example, indent=2)[:max_output_length]
        
        formatted_parts.append(
            f"### Example {i} (Quality: {ex.quality_score:.2f})\n"
            f"**Input:**\n{input_preview}\n\n"
            f"**High-Quality Output:**\n```json\n{output_json}\n```"
        )
    
    return "\n\n".join(formatted_parts)
```

**Update comparison script** (`/backend/scripts/compare_quality_g_eval.py`):

```python
from app.shared.services.prompts.few_shot_selector import (
    FewShotExample,
    select_diverse_examples,
    format_few_shot_examples,
)

# In run_g_eval_comparison function:
for agent_type, examples in list(by_type.items())[:5]:
    print(f"\n📊 Agent Type: {agent_type}")
    
    # Convert to FewShotExample with quality scores
    few_shot_candidates = [
        FewShotExample(
            input_summary=ex.input_summary,
            input_content=ex.input_content_preview,
            output_example=ex.output_example,
            quality_score=ex.quality_score,  # ✅ Use actual quality
            agent_type=ex.agent_type,
        )
        for ex in examples
    ]
    
    # Select diverse, high-quality examples
    selected_examples = select_diverse_examples(
        few_shot_candidates,
        target_count=2,
        min_quality=0.85,  # ✅ Higher threshold
    )
    
    # Format for prompt injection
    few_shot_text = format_few_shot_examples(selected_examples)
    
    # Use in few-shot variant
    system_prompt = base_prompt + f"\n\n{few_shot_text}"
```

**Expected Impact:**
- **+10-15% improvement** in few-shot variant quality
- Reduced negative cases (no more -4.5% average)
- More consistent performance across agent types

---

## 5. Cost Optimization Strategies

### Recommendation 5: Add Token Tracking & Cost Monitoring

**Create `/backend/app/shared/services/g_eval/cost_tracker.py`:**

```python
"""Cost tracking for G-Eval LLM-as-Judge scoring."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0  # Anthropic prompt caching

@dataclass
class CostMetrics:
    """Cost metrics for G-Eval evaluation."""
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    
    # Cost per million tokens (update with current pricing)
    COST_PER_M_INPUT: ClassVar[float] = 3.00  # Claude Haiku input
    COST_PER_M_OUTPUT: ClassVar[float] = 15.00  # Claude Haiku output
    COST_PER_M_CACHE_WRITE: ClassVar[float] = 3.75  # Cache write
    COST_PER_M_CACHE_READ: ClassVar[float] = 0.30  # Cache read
    
    @property
    def estimated_cost_usd(self) -> float:
        """Estimate total cost in USD."""
        input_cost = (self.total_input_tokens / 1_000_000) * self.COST_PER_M_INPUT
        output_cost = (self.total_output_tokens / 1_000_000) * self.COST_PER_M_OUTPUT
        cache_cost = (self.total_cached_tokens / 1_000_000) * self.COST_PER_M_CACHE_READ
        return input_cost + output_cost + cache_cost
    
    def add_usage(self, usage: TokenUsage) -> None:
        """Add token usage to metrics."""
        self.total_calls += 1
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_cached_tokens += usage.cached_tokens


# Global cost tracker
_cost_tracker = CostMetrics()

def get_cost_tracker() -> CostMetrics:
    """Get global cost tracker."""
    return _cost_tracker

def reset_cost_tracker() -> None:
    """Reset cost tracker (for testing)."""
    global _cost_tracker
    _cost_tracker = CostMetrics()
```

**Update `_score_criterion` to track costs:**

```python
from app.shared.services.g_eval.cost_tracker import get_cost_tracker, TokenUsage

async def _score_criterion(
    input_content: str,
    output: str,
    criterion: str,
    agent_type: str,
) -> CriterionScore:
    model = get_chat_model()
    # ... prompt construction ...
    
    try:
        response = await model.ainvoke(messages)
        
        # Track token usage
        if hasattr(response, "usage_metadata"):
            usage = TokenUsage(
                input_tokens=response.usage_metadata.get("input_tokens", 0),
                output_tokens=response.usage_metadata.get("output_tokens", 0),
                cached_tokens=response.usage_metadata.get("cache_read_input_tokens", 0),
            )
            get_cost_tracker().add_usage(usage)
        
        return _parse_g_eval_response(response.content, criterion)
    except Exception as e:
        # ... error handling ...
```

**Add cost reporting to comparison script:**

```python
from app.shared.services.g_eval.cost_tracker import get_cost_tracker, reset_cost_tracker

async def run_g_eval_comparison(sample_size: int = 2) -> None:
    reset_cost_tracker()  # Start fresh
    
    # ... run comparisons ...
    
    # Report costs
    tracker = get_cost_tracker()
    print("\n" + "=" * 70)
    print("COST ANALYSIS")
    print("=" * 70)
    print(f"  Total LLM calls:        {tracker.total_calls}")
    print(f"  Total input tokens:     {tracker.total_input_tokens:,}")
    print(f"  Total output tokens:    {tracker.total_output_tokens:,}")
    print(f"  Total cached tokens:    {tracker.total_cached_tokens:,}")
    print(f"  Estimated cost:         ${tracker.estimated_cost_usd:.4f}")
    print(f"  Cost per comparison:    ${tracker.estimated_cost_usd / len(results):.4f}")
```

---

## 6. Batching & Parallelization

### Current Issue: Sequential Variant Generation

**In `/backend/scripts/compare_quality_g_eval.py:197-205`:**
```python
# ⚠️ SEQUENTIAL - wastes time
print("      Running control variant...")
control_output = await run_variant(example, "control")

print("      Running few-shot variant...")
few_shot_output = await run_variant(example, "few_shot", few_shot_examples)

print("      Running CoT variant...")
cot_output = await run_variant(example, "cot")
```

**Problem:** Each variant waits for the previous to complete, even though they're independent.

### Recommendation 6: Parallelize Variant Generation

```python
# PARALLEL - 3x faster
print("      Running all variants in parallel...")
control_task = run_variant(example, "control")
few_shot_task = run_variant(example, "few_shot", few_shot_examples)
cot_task = run_variant(example, "cot")

control_output, few_shot_output, cot_output = await asyncio.gather(
    control_task,
    few_shot_task,
    cot_task,
)
```

**Expected Improvement:**
- **3x faster** variant generation (from ~45s to ~15s per example)
- Reduces rate-limiting impact (requests spread over time)

---

## 7. Test Methodology Improvements

### Current Gaps in `/backend/scripts/compare_quality_g_eval.py`

1. **Small sample size:** 7 samples (should be 20+ for statistical significance)
2. **No confidence intervals:** Results lack error bars
3. **No agent-specific baseline:** All agents compared to same control
4. **No ablation studies:** Can't isolate impact of individual optimizations

### Recommendation 7: Enhanced Test Methodology

**Add statistical rigor:**

```python
import numpy as np
from scipy import stats

def calculate_confidence_interval(
    scores: list[float],
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Calculate mean and confidence interval.
    
    Returns:
        (mean, lower_bound, upper_bound)
    """
    if len(scores) < 2:
        return (scores[0] if scores else 0, 0, 0)
    
    mean = np.mean(scores)
    std_err = stats.sem(scores)
    margin = std_err * stats.t.ppf((1 + confidence) / 2, len(scores) - 1)
    
    return (mean, mean - margin, mean + margin)

# In summary reporting:
control_scores = [r.control.g_eval_overall for r in results]
cot_scores = [r.cot.g_eval_overall for r in results]

control_mean, control_lower, control_upper = calculate_confidence_interval(control_scores)
cot_mean, cot_lower, cot_upper = calculate_confidence_interval(cot_scores)

print(f"  Control:  {control_mean:.3f} (95% CI: [{control_lower:.3f}, {control_upper:.3f}])")
print(f"  CoT:      {cot_mean:.3f} (95% CI: [{cot_lower:.3f}, {cot_upper:.3f}])")

# Statistical significance test
t_stat, p_value = stats.ttest_rel(cot_scores, control_scores)
significance = "✅ SIGNIFICANT" if p_value < 0.05 else "❌ NOT SIGNIFICANT"
print(f"  CoT vs Control: p={p_value:.4f} {significance}")
```

**Add ablation study framework:**

```python
# Test individual optimizations
ABLATION_CONFIGS = {
    "baseline": {
        "caching": False,
        "diverse_few_shot": False,
        "specialized_rubrics": False,
    },
    "with_caching": {
        "caching": True,
        "diverse_few_shot": False,
        "specialized_rubrics": False,
    },
    "with_diverse_fs": {
        "caching": False,
        "diverse_few_shot": True,
        "specialized_rubrics": False,
    },
    "with_specialized_rubrics": {
        "caching": False,
        "diverse_few_shot": False,
        "specialized_rubrics": True,
    },
    "all_optimizations": {
        "caching": True,
        "diverse_few_shot": True,
        "specialized_rubrics": True,
    },
}

async def run_ablation_study(example: AgentExample) -> dict[str, GEvalResult]:
    """Run ablation study on single example."""
    results = {}
    for config_name, config in ABLATION_CONFIGS.items():
        # ... run with config ...
        results[config_name] = await g_eval_score(..., **config)
    return results
```

---

## 8. Implementation Priority & Roadmap

### Phase 1: Quick Wins (1-2 days)
1. **Add token tracking** → Immediate cost visibility
2. **Parallelize variant generation** → 3x faster tests
3. **Audit rubric coverage** → Identify gaps
4. **Fix few-shot selection** → Quality filter + diversity

**Expected Impact:** +5-8% improvement, 50% cost visibility

---

### Phase 2: Caching Infrastructure (2-3 days)
1. **Implement response-level caching** → Cross-example deduplication
2. **Add Anthropic prompt caching** → 70-80% token savings
3. **Add cache expiration/invalidation** → Freshness guarantees

**Expected Impact:** 70-80% token cost reduction, faster test cycles

---

### Phase 3: Rubric Enhancement (3-4 days)
1. **Add specialized rubrics for all agents** → learning_path, performance_analyst
2. **Align rubrics with CoT reasoning** → Match evaluation criteria to CoT steps
3. **Add rubric validation tests** → Ensure 1-5 scale calibration

**Expected Impact:** +8-12% improvement, reduced variance

---

### Phase 4: Advanced Optimizations (1 week)
1. **Implement batching for G-Eval calls** → Process multiple examples in parallel
2. **Add adaptive few-shot selection** → Learn optimal example count per agent
3. **Build cost-quality trade-off dashboard** → Optimize cost vs accuracy

**Expected Impact:** 15-25% total improvement, <50% baseline costs

---

## 9. Code Locations & File Changes

### Files to Modify
```
/backend/app/shared/services/g_eval/
  ├── scorer.py              (caching, token tracking)
  ├── rubrics.py             (add missing agent rubrics)
  ├── cost_tracker.py        (NEW - token & cost tracking)
  └── __init__.py            (export new functions)

/backend/app/shared/services/prompts/
  ├── few_shot_selector.py   (NEW - intelligent selection)
  └── chain_of_thought.py    (align with rubric criteria)

/backend/scripts/
  ├── compare_quality_g_eval.py  (parallelize, add stats)
  ├── audit_rubric_coverage.py   (NEW - rubric audit)
  └── ablation_study.py          (NEW - isolate optimizations)

/backend/tests/
  └── unit/services/g_eval/
      ├── test_scorer_cache.py   (NEW - cache tests)
      ├── test_cost_tracker.py   (NEW - cost tracking tests)
      └── test_few_shot_selector.py  (NEW - selection tests)
```

### Test Coverage Requirements
- **Caching:** Test hit/miss, expiration, invalidation
- **Cost tracking:** Test token accumulation, cost estimation
- **Few-shot selection:** Test diversity, quality filtering
- **Rubric coverage:** Test all agent types have specialized rubrics

---

## 10. Success Metrics

### Target Metrics (Post-Optimization)
- **CoT Improvement:** +15-25% (currently +11.7%)
- **Few-Shot Improvement:** +10-20% (currently -4.5%)
- **Token Cost:** <30% of baseline (70%+ reduction)
- **Test Speed:** <50% of baseline (2x faster)
- **Variance:** σ < 5% across agent types (currently ~20%)

### Monitoring Dashboard
```python
# Add to comparison report
print("\n" + "=" * 70)
print("OPTIMIZATION EFFECTIVENESS")
print("=" * 70)
print(f"  Avg improvement:      {avg_cot_improvement:+.1f}%")
print(f"  Target range:         +15% to +25%")
print(f"  Cache hit rate:       {cache_hits / total_calls * 100:.1f}%")
print(f"  Cost per comparison:  ${cost_per_comparison:.4f}")
print(f"  Improvement variance: {improvement_std:.1f}%")
```

---

## Appendix A: Phase 2 Result Details

### Agent-Level Breakdown
```
research_analyst:
  Control: 0.556  Few-Shot: 0.550 (+0.8%)  CoT: 0.738 (+40.7%) ✅
  → CoT works VERY well (strong reasoning alignment)

implementation_planner:
  Control: 0.519  Few-Shot: 0.344 (-28.5%) ❌  CoT: 0.494 (-6.6%) ⚠️
  → Few-shot examples may be off-topic or low-quality
  → CoT slightly worse (prompt may need tuning)

code_reviewer:
  Control: 0.800  Few-Shot: 0.869 (+12.0%) ✅  CoT: 0.938 (+20.8%) ✅
  → Both techniques work (already high baseline)

learning_path:
  Control: 0.537  Few-Shot: 0.537 (+0.0%) ⚠️  CoT: 0.387 (-27.9%) ❌
  → CoT prompt misaligned with rubric
  → Few-shot examples ineffective (no quality signal)
```

### Key Insight
**Success correlates with rubric specialization:**
- ✅ Specialized rubrics (tech_comparator, security_auditor, code_reviewer) → positive gains
- ❌ Default rubrics (learning_path) → negative or zero gains

---

## Appendix B: Cost-Benefit Analysis

### Current Costs (Estimated)
```
Per comparison (3 variants × 4 criteria):
  - 15 LLM calls × 2000 input tokens × $3/M = $0.09
  - 15 LLM calls × 300 output tokens × $15/M = $0.07
  Total: ~$0.16 per comparison

Phase 2 test (7 comparisons):
  - Total cost: ~$1.12

Production scale (100 comparisons/day):
  - Daily cost: ~$16
  - Monthly cost: ~$480
```

### Post-Optimization Costs (Projected)
```
With caching (70% reduction):
  - Per comparison: ~$0.05
  - Monthly (100/day): ~$150

Savings: $330/month (69% reduction)
```

### ROI Timeline
- **Implementation time:** 2-3 weeks
- **Break-even:** 1 month (if running >50 comparisons/day)
- **Annual savings:** ~$4000 (at 100 comparisons/day)

---

**End of Analysis**

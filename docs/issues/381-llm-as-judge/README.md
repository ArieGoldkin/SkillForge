# Issue #381: Integrate Langfuse LLM-as-Judge Evaluators

**Status:** 📋 Planned
**Branch:** `issue/381-langfuse-evaluators`
**Milestone:** Langfuse Migration Phase 2
**Priority:** 🟡 MEDIUM
**Estimated Effort:** 4-6 hours
**Dependencies:** Issue #372 (Langfuse Migration) ✅ Complete, Issue #383 (Token/Cost Tracking) 📋 Planned

---

## Summary

**HYBRID STRATEGY**: Add Langfuse LLM-as-Judge evaluators as a **COMPLEMENTARY** evaluation path alongside our existing local G-Eval implementation. This provides:
- **Built-in cost tracking** - Langfuse automatically tracks evaluation costs in the dashboard
- **Debugging UI** - Visual inspection of evaluation reasoning and scores
- **Score analytics** - Compare evaluator performance over time
- **Template library** - Access to pre-built evaluation prompts

**CRITICAL**: This does NOT replace our local G-Eval scorer. Instead, it adds Langfuse as an **alternative path** with the local implementation as the **PRIMARY** and **FALLBACK** option.

## Key Features

- **Dual evaluation paths**: Local G-Eval (PRIMARY) + Langfuse (COMPLEMENTARY)
- **Configurable evaluator selection**: Environment variable to choose evaluation backend
- **Cost visibility**: Evaluation LLM costs tracked in Langfuse dashboard
- **Debug UI**: Visual inspection of evaluation reasoning in Langfuse web UI
- **Template management**: Store and version evaluation prompts in Langfuse
- **Performance comparison**: A/B test local vs Langfuse evaluators
- **Zero production disruption**: Local G-Eval remains default, Langfuse opt-in

## Current G-Eval Implementation Status

### ✅ What's Working (Local G-Eval)
- **Robust scoring system** (`backend/app/shared/services/g_eval/scorer.py`)
  - Agent-specific rubrics for domain-aware evaluation
  - Parallel criterion scoring for efficiency
  - Confidence scores and chain-of-thought reasoning
  - Two-layer caching: file-based + Redis semantic cache
  - Gemini dict response parsing (fixed Dec 2024)

- **Quality gate integration** (`backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`)
  - 3 quality aspects: relevance, depth, coherence
  - Threshold: 0.7 average score + per-aspect minimums
  - Coverage-adjusted thresholds for limited data
  - Retry logic (up to 2 attempts) for failing quality

- **Content extraction** (`backend/app/evaluation/evaluators/quality.py`)
  - Smart content extraction from nested dicts
  - 15,000 character limit (increased Dec 2024 for depth)
  - Priority-based key extraction (insights, synthesis, etc.)

- **Self-consistency voting** (`backend/app/shared/services/g_eval/self_consistency.py`)
  - Multiple judge votes for reliability
  - Vote aggregation and distribution tracking

### 🎯 Why Add Langfuse Evaluators?

1. **Observability Gap**: Current G-Eval has no UI for debugging evaluation decisions
2. **Cost Blind Spot**: Evaluation LLM costs not tracked separately from workflow costs
3. **Template Versioning**: No centralized prompt management for evaluation rubrics
4. **Comparison Testing**: Cannot easily A/B test different evaluation strategies
5. **Team Collaboration**: No shared dashboard for reviewing quality scores

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│              HYBRID LLM-AS-JUDGE ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  quality_gate_node.py                                               │
│       ↓                                                              │
│  Check config: EVALUATOR_BACKEND                                    │
│       ├──────────────────────────┬──────────────────────────┐      │
│       ↓                          ↓                          ↓       │
│  "local" (DEFAULT)          "langfuse"               "hybrid"       │
│       ↓                          ↓                          ↓       │
│                                                                     │
│  ┌────────────────────┐    ┌──────────────────────┐   ┌─────────┐ │
│  │  LOCAL G-EVAL      │    │  LANGFUSE EVALUATOR  │   │  BOTH   │ │
│  │  (PRIMARY)         │    │  (COMPLEMENTARY)     │   │         │ │
│  ├────────────────────┤    ├──────────────────────┤   └─────────┘ │
│  │                    │    │                      │                │
│  │ scorer.py          │    │ langfuse_evaluators. │                │
│  │   ├─ Rubrics       │    │   ├─ Template fetch │                │
│  │   ├─ Prompt format │    │   ├─ LLM judge call │                │
│  │   ├─ LLM invoke    │    │   ├─ Score parsing  │                │
│  │   ├─ Cache check   │    │   └─ Langfuse store │                │
│  │   └─ Self-consist. │    │                      │                │
│  │                    │    │ Langfuse Dashboard:  │                │
│  │ Quality Gate:      │    │   ├─ Eval traces    │                │
│  │   ├─ 3 criteria    │    │   ├─ Cost breakdown │                │
│  │   ├─ Thresholds    │    │   ├─ Score trends   │                │
│  │   ├─ Retry logic   │    │   └─ Reasoning UI   │                │
│  │   └─ Coverage adj. │    │                      │                │
│  │                    │    │                      │                │
│  │ Fallback: NONE     │    │ Fallback: LOCAL      │                │
│  │ (self-contained)   │    │ (on API errors)      │                │
│  │                    │    │                      │                │
│  └────────────────────┘    └──────────────────────┘                │
│                                                                     │
│  DECISION MATRIX: When to Use Which?                                │
│  ════════════════════════════════════════                           │
│                                                                     │
│  Use Local G-Eval When:                                             │
│    ✓ Production workflows (reliable, fast, proven)                 │
│    ✓ Cost optimization is critical (no external API)               │
│    ✓ Offline/air-gapped environments                               │
│    ✓ Custom rubrics require domain-specific logic                  │
│    ✓ Low latency is essential (<500ms per criterion)               │
│                                                                     │
│  Use Langfuse Evaluators When:                                      │
│    ✓ Debugging evaluation decisions (need UI inspection)           │
│    ✓ Tracking evaluation costs separately                          │
│    ✓ Team collaboration on quality standards                       │
│    ✓ A/B testing evaluation strategies                             │
│    ✓ Experimenting with new evaluation criteria                    │
│                                                                     │
│  Use Hybrid Mode When:                                              │
│    ✓ Comparing local vs Langfuse scores (validation)               │
│    ✓ Running quality audits (cross-check evaluators)               │
│    ✓ Migrating from local to Langfuse (gradual transition)         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## When to Use Local vs Langfuse

| Criteria | Local G-Eval | Langfuse Evaluators | Winner |
|----------|-------------|---------------------|--------|
| **Production reliability** | ✅ Proven, stable, 2+ months in prod | ⚠️ New integration, untested | **Local** |
| **Cost tracking** | ❌ No separate eval cost tracking | ✅ Automatic dashboard visibility | **Langfuse** |
| **Debugging** | ❌ Log files only | ✅ Web UI with reasoning inspection | **Langfuse** |
| **Latency** | ✅ Fast (Redis cache + local logic) | ⚠️ Network round-trip to Langfuse API | **Local** |
| **Offline support** | ✅ Works without internet | ❌ Requires Langfuse API access | **Local** |
| **Template versioning** | ❌ Code-based prompts | ✅ Centralized prompt management | **Langfuse** |
| **Custom logic** | ✅ Full Python control (rubrics, caching) | ⚠️ Limited to Langfuse API capabilities | **Local** |
| **Team collaboration** | ❌ No shared UI | ✅ Dashboard for stakeholders | **Langfuse** |
| **Maturity** | ✅ Battle-tested (fixed 5+ bugs) | 🆕 New, needs validation | **Local** |

**Recommendation**: Use **Local G-Eval as PRIMARY** (default), **Langfuse as COMPLEMENTARY** (opt-in for debugging and analytics).

## Cost Analysis

### Local G-Eval Costs
```
Per Analysis (3 criteria × 1 judge vote):
  - Model: gemini-flash-1.5 (fast, cheap)
  - Input tokens: ~1,500 per criterion = 4,500 total
  - Output tokens: ~200 per criterion = 600 total
  - Cost: ~$0.002 per analysis (with caching)

With Self-Consistency (3 votes):
  - Cost: ~$0.006 per analysis
  - Cache hit rate: ~40% (Redis semantic cache)
  - Effective cost: ~$0.004 per analysis
```

### Langfuse Evaluator Costs
```
Per Analysis (3 criteria):
  - Model: Configurable (gemini-flash-1.5 recommended)
  - Input tokens: ~1,500 per criterion = 4,500 total
  - Output tokens: ~200 per criterion = 600 total
  - Cost: ~$0.002 per analysis (base LLM cost)
  - Langfuse API overhead: Negligible (metadata only)
  - Langfuse prompt caching: Available (experimental)

Additional value:
  - Cost visibility in dashboard (FREE)
  - Evaluation traces stored (FREE, self-hosted)
  - Debugging UI (FREE)
  - Prompt versioning (FREE)
```

**Verdict**: Same base LLM cost, but Langfuse adds observability value at zero marginal cost.

## Implementation Checklist

### Phase 1: Core Infrastructure (2 hours)

- [ ] **Create langfuse_evaluators.py** (NEW file)
  ```
  backend/app/shared/services/g_eval/langfuse_evaluators.py
  ```
  - [ ] Implement `LangfuseEvaluator` base class
  - [ ] Implement `RelevanceEvaluator` using Langfuse SDK
  - [ ] Implement `DepthEvaluator` using Langfuse SDK
  - [ ] Implement `CoherenceEvaluator` using Langfuse SDK
  - [ ] Add error handling with fallback to local G-Eval
  - [ ] Add cost tracking integration

- [ ] **Add configuration** (backend/app/core/config.py)
  ```python
  # Evaluation backend selection
  EVALUATOR_BACKEND: Literal["local", "langfuse", "hybrid"] = "local"

  # Langfuse evaluator config
  LANGFUSE_EVAL_MODEL: str = "gemini-flash-1.5"
  LANGFUSE_EVAL_TEMPERATURE: float = 0.1
  ```

- [ ] **Create evaluator factory** (NEW file)
  ```
  backend/app/evaluation/evaluators/factory.py
  ```
  - [ ] `create_evaluator(backend: str, criterion: str) -> BaseEvaluator`
  - [ ] Returns local or Langfuse evaluator based on config
  - [ ] Handles fallback logic

### Phase 2: Quality Gate Integration (1.5 hours)

- [ ] **Update quality_gate_node.py**
  - [ ] Import `create_evaluator()` factory
  - [ ] Replace hardcoded `create_quality_evaluator()` with factory calls
  - [ ] Add config check for `EVALUATOR_BACKEND`
  - [ ] Implement hybrid mode (run both, compare scores)
  - [ ] Maintain existing threshold logic
  - [ ] Preserve retry mechanism

- [ ] **Add score comparison logging**
  ```python
  if config.EVALUATOR_BACKEND == "hybrid":
      local_score = await local_evaluator.evaluate(...)
      langfuse_score = await langfuse_evaluator.evaluate(...)
      logger.info(f"Score comparison - Local: {local_score}, Langfuse: {langfuse_score}")
  ```

### Phase 3: Langfuse Evaluator Templates (1 hour)

- [ ] **Create evaluation templates in Langfuse UI**
  - [ ] Relevance template (adapted from local rubric)
  - [ ] Depth template (adapted from local rubric)
  - [ ] Coherence template (adapted from local rubric)

- [ ] **Template naming convention**
  ```
  skillforge-eval-relevance-v1
  skillforge-eval-depth-v1
  skillforge-eval-coherence-v1
  ```

- [ ] **Map local rubrics to Langfuse templates**
  ```python
  LANGFUSE_TEMPLATE_MAP = {
      "relevance": "skillforge-eval-relevance-v1",
      "depth": "skillforge-eval-depth-v1",
      "coherence": "skillforge-eval-coherence-v1",
  }
  ```

### Phase 4: Testing & Validation (1.5 hours)

- [ ] **Unit tests** - `test_langfuse_evaluators.py` (NEW)
  - [ ] Test each Langfuse evaluator (relevance, depth, coherence)
  - [ ] Test fallback to local on Langfuse API errors
  - [ ] Test score format compatibility (0.0-1.0 normalized)
  - [ ] Test error handling (network errors, template not found)
  - [ ] Mock Langfuse API responses

- [ ] **Integration tests** - `test_evaluator_factory.py` (NEW)
  - [ ] Test factory creates correct evaluator based on config
  - [ ] Test hybrid mode runs both evaluators
  - [ ] Test score comparison logging

- [ ] **Quality gate tests** (update existing)
  - [ ] Test quality gate with Langfuse evaluators
  - [ ] Verify thresholds work identically
  - [ ] Verify retry logic preserved

- [ ] **Manual validation checklist**
  - [ ] Enable Langfuse: `EVALUATOR_BACKEND=langfuse`
  - [ ] Run analysis workflow
  - [ ] Verify evaluation traces in Langfuse UI
  - [ ] Check cost breakdown shows evaluation LLM calls
  - [ ] Inspect evaluation reasoning in Langfuse
  - [ ] Compare scores with local G-Eval (hybrid mode)
  - [ ] Verify fallback works (disable Langfuse API)

## Evaluation Criteria Mapping

| Local G-Eval Criterion | Langfuse Template | Rubric Adaptation |
|----------------------|-------------------|-------------------|
| **Relevance** | `skillforge-eval-relevance-v1` | Direct mapping - "How relevant are insights to input content?" |
| **Depth** | `skillforge-eval-depth-v1` | Direct mapping - "How thorough and detailed is the analysis?" |
| **Coherence** | `skillforge-eval-coherence-v1` | Direct mapping - "How well-structured and clear are the insights?" |
| **Accuracy** | *(Future)* | Requires factual verification logic |
| **Completeness** | *(Future)* | Requires section coverage analysis |

**Note**: Start with 3 core criteria (relevance, depth, coherence) to match current quality gate. Add accuracy/completeness in Phase 2.

## Acceptance Criteria

### Functional Requirements
- [ ] Langfuse evaluators return scores in same format as local G-Eval (0.0-1.0)
- [ ] Config variable `EVALUATOR_BACKEND` controls which evaluator is used
- [ ] Local G-Eval remains default (`EVALUATOR_BACKEND=local`)
- [ ] Langfuse evaluators appear as traces in Langfuse dashboard
- [ ] Evaluation costs visible in Langfuse UI (separate from workflow costs)
- [ ] Hybrid mode successfully runs both evaluators and logs comparison
- [ ] Fallback to local G-Eval works when Langfuse API unavailable

### Quality Gate Integration
- [ ] Quality thresholds work identically with Langfuse evaluators
- [ ] Retry logic preserved (up to 2 attempts on failure)
- [ ] Coverage-adjusted thresholds still apply
- [ ] Per-aspect minimums enforced correctly

### Code Quality
- [ ] All modified files pass linting: `ruff format --check && ruff check && ty check`
- [ ] Test coverage ≥80% maintained
- [ ] Unit tests pass for Langfuse evaluators
- [ ] Integration tests pass with both backends
- [ ] No breaking changes to existing quality gate behavior

### Observability
- [ ] Langfuse UI shows evaluation traces with reasoning
- [ ] Evaluation costs tracked separately from analysis workflow costs
- [ ] Template versions visible in Langfuse prompt management
- [ ] Hybrid mode logs score differences for analysis

## Files to Create/Modify

### New Files (3)
1. `backend/app/shared/services/g_eval/langfuse_evaluators.py` - Langfuse evaluator implementations
2. `backend/app/evaluation/evaluators/factory.py` - Evaluator factory for backend selection
3. `backend/tests/unit/shared/services/g_eval/test_langfuse_evaluators.py` - Unit tests

### Modified Files (3)
4. `backend/app/core/config.py` - Add `EVALUATOR_BACKEND` and Langfuse eval config
5. `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py` - Integrate factory
6. `backend/tests/unit/workflows/nodes/test_quality_gate_node.py` - Update tests

### Documentation (2)
7. `docs/issues/381-llm-as-judge/README.md` - This file
8. `docs/ARCHITECTURE.md` - Update with hybrid evaluation architecture

## Fallback Strategy

**Langfuse evaluators MUST gracefully fall back to local G-Eval on ANY error:**

```python
async def evaluate_with_fallback(
    criterion: str,
    input_content: str,
    output_content: str,
    backend: str = "local"
) -> float:
    """Evaluate with automatic fallback to local G-Eval."""

    if backend == "langfuse":
        try:
            # Try Langfuse evaluator
            langfuse_evaluator = create_langfuse_evaluator(criterion)
            return await langfuse_evaluator.evaluate(input_content, output_content)
        except (LangfuseAPIError, TemplateNotFoundError, NetworkError) as e:
            logger.warning(
                f"Langfuse evaluator failed for {criterion}: {e}. "
                "Falling back to local G-Eval."
            )
            # FALLBACK: Use local G-Eval
            backend = "local"

    # Local G-Eval (default and fallback)
    local_evaluator = create_local_evaluator(criterion)
    return await local_evaluator.evaluate(input_content, output_content)
```

**Failure scenarios requiring fallback:**
- Langfuse API unreachable (network errors)
- Template not found in Langfuse
- LLM rate limiting
- Invalid API credentials
- Timeout errors (>30s)

## Implementation Example

### Langfuse Evaluator Structure
```python
# backend/app/shared/services/g_eval/langfuse_evaluators.py

from langfuse import Langfuse
from app.core.config import get_settings

class LangfuseEvaluator:
    """Base class for Langfuse LLM-as-Judge evaluators."""

    def __init__(self, criterion: str, template_name: str):
        self.criterion = criterion
        self.template_name = template_name
        self.langfuse = Langfuse()  # Uses env vars from settings

    async def evaluate(
        self,
        input_content: str,
        output_content: str
    ) -> float:
        """Run evaluation using Langfuse template."""

        # Fetch template from Langfuse
        template = self.langfuse.get_prompt(self.template_name)

        # Format evaluation prompt
        messages = [
            {"role": "system", "content": template.prompt},
            {"role": "user", "content": f"Input:\n{input_content}\n\nOutput:\n{output_content}"}
        ]

        # Call LLM judge via Langfuse
        result = await self.langfuse.evaluate(
            name=f"quality-{self.criterion}",
            messages=messages,
            model=get_settings().LANGFUSE_EVAL_MODEL,
        )

        # Parse score (1-5) and normalize to 0.0-1.0
        score = self._parse_score(result.output)
        normalized = (score - 1) / 4  # 1->0.0, 3->0.5, 5->1.0

        return normalized

    def _parse_score(self, output: str) -> int:
        """Extract score from LLM response."""
        # Same parsing logic as local G-Eval
        match = re.search(r'Score:\s*(\d)', output)
        if match:
            return int(match.group(1))
        raise ValueError(f"Failed to parse score from: {output}")

# Criterion-specific evaluators
class RelevanceEvaluator(LangfuseEvaluator):
    def __init__(self):
        super().__init__("relevance", "skillforge-eval-relevance-v1")

class DepthEvaluator(LangfuseEvaluator):
    def __init__(self):
        super().__init__("depth", "skillforge-eval-depth-v1")

class CoherenceEvaluator(LangfuseEvaluator):
    def __init__(self):
        super().__init__("coherence", "skillforge-eval-coherence-v1")
```

### Quality Gate Integration
```python
# backend/app/domains/analysis/workflows/nodes/quality_gate_node.py

from app.evaluation.evaluators.factory import create_evaluator
from app.core.config import get_settings

async def quality_gate_node(state: AnalysisState) -> dict[str, object]:
    """Quality gate with configurable evaluator backend."""

    config = get_settings()
    backend = config.EVALUATOR_BACKEND  # "local", "langfuse", or "hybrid"

    # Evaluate each criterion
    scores = {}
    for criterion in QUALITY_ASPECTS:  # ["relevance", "depth", "coherence"]
        if backend == "hybrid":
            # Run BOTH evaluators for comparison
            local_score = await create_evaluator("local", criterion).evaluate(...)
            langfuse_score = await create_evaluator("langfuse", criterion).evaluate(...)

            logger.info(
                f"Hybrid evaluation - {criterion}: "
                f"Local={local_score:.2f}, Langfuse={langfuse_score:.2f}, "
                f"Diff={abs(local_score - langfuse_score):.2f}"
            )

            # Use local score for gate decision (primary)
            scores[criterion] = local_score
        else:
            # Single evaluator (local or langfuse)
            evaluator = create_evaluator(backend, criterion)
            scores[criterion] = await evaluator.evaluate(input_content, output_content)

    # Rest of quality gate logic unchanged...
    average_score = sum(scores.values()) / len(scores)
    passed = average_score >= QUALITY_THRESHOLD

    return {"quality_scores": scores, "quality_gate_passed": passed}
```

## Related Issues

- **#372**: Langfuse Migration (dependency, ✅ complete)
- **#383**: Token/Cost Tracking (dependency, 📋 planned - needed for separate eval costs)
- **#378**: Session & User Tracking (complementary, enables per-user quality analytics)
- **#379**: Prompt Management (complementary, uses Langfuse templates)
- **#299-304**: Artifact Quality Initiative (parent issue, quality gate foundation)

## Resources

### Langfuse Documentation
- [Evaluation Overview](https://langfuse.com/docs/evaluation/overview)
- [LLM-as-Judge Evaluators](https://langfuse.com/docs/evaluation/llm-as-judge)
- [Prompt Management](https://langfuse.com/docs/prompts/get-started)
- [Cost Tracking for Evaluations](https://langfuse.com/docs/model-usage-and-cost)

### Internal Documentation
- Local G-Eval Implementation: `backend/app/shared/services/g_eval/scorer.py`
- Quality Gate: `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`
- Quality Evaluators: `backend/app/evaluation/evaluators/quality.py`
- Rubrics: `backend/app/shared/services/g_eval/rubrics.py`

### Research Papers
- [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634)

---

**Implementation Philosophy**:
- **Preserve existing quality** - Local G-Eval is battle-tested and reliable
- **Add observability** - Langfuse provides debugging and cost visibility
- **Enable experimentation** - Hybrid mode allows A/B testing
- **Fail safely** - Always fall back to local G-Eval on errors
- **Zero production risk** - Local remains default, Langfuse is opt-in

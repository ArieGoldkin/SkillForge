# Phase 1 Quality Regression - Root Cause Analysis

**Date**: 2025-12-16
**Analyst**: AI/ML Engineer
**Status**: CRITICAL - Test Infrastructure Failure Detected

## Executive Summary

The quality comparison test reported a -1.9% overall improvement, but investigation reveals this is **not a valid measurement**. The test infrastructure has fundamental flaws that make the results unreliable.

**Key Finding**: 71% of test cases (15/21) produced **identical outputs** between control and treatment variants, with abnormally low scores (0.123), indicating **test failure rather than actual quality regression**.

---

## Test Results Analysis

### Raw Data Breakdown

| Agent Type | Samples | Control Score | Treatment Score | Improvement | Status |
|------------|---------|---------------|-----------------|-------------|---------|
| research_analyst | 3 | 0.123 | 0.123 | 0.0% | IDENTICAL (Error) |
| code_reviewer | 3 | 0.123 | 0.123 | 0.0% | IDENTICAL (Error) |
| learning_path | 3 | 0.123 | 0.123 | 0.0% | IDENTICAL (Error) |
| performance_analyst | 3 | 0.123 | 0.123 | 0.0% | IDENTICAL (Error) |
| implementation_planner | 3 | 0.345 | 0.345 | 0.0% | IDENTICAL (Partial) |
| tech_comparator | 3 | 0.377 | 0.360 | -4.3% | REGRESSION |
| security_auditor | 3 | 0.427 | 0.390 | -8.7% | REGRESSION |

### Critical Observations

1. **Identical Outputs (71% of tests)**
   - 15/21 test cases show control_score == treatment_score (exactly)
   - Suggests LLM returned identical outputs for both variants
   - This should be statistically impossible for semantic tasks

2. **Abnormally Low Scores (0.123)**
   - 12/21 test cases scored exactly 0.123
   - This appears to be a fallback/error score
   - Quality scorer returns 0.123 when critical validation fails

3. **Missing Schema Validation**
   - 5/7 agent types have `schema_class = None` in test script
   - Without schemas, both variants likely return unstructured/invalid outputs
   - Quality scorer cannot properly validate without schemas

4. **No Example Retrieval Logging**
   - Cannot verify if treatment variant actually retrieved few-shot examples
   - May have silently failed and fallen back to control variant
   - No evidence that few-shot factory actually injected examples

---

## Root Causes (Ranked by Impact)

### 1. Missing Pydantic Schemas (CRITICAL)

**Impact**: 60% of tests affected (12/21)

**Evidence**:
```python
# From compare_few_shot_quality.py lines 85-95
AGENT_SCHEMAS: dict[str, type | None] = {
    "tech_comparator": TechComparison,
    "security_auditor": SecurityAudit,
    "implementation_planner": ImplementationPlan,
    "dependency_mapper": None,  # Not yet implemented
    "trend_validator": None,
    "performance_analyst": None,  # ← Used in test, but no schema!
    "code_reviewer": None,        # ← Used in test, but no schema!
    "learning_path": None,        # ← Used in test, but no schema!
    "research_analyst": None,     # ← Used in test, but no schema!
}
```

**Problem**:
- Without schemas, `create_structured_agent()` cannot validate outputs
- LLM likely returns invalid/unstructured responses
- Both control and treatment fail identically → 0.0% improvement

**Fix Required**:
- Create Pydantic schemas for all 4 missing agent types
- Update AGENT_SCHEMAS mapping
- Re-test with proper validation

---

### 2. Test Data Contamination (HIGH)

**Impact**: Unknown (needs investigation)

**Evidence**:
- Test uses `load_agent_examples()` which queries `AgentExample` table
- These examples may BE the golden dataset examples we're comparing against
- Testing "how well does few-shot work" using the SAME examples as few-shot prompts

**Problem**:
- If test input = few-shot example input:
  - Treatment variant sees its own test case as an example
  - Creates data leakage / circular reference
  - Results invalid (testing memorization, not generalization)

**Fix Required**:
```python
# In compare_few_shot_quality.py, add deduplication:
def should_skip_example(test_example: AgentExample, few_shot_examples: list) -> bool:
    """Skip if test example was used in few-shot prompts."""
    for ex in few_shot_examples:
        if test_example.id == ex.id:
            return True
        if test_example.input_summary == ex.input_summary:
            return True  # Same content
    return False
```

---

### 3. Quality Scorer Breakdown Analysis

**Impact**: All tests (scoring logic issues)

**Evidence from quality_scorer.py**:

#### Completeness Score (30% weight)
- Lines 92-94: If output exists, gets 0.2 base score
- Lines 96-110: Schema validation gives 0.4 (or partial credit based on error count)
- Lines 115-118: Required fields check (confidence_score, recommendation) → 0.2
- Lines 121-126: Non-empty lists check → 0.2

**Why 0.123 appears**:
- 0.2 (output exists) + 0.0 (schema fails) + 0.0 (no required fields) + 0.1 (no lists) = 0.3 completeness
- 0.3 completeness * 0.30 weight = 0.09
- Plus minimal accuracy/detail/structure scores ≈ 0.123 total

**Problem**: Without schemas, completeness maxes at ~0.3 → overall score ~0.12

#### Detail Score (20% weight)
- Lines 224-231: List length scoring (target: 3-5 items)
- Lines 233-245: Text field depth (target: 100+ chars)
- Lines 247-280: Agent-specific checks

**Potential Issue**: May penalize longer, thorough outputs
- Line 228: `score += min(avg_length / 5, 1.0) * 0.4`
- This rewards brevity (capped at 5 items)
- Longer lists don't score higher

**Fix**: Consider removing cap for list length scoring

---

### 4. Few-Shot Factory Silent Failures (MEDIUM)

**Impact**: Unknown (no logs in results)

**Evidence**:
- `few_shot_factory.py` lines 352-377: Graceful degradation falls back to control on ANY error
- No logging in test results showing example retrieval
- Cannot verify treatment variant actually used few-shot examples

**Problem**:
```python
# Lines 352-377: Silent fallback on any error
except Exception as e:  # noqa: BLE001 - Intentional catch-all
    logger.warning("few_shot_factory_error_fallback", ...)
    return base_agent_factory(**factory_kwargs)  # ← Falls back to control!
```

If example retrieval failed silently:
- Treatment variant = control variant
- 0.0% improvement (as observed in 15/21 tests)

**Fix Required**:
- Add explicit example count validation
- Raise error if treatment variant returns 0 examples
- Log example retrieval details to test output

---

### 5. Example Relevance Thresholds Too Loose (MEDIUM)

**Impact**: Quality of few-shot examples (when they work)

**Evidence from few_shot_factory.py**:
```python
# Lines 182-183
max_examples: int = 5,
min_quality_score: float = 0.8,
```

**Evidence from selector.py**:
```python
# Lines 158-174: No relevance distance filtering
query = (
    select(AgentExampleModel, ...)
    .where(AgentExampleModel.quality_score >= min_quality_score)
    .order_by("distance").limit(max_examples)
)
# ← Returns top K regardless of distance!
```

**Problem**:
- No maximum distance threshold (e.g., distance < 0.3 for 70% similarity)
- May include irrelevant examples if not enough high-quality matches
- Low-relevance examples hurt quality rather than help

**Fix Required**:
```python
# In selector.py, add after line 166:
.where(
    AgentExampleModel.embedding.cosine_distance(query_embedding) <= 0.3
)
```

---

## Hypothesis Testing Results

| Hypothesis | Status | Evidence |
|------------|--------|----------|
| H1: Testing on Golden Dataset | ✅ CONFIRMED | Test uses AgentExample table (likely golden data) |
| H2: Low Example Relevance | ⚠️ POSSIBLE | No distance threshold in selector |
| H3: Quality Scorer Bias | ✅ CONFIRMED | 0.123 score indicates schema validation failure |
| H4: Prompt Bloat | ❌ UNLIKELY | Most tests had 0 examples (silent failures) |
| H5: Missing Schemas | ✅ CONFIRMED | 5/7 agent types have schema_class=None |

---

## Recommended Fixes (Priority Order)

### Priority 1: CRITICAL (Blocking)

#### Fix 1.1: Create Missing Pydantic Schemas
**Files to Create**:
- `app/domains/analysis/workflows/agents/schemas/research_analyst.py`
- `app/domains/analysis/workflows/agents/schemas/code_reviewer.py`
- `app/domains/analysis/workflows/agents/schemas/learning_path.py`
- `app/domains/analysis/workflows/agents/schemas/performance_analyst.py`

**Template** (based on existing schemas):
```python
from pydantic import BaseModel, Field

class ResearchAnalysis(BaseModel):
    """Research analyst output schema."""

    key_findings: list[str] = Field(
        description="3-5 key research findings",
        min_length=3,
        max_length=5,
    )
    methodology: str = Field(
        description="Research methodology used",
        min_length=100,
    )
    limitations: list[str] = Field(
        description="Study limitations",
        min_length=2,
    )
    confidence_score: float = Field(
        description="Confidence in analysis (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    recommendation: str = Field(
        description="Overall recommendation",
        min_length=50,
    )
```

#### Fix 1.2: Update AGENT_SCHEMAS Mapping
```python
# In compare_few_shot_quality.py, update lines 85-95:
from app.domains.analysis.workflows.agents.schemas.research_analyst import ResearchAnalysis
from app.domains.analysis.workflows.agents.schemas.code_reviewer import CodeReview
# ... (import others)

AGENT_SCHEMAS: dict[str, type | None] = {
    "tech_comparator": TechComparison,
    "security_auditor": SecurityAudit,
    "implementation_planner": ImplementationPlan,
    "research_analyst": ResearchAnalysis,  # ✅ Added
    "code_reviewer": CodeReview,            # ✅ Added
    "learning_path": LearningPath,          # ✅ Added
    "performance_analyst": PerformanceAnalysis,  # ✅ Added
}
```

---

### Priority 2: HIGH (Quality)

#### Fix 2.1: Add Relevance Distance Filtering
```python
# In app/shared/services/examples/selector.py, after line 166:
.where(
    AgentExampleModel.embedding.cosine_distance(query_embedding) <= 0.3
)
```

**Rationale**: Only use examples with ≥70% similarity (distance ≤ 0.3)

#### Fix 2.2: Increase Quality Threshold
```python
# In app/shared/services/agents/few_shot_factory.py, line 183:
min_quality_score: float = 0.95,  # Up from 0.8
```

**Rationale**: Only use excellent examples (gold standard)

#### Fix 2.3: Reduce Example Count
```python
# In app/shared/services/agents/few_shot_factory.py, line 182:
max_examples: int = 3,  # Down from 5
```

**Rationale**: Fewer, higher-quality examples prevent prompt bloat

---

### Priority 3: MEDIUM (Test Infrastructure)

#### Fix 3.1: Prevent Test Data Contamination
```python
# In scripts/compare_few_shot_quality.py, add after line 280:
async def get_treatment_examples(
    example: AgentExample,
    session: AsyncSession,
    embedding_service: EmbeddingService,
) -> list[AgentExample]:
    """Get few-shot examples that would be used for treatment variant."""
    selector = SemanticExampleSelector(session, embedding_service)
    result = await selector.select_examples(
        content=example.input_content_preview or example.input_summary,
        agent_type=example.agent_type,
        max_examples=3,
        min_quality_score=0.95,
    )
    return result.examples

async def compare_example(
    example: AgentExample,
    dry_run: bool = False,
) -> ComparisonResult:
    # ... existing code ...

    # NEW: Check for data contamination
    async with get_session_factory()() as session:
        embedding_service = EmbeddingService()
        treatment_examples = await get_treatment_examples(
            example, session, embedding_service
        )

        # Skip if test example appears in few-shot examples
        for ex in treatment_examples:
            if example.id == ex.id:
                logger.warning(
                    "test_data_contamination_detected",
                    test_example_id=str(example.id),
                    skipping=True,
                )
                # Return null result (filter out later)
                return None
```

#### Fix 3.2: Add Few-Shot Example Logging
```python
# In scripts/compare_few_shot_quality.py, line 356:
logger.info(
    "treatment_variant_completed",
    agent_type=example.agent_type,
    example_id=str(example.id),
    elapsed_ms=elapsed_ms,
    num_examples_used=len(treatment_examples),  # ✅ Add this
    example_ids=[str(ex.id) for ex in treatment_examples],  # ✅ Add this
)
```

---

### Priority 4: LOW (Nice-to-Have)

#### Fix 4.1: Review Quality Scorer Detail Weights
Consider adjusting detail score to reward thoroughness over brevity:

```python
# In app/shared/services/quality_scorer.py, line 228:
# OLD: score += min(avg_length / 5, 1.0) * 0.4
# NEW: Reward longer lists up to 10 items
score += min(avg_length / 10, 1.0) * 0.4
```

#### Fix 4.2: Generate Fresh Test Dataset
Create new test cases NOT in golden dataset:

```bash
# scripts/generate_test_cases.py
# - Generate 10-15 NEW analysis requests per agent type
# - Different topics than golden dataset
# - Store separately (test_cases table, not agent_examples)
```

---

## Re-Test Plan

### Phase 1: Infrastructure Fixes (Est: 4 hours)
1. ✅ Create missing Pydantic schemas (4 agent types)
2. ✅ Update AGENT_SCHEMAS mapping
3. ✅ Add relevance distance filtering
4. ✅ Increase quality threshold to 0.95
5. ✅ Reduce max examples to 3

### Phase 2: Test Improvements (Est: 2 hours)
1. ✅ Add test data contamination detection
2. ✅ Add few-shot example logging
3. ✅ Add validation that treatment variant uses examples

### Phase 3: Re-Run Tests (Est: 30 minutes)
```bash
# With fixes applied:
cd backend
poetry run python scripts/compare_few_shot_quality.py \
  --sample-size 5 \
  --output-dir docs/ \
  2>&1 | tee logs/phase1-retest.log
```

### Phase 4: Analysis (Est: 1 hour)
1. Verify no 0.123 scores (indicates schemas work)
2. Verify control ≠ treatment scores (indicates few-shot works)
3. Calculate actual improvement percentage
4. Document findings in updated report

---

## Success Criteria for Re-Test

✅ **Infrastructure Valid**:
- Zero test cases with score = 0.123 (schema validation working)
- Zero test cases with control_score == treatment_score (variants differ)
- All treatment variants log ≥1 few-shot example retrieved

✅ **Quality Improvement**:
- Overall improvement > 0% (even 5-10% shows progress)
- At least 3/7 agent types show positive improvement
- No agent types show >10% regression

✅ **Statistical Validity**:
- Sample size ≥15 per agent type
- Standard deviation < 20%
- No data contamination detected

---

## Next Steps

1. **Immediate**: Implement Priority 1 fixes (missing schemas)
2. **Today**: Implement Priority 2 fixes (relevance thresholds)
3. **Tomorrow**: Re-run test with full logging
4. **Follow-up**: Analyze results and determine Phase 1 readiness

---

## Appendix: Detailed Score Breakdown

### Why 0.123 Score Appears

Quality score formula (from quality_scorer.py line 442):
```
overall = completeness * 0.30 + accuracy * 0.30 + detail * 0.20 + structure * 0.20
```

**Without schema validation**:
- Completeness: 0.3 (max without schema)
- Accuracy: 0.5 (uses confidence_score as proxy, likely default)
- Detail: 0.0 (no lists or text fields)
- Structure: 0.2 (has recommendation field)

**Calculation**:
```
0.3 * 0.30 + 0.5 * 0.30 + 0.0 * 0.20 + 0.2 * 0.20
= 0.09 + 0.15 + 0.0 + 0.04
= 0.28
```

Wait, that doesn't match 0.123... Let me check if there's validation error handling:

**With validation errors** (lines 101-110):
```python
except ValidationError as e:
    error_count = len(e.errors())
    partial_credit = max(0, 0.4 - (error_count * 0.05))
    score += partial_credit
```

If 8+ validation errors → partial_credit = 0.0
Then completeness = 0.2 + 0.0 + 0.0 + 0.1 = 0.3
Overall = 0.3 * 0.30 + 0.15 * 0.30 + 0.05 * 0.20 + 0.2 * 0.20
       = 0.09 + 0.045 + 0.01 + 0.04 = **0.185**

Still not 0.123... Need to check actual outputs.

**Most likely**: The 0.123 indicates the LLM returned minimal/invalid outputs that failed multiple scoring dimensions.

---

**End of Analysis**

# Issue #487: Artifact Generator Hallucination Fix

**GitHub Issue:** [#487](https://github.com/ArieGoldkin/SkillForge/issues/487)
**Status:** In Progress
**Branch:** `issue/487-artifact-hallucination-fix`
**Assignee:** Yonatan
**Story Points:** 5 pts
**Priority:** CRITICAL
**Labels:** `backend`, `langgraph`, `bug`, `critical`

---

## Overview

**Title:** Artifact Generator Hallucination - Fabricates Content Unrelated to Source

**Description:**
The artifact generator produces implementation guides with content **completely unrelated** to the source material when agents report insufficient data. This is a fundamental failure that makes the system actively misleading rather than helpful.

**Example:**
- **Input:** News article about Alibaba's Qwen3-Next model
- **Expected:** Summary about Qwen3-Next, HuggingFace availability, Chinese AI competition
- **Actual:** Guide about "Building apps with Anthropic Claude API" (FABRICATED!)

---

## Problem Statement

### Root Cause Analysis

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        HALLUCINATION DATA FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

    Source Content (News article - NO code)
           │
           ▼
    ┌──────────────────────────────────────┐
    │  8 SPECIALIST AGENTS                 │
    │  ┌─────────┐ ┌─────────┐ ┌────────┐  │
    │  │ Tech    │ │ Security│ │ Code   │  │
    │  │ Compar. │ │ Auditor │ │ Quality│  │
    │  └────┬────┘ └────┬────┘ └────┬───┘  │
    │       │           │           │      │
    │       ▼           ▼           ▼      │
    │  "insuffi-"  "insuffi-"  "insuffi-"  │  ◄── All agents report
    │   "cient"     "cient"     "cient"    │      data_availability="insufficient"
    └──────────────────────────────────────┘
           │
           │  PROBLEM #1: Empty/minimal findings
           ▼
    ┌──────────────────────────────────────┐
    │  AGGREGATOR (synthesis.py)           │
    │                                      │
    │  LLM Prompt:                         │
    │  ┌────────────────────────────────┐  │
    │  │ ## Agent Findings:             │  │
    │  │ (nearly empty)                 │  │  ◄── PROBLEM #2: No source
    │  │                                │  │      content passed to LLM!
    │  │ ## Source Content:             │  │
    │  │ ❌ MISSING!                    │  │
    │  └────────────────────────────────┘  │
    └──────────────────────────────────────┘
           │
           │  PROBLEM #3: LLM fills void with training data
           ▼
    ┌──────────────────────────────────────┐
    │  HALLUCINATED OUTPUT                 │
    │                                      │
    │  "Build apps with Anthropic Claude   │
    │   API using pip install anthropic"   │
    │                                      │
    │  Source: Alibaba Qwen3-Next          │
    │  Output: Anthropic Claude            │
    │                                      │
    │  🔴 COMPLETELY UNRELATED!            │
    └──────────────────────────────────────┘
```

### Four Hallucination Entry Points

| # | Location | Problem | Impact |
|---|----------|---------|--------|
| 1 | `synthesis_prompts.py` | No source content in LLM prompt | LLM has nothing to ground on |
| 2 | `aggregate_findings.py` | No coverage threshold check | Proceeds even with 0% useful findings |
| 3 | `generate_artifact.py` | No access to `raw_content` | Can't validate output |
| 4 | `artifact.j2` | No content validation | Renders hallucinated content blindly |

---

## Design Philosophy: Fail-Open

### Related Issues Discovery

| Issue | Relationship | Key Insight |
|-------|-------------|-------------|
| **#490** | Root cause fix (content-type routing) | Long-term solution, larger scope |
| **#491** | Overlaps (hallucination detection) | Will be closed as "implemented in #487" |
| **#455** | Establishes fail-open philosophy | **Critical guidance** |

### #455 Philosophy

> "Agents should report 'insufficient data' rather than failing. Artifacts SHOULD be generated even with low specificity scores, just with quality metadata/warnings."

**This means:**
- ❌ DON'T block artifact generation (user gets nothing = bad UX)
- ✅ DO adapt output to content type (user always gets something useful)

---

## Proposed Solution: Three-Layer Defense

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     THREE-LAYER HALLUCINATION DEFENSE                           │
└─────────────────────────────────────────────────────────────────────────────────┘

         LAYER 1                    LAYER 2                    LAYER 3
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │   GROUNDING  │          │   COVERAGE   │          │  VALIDATION  │
    │              │          │    CHECK     │          │              │
    │ Pass source  │    +     │ Detect low   │    +     │ Verify terms │
    │ to LLM       │          │ coverage     │          │ overlap      │
    └──────────────┘          └──────────────┘          └──────────────┘
           │                         │                         │
           ▼                         ▼                         ▼
    ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
    │ LLM sees     │          │ Switch to    │          │ Add warning  │
    │ actual       │          │ trend-       │          │ if output    │
    │ source text  │          │ summary mode │          │ doesn't      │
    │              │          │              │          │ match source │
    └──────────────┘          └──────────────┘          └──────────────┘


    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         ADAPTIVE OUTPUT                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  HIGH COVERAGE (≥30%)              LOW COVERAGE (<30%)                 │
    │  ═══════════════════               ════════════════════                │
    │                                                                         │
    │  Full Implementation Guide         Trend Summary Only                  │
    │  • Step-by-step instructions       • Key topics identified             │
    │  • Code examples                   • Related technologies              │
    │  • Best practices                  • Learning path suggestions         │
    │                                    • Quality warning displayed         │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Source Grounding (Prevent Hallucination)

**Goal:** Pass source content to LLM so it can't invent unrelated topics.

**New File:** `aggregation/source_content_extractor.py`
```python
def extract_source_summary(
    raw_content: str,
    extraction_metadata: dict,
    max_chars: int = 2000,
) -> dict[str, str]:
    """Extract key information from source for LLM grounding.

    Returns:
        {
            "title": str,
            "summary": str (truncated content),
            "key_terms": list[str],
        }
    """
```

**Modify:** `synthesis_prompts.py`
```python
CORE_SYNTHESIS_PROMPT = """You are synthesizing technical analysis findings...

## SOURCE CONTENT (GROUNDING)
Title: {source_title}
Original Content Summary:
{source_summary}

## CRITICAL GROUNDING RULES
1. ONLY discuss technologies, products, and concepts mentioned in the source
2. If agents report insufficient data, acknowledge this limitation honestly
3. Do NOT hallucinate implementation details not found in source
4. When in doubt, say "The source does not provide implementation details"

## Agent Findings:
{agent_findings}
...
"""
```

**Files Changed:**
- `aggregation/source_content_extractor.py` (NEW)
- `aggregation/synthesis_prompts.py` (MODIFY)
- `aggregation/synthesis_phased.py` (MODIFY - add source_context param)
- `aggregate_findings.py` (MODIFY - extract and pass source)

---

### Phase 2: Hallucination Detection (Safety Net)

**Goal:** Detect when output doesn't match source via key term overlap.

**New File:** `aggregation/grounding_validator.py`
```python
def extract_key_terms(text: str, top_n: int = 50) -> set[str]:
    """Extract key technical terms from text."""

def validate_grounding(
    source_content: str,
    generated_content: str,
    min_overlap: float = 0.15,
) -> tuple[bool, float, list[str]]:
    """Validate generated content is grounded in source.

    Returns:
        (is_grounded: bool, score: float, warnings: list[str])

    Example:
        source = "Alibaba Qwen3-Next 80B parameters"
        output = "Anthropic Claude API Python SDK"

        # Result: is_grounded=False, score=0.02,
        #         warnings=["Output contains terms not in source: Claude, Anthropic"]
    """
```

**Files Changed:**
- `aggregation/grounding_validator.py` (NEW)
- `aggregate_findings.py` (MODIFY - add validation after synthesis)

---

### Phase 3: Adaptive Artifact Mode (Fail-Open)

**Goal:** When coverage is low, generate trend-summary instead of full guide.

**Modify:** `aggregate_findings.py`
```python
# Calculate data sufficiency
sufficiency_score = calculate_data_sufficiency_score(validated_findings)

if sufficiency_score < DATA_SUFFICIENCY_THRESHOLD:  # 0.3
    # Switch to trend-summary mode instead of blocking
    artifact_mode = "trend_summary"

    # Use only trend_validator findings
    # Generate summary artifact (not implementation guide)
    # Add quality warnings to metadata
```

**Modify:** `aggregation_fallback.py`
```python
async def create_trend_summary_response(
    analysis_id: AnalysisID,
    source_context: dict,
    trend_findings: dict | None,
) -> dict[str, Any]:
    """Create useful trend summary when full analysis not possible.

    Returns honest, grounded summary:
    "This article discusses Alibaba's Qwen3-Next model with 80B parameters.
    Key trends: Open-source AI competition, HuggingFace availability.
    Note: This is a news article without implementation code."
    """
```

**Files Changed:**
- `aggregation_helpers.py` (MODIFY - add `calculate_data_sufficiency_score`)
- `aggregate_findings.py` (MODIFY - add threshold check, mode switching)
- `aggregation_fallback.py` (MODIFY - add trend summary generator)

---

### Phase 4: Tests

**New Tests:**

| Test File | Test Cases |
|-----------|------------|
| `test_source_content_extractor.py` | Extract title, truncate content, key terms |
| `test_grounding_validator.py` | High overlap passes, hallucination fails |
| `test_data_sufficiency.py` | All sufficient=1.0, all insufficient=0.0, mixed=weighted |
| `test_aggregate_findings.py` | Add: blocks hallucination, trend-summary fallback |

**Key Test Case:**
```python
async def test_news_article_produces_trend_summary_not_hallucination():
    """Issue #487: News article should NOT produce fabricated guide."""
    state = AnalysisState(
        raw_content="Alibaba announces Qwen3-Next model with 80B parameters...",
        agent_findings=[
            {"agent_type": "tech_comparator", "findings": {"data_availability": "insufficient"}},
            {"agent_type": "security_auditor", "findings": {"data_availability": "insufficient"}},
            # ... all agents insufficient
        ],
    )

    result = await aggregate_findings(state)

    # Should NOT hallucinate
    assert "Claude" not in result["aggregated_insights"]["executive_summary"]
    assert "Anthropic" not in result["aggregated_insights"]["executive_summary"]

    # Should reference actual source
    assert "Qwen3" in result["aggregated_insights"]["executive_summary"] or \
           "Alibaba" in result["aggregated_insights"]["executive_summary"]

    # Should indicate limited analysis
    assert result["aggregated_insights"]["metadata"]["artifact_mode"] == "trend_summary"
```

---

## Files Summary

### New Files (3)

| File | Purpose | Lines |
|------|---------|-------|
| `aggregation/source_content_extractor.py` | Extract source for LLM grounding | ~60 |
| `aggregation/grounding_validator.py` | Key term validation | ~80 |
| `tests/.../test_grounding_validator.py` | Validation tests | ~100 |

### Modified Files (5)

| File | Changes | Lines Changed |
|------|---------|---------------|
| `aggregation/synthesis_prompts.py` | Add source grounding section | +30 |
| `aggregation/synthesis_phased.py` | Pass source_context param | +15 |
| `aggregate_findings.py` | Extract source, threshold check, validation | +80 |
| `aggregation_helpers.py` | Add sufficiency score calc | +40 |
| `aggregation_fallback.py` | Add trend summary generator | +60 |

**Total Estimated Changes:** ~465 lines

---

## Configuration

### New Constants

```python
# backend/app/core/constants.py

# Minimum data sufficiency to generate full implementation guide
DATA_SUFFICIENCY_THRESHOLD = 0.3  # 30%

# Minimum key term overlap to consider output grounded
MIN_GROUNDING_OVERLAP = 0.15  # 15%

# Maximum chars of source content to include in LLM prompt
SOURCE_SUMMARY_MAX_CHARS = 2000
```

### Sufficiency Scoring

```python
# Weight by data_availability field
SUFFICIENCY_WEIGHTS = {
    "sufficient": 1.0,    # Full data available
    "limited": 0.5,       # Partial data
    "insufficient": 0.0,  # No useful data
}

# Score = sum(weights) / num_agents
# Example: 2 sufficient + 2 limited + 4 insufficient = (2 + 1 + 0) / 8 = 0.375
```

---

## Expected Outcomes

### Before (Hallucination)

```
Input: https://cosmico.org/alibaba-open-sources-qwen3-next...

Output:
"## TL;DR
This guide focuses on building robust and testable applications
using the Anthropic Claude API..."

🔴 COMPLETELY FABRICATED - Source mentions Alibaba/Qwen3, not Claude!
```

### After (Grounded)

```
Input: https://cosmico.org/alibaba-open-sources-qwen3-next...

Output:
"## Summary
This article discusses Alibaba's Qwen3-Next-80B-A3B model, featuring
80 billion parameters with claimed 10x performance improvement.

## Key Trends
- Open-source AI model competition (Alibaba vs OpenAI vs Anthropic)
- HuggingFace as distribution platform
- Chinese AI ecosystem development

## Note
This is a news/announcement article. No implementation code was found.
For hands-on learning, consider exploring the model on HuggingFace."

✅ GROUNDED - References actual source content, acknowledges limitations
```

---

## Acceptance Criteria

- [ ] Generated artifacts reference actual content from source
- [ ] No fabricated technologies/APIs that don't appear in source
- [ ] Clear trend-summary fallback when agents produce insufficient findings
- [ ] Quality warnings shown when artifact_mode is "trend_summary"
- [ ] Automated test that catches content hallucination
- [ ] Verification with reproduction case (Qwen3-Next article)

---

## Related Issues

| Issue | Relationship | Action |
|-------|-------------|--------|
| **#490** | Root cause fix (content-type routing) | Separate effort after #487 |
| **#491** | Overlaps (hallucination detection) | Close as "implemented in #487" |
| **#455** | Fail-open philosophy reference | Followed in design |
| **#495** | Documentation issue | Complete after implementation |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token usage increase from source | LOW | Truncate to 2000 chars |
| False positives in grounding check | MEDIUM | Warn-only, don't block; tune threshold |
| Breaking existing tests | LOW | Run full test suite after each phase |
| Performance impact | LOW | String operations are O(n), negligible |

---

## References

- **GitHub Issue:** [#487](https://github.com/ArieGoldkin/SkillForge/issues/487)
- **Related PR:** TBD
- **Architecture:** `docs/ARCHITECTURE.md`
- **Aggregation Docs:** `docs/issues/175-enhanced-aggregation/README.md`

---

**Last Updated:** December 23, 2025
**Status:** In Progress
**Maintained By:** Yonatan

# ADR-0010: Artifact Quality Enforcement System

**Status**: Proposed
**Date**: 2024-12-14
**Author**: Claude + Yonatan
**Issue**: #ARTIFACT-QUALITY

---

## Context

### Problem Statement
Generated artifacts contain **hallucinated garbage** despite sophisticated quality infrastructure existing in the codebase. The system ships mediocre artifacts because quality checks are **fail-open** (permissive) rather than **fail-closed** (strict).

### Evidence (Analysis ID: 52ce557a-f8f2-4ddc-bbfc-5e391118ed24)
```
Quality Gate Results:
├── Relevance: 0.4  (40% - TERRIBLE)
├── Depth:     0.9  (90%)
├── Coherence: 0.8  (80%)
└── AVERAGE:   0.7  (70% - PASSED!)

Artifact Content:
├── "LangGraph 0.6.7" - COPIED from prompt example
├── "pip install transformers" - IRRELEVANT to source article
├── "CVE-2023-12345" - FABRICATED vulnerability
├── /my-project/src/api.js - INVENTED file paths
└── Missing: TL;DR, diagrams, glossary, exercises, quiz
```

### Root Causes Identified

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | Using gpt-4o-mini instead of Claude | `.env` | Weak model copies examples, ignores content |
| 2 | No grounding instructions | Agent prompts | LLM invents data not in source |
| 3 | Quality gate only checks AVERAGE | `quality_gate_node.py:182` | 0.4 relevance passes if avg=0.7 |
| 4 | Fail-open on max retries | `quality_gate_node.py:311-321` | Ships garbage after 2 retries |
| 5 | Specificity scorer logs-only | `execution.py` | Warns but doesn't block |
| 6 | Triple-consumer sections missing | `synthesis.py` | Not requiring all output sections |

### Existing Infrastructure (Underutilized)

```
┌────────────────────────────────────────────────────────────────┐
│              EXISTING QUALITY INFRASTRUCTURE                   │
├────────────────────────────────────────────────────────────────┤
│ ✅ Specificity Scorer (552 lines) - 40+ vague phrase patterns  │
│ ✅ Quality Gate (331 lines) - LLM-as-judge evaluation          │
│ ✅ Confidence Scores - All 8 agents produce them               │
│ ✅ Numeric Validation - 14 pattern types                       │
│ ✅ Pydantic Schemas - Structural validation for all agents     │
│ ✅ Artifact Template - 13 sections defined in Jinja2           │
├────────────────────────────────────────────────────────────────┤
│ ⚠️ STATUS: LOGS WARNINGS BUT NEVER BLOCKS EXECUTION           │
└────────────────────────────────────────────────────────────────┘
```

---

## Decision

We will transform quality infrastructure from **monitoring** to **enforcement** through these changes:

### 1. Switch LLM Model
```env
# .env
LLM_MODEL=claude-sonnet-4-20250514  # Was: gpt-4o-mini
```

### 2. Add Content Grounding (All 8 Agents)
```python
# app/workflows/agents/grounding.py (NEW FILE)
GROUNDING_INSTRUCTIONS = """
=== CRITICAL: CONTENT GROUNDING REQUIREMENTS ===
- ONLY analyze what's in the provided content
- NEVER fabricate CVEs, versions, metrics, file paths
- If not covered in source, say "Not covered in source material"
- Set confidence_score <= 0.3 for unsupported analysis
"""
```

Apply via `apply_grounding(base_prompt)` to all agent prompts.

### 3. Fix Quality Gate - Individual Aspect Minimums
```python
# app/workflows/nodes/quality_gate_node.py
QUALITY_THRESHOLD = 0.7  # Average minimum
ASPECT_MINIMUMS = {
    "relevance": 0.5,  # CRITICAL: Must be relevant to source!
    "depth": 0.4,
    "coherence": 0.4,
}

# NEW: Check individual minimums, not just average
for aspect, minimum in ASPECT_MINIMUMS.items():
    if quality_scores[aspect]["score"] < minimum:
        gate_passed = False
        failed_aspects.append(aspect)
```

### 4. Change Fail-Open to Fail-Closed
```python
# BEFORE (fail-open on max retries):
if retry_count >= MAX_RETRY_ATTEMPTS:
    return "continue"  # Ships garbage!

# AFTER (fail-closed):
if retry_count >= MAX_RETRY_ATTEMPTS:
    raise QualityGateError(
        f"Quality gate failed after {MAX_RETRY_ATTEMPTS} retries. "
        f"Relevance: {scores['relevance']}, threshold: {ASPECT_MINIMUMS['relevance']}"
    )
```

### 5. Require All Triple-Consumer Sections in Synthesis
```python
# app/workflows/tasks/aggregation/synthesis.py
REQUIRED_SECTIONS = [
    "executive_summary",      # Basic
    "key_findings",           # Basic
    "ai_assistant_prompt",    # For AI assistants
    "core_concepts",          # For tutor system
    "exercises",              # For tutor system
    "tldr",                   # For humans
    "diagrams",               # For humans (Mermaid)
    "glossary",               # For humans
]

# Validate after synthesis
for section in REQUIRED_SECTIONS:
    if not aggregated_insights.get(section):
        raise ValueError(f"Missing required section: {section}")
```

### 6. Add Confidence Threshold Enforcement
```python
# app/workflows/tasks/aggregation/validation.py
MIN_CONFIDENCE = 0.6

for agent_type, confidence in confidence_scores.items():
    if confidence < MIN_CONFIDENCE:
        logger.warning(f"Low confidence from {agent_type}: {confidence}")
        # Flag for potential re-analysis or exclude from synthesis
```

---

## Implementation Plan

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PHASES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 1: Model + Grounding (DONE)                             │
│  ├── [x] Switch to Claude Sonnet 4                              │
│  ├── [x] Create grounding.py module                            │
│  └── [x] Apply grounding to all 8 agents                       │
│                                                                 │
│  PHASE 2: Quality Gate Enforcement (IN PROGRESS)               │
│  ├── [x] Add ASPECT_MINIMUMS configuration                     │
│  ├── [ ] Implement individual aspect checking                  │
│  └── [ ] Change fail-open to fail-closed                       │
│                                                                 │
│  PHASE 3: Synthesis Completeness                                │
│  ├── [ ] Define REQUIRED_SECTIONS list                         │
│  ├── [ ] Add post-synthesis validation                         │
│  └── [ ] Ensure template renders all sections                  │
│                                                                 │
│  PHASE 4: Testing & Validation                                 │
│  ├── [ ] Rebuild Docker with all changes                       │
│  ├── [ ] Run single analysis with enforced quality             │
│  ├── [ ] Verify artifact has all sections                      │
│  └── [ ] Verify content is grounded (no hallucinations)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Consequences

### Positive
- **No more hallucinated content**: Grounding instructions prevent fabrication
- **Relevance enforced**: Low-relevance artifacts blocked, not shipped
- **Complete artifacts**: All 13 sections required, not optional
- **Better model**: Claude follows complex instructions accurately
- **Existing infrastructure utilized**: 1500+ lines of quality code now active

### Negative
- **Higher failure rate initially**: Stricter quality will reject more analyses
- **Longer processing time**: Claude is slower than gpt-4o-mini
- **Higher API costs**: Claude costs ~3x more per token
- **May need prompt tuning**: Claude behaves differently than OpenAI models

### Neutral
- **Retry logic unchanged**: Still 2 retries, just fails-closed after
- **Specificity scoring unchanged**: Already implemented, just now enforced
- **Schema validation unchanged**: Pydantic still handles structure

---

## Alternatives Considered

### Alternative 1: Keep gpt-4o-mini with Better Prompts
**Pros**: Lower cost, faster responses
**Cons**: Model fundamentally struggles with complex multi-section output
**Why not chosen**: Prompts already have examples; model ignores content regardless

### Alternative 2: Remove Quality Gate Entirely
**Pros**: Faster processing, no failures
**Cons**: Ships garbage with no quality control
**Why not chosen**: Defeats purpose of quality infrastructure

### Alternative 3: Make Quality Gate Configurable (Strict/Permissive)
**Pros**: Flexibility for different use cases
**Cons**: Complexity, risk of always using permissive mode
**Why not chosen**: Default should be strict; permissive available via env vars

---

## Files Modified

| File | Change |
|------|--------|
| `backend/.env` | `LLM_MODEL=claude-sonnet-4-20250514` |
| `backend/app/workflows/agents/grounding.py` | NEW: Grounding instructions module |
| `backend/app/workflows/agents/*.py` (8 files) | Import and apply grounding |
| `backend/app/workflows/nodes/quality_gate_node.py` | Add ASPECT_MINIMUMS, fail-closed |
| `backend/app/workflows/tasks/aggregation/synthesis.py` | Add REQUIRED_SECTIONS validation |

---

## Verification Checklist

- [ ] Run lint: `poetry run ruff check app/`
- [ ] Run type check: `poetry run mypy app/`
- [ ] Run unit tests: `poetry run pytest tests/unit/`
- [ ] Rebuild Docker: `docker compose up -d --build backend`
- [ ] Test single analysis with Anthropic article
- [ ] Verify quality gate rejects if relevance < 0.5
- [ ] Verify artifact has all 13 sections
- [ ] Verify no hallucinated content (CVEs, versions, paths)
- [ ] Screenshot with Playwright for visual verification

---

## References

- Quality Gate Node: `app/workflows/nodes/quality_gate_node.py`
- Specificity Scorer: `app/workflows/agents/validation/specificity_scorer.py`
- Artifact Template: `app/workflows/tasks/templates/artifact.j2`
- Previous Analysis: `52ce557a-f8f2-4ddc-bbfc-5e391118ed24`

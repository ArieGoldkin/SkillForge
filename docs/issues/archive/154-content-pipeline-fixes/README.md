# Issue #154: Content Pipeline Fixes

**Status:** COMPLETE
**Sprint:** 4
**Story Points:** 5
**Assignee:** YonatanGross
**Branch:** `feature/issue-154-content-pipeline-fixes`

---

## Description

Fix three related problems in the content analysis pipeline that affect artifact quality:

1. Confidence scores missing from generated artifacts
2. Quick Reference section lacking actionable specifics
3. Agent prompts producing vague, non-quantified outputs

---

## Problem

### 1. Missing Confidence Scores

Agent confidence scores were being extracted but not propagated to the artifact templates. The Jinja2 template couldn't access `{{ confidence_score }}` because it was only passed to the database save function.

### 2. No Quick Reference Section

Generated artifacts lacked an "at-a-glance" section for developers who need quick access to prerequisites, commands, and gotchas without reading the full artifact.

### 3. Vague Agent Outputs

Agents produced non-specific outputs like:

```text
bottlenecks: Database queries are slow
recommendation: Improve caching and optimize queries
```

Instead of quantified specifics:

```text
bottlenecks: Database queries consume 450ms/request due to N+1 (23 queries/request)
recommendation: Priority 1: Redis cache (90% hit ratio, 2h). Priority 2: Fix N+1 (15% gain, 4h)
```

---

## Solution

### Phase 1: Confidence Score Bug Fix

Modified `result_processing.py` to include `confidence_score` at the top level of the findings dictionary, making it accessible to Jinja2 templates.

### Phase 2: Quick Reference Template Section

Added a new Quick Reference section to the artifact template with constrained limits:

- Prerequisites (max 4 items)
- Critical commands (max 6 items)
- Key files to modify (max 10 items)
- Common gotchas (max 5 items)

### Phase 3: Agent Prompt Improvements

Updated all 8 agent prompts with two new sections:

1. **NUMERIC SPECIFICITY REQUIREMENTS** - Explicit requirements for numeric values with units
2. **FORBIDDEN VAGUE LANGUAGE** - Prohibited phrases with specific alternatives

### Phase 4: Specificity Scoring System

Added a validation module to score agent output specificity (0.0-1.0) and log warnings for low-quality outputs.

---

## Tasks Completed

- [x] Fix confidence score propagation to templates
- [x] Add Quick Reference section to artifact template
- [x] Create Quick Reference extraction module (`quick_reference.py`)
- [x] Update all 8 agent prompts with specificity requirements
- [x] Create specificity scoring module with vague phrase detection
- [x] Fix all ruff linting errors (30+ issues across source and tests)
- [x] Pass mypy type checking
- [x] Add comprehensive test suites (70 tests total)
- [x] Create documentation

---

## Acceptance Criteria

- [x] Confidence scores display correctly in artifacts (verified: 0.9, 0.92, etc.)
- [x] Quick Reference section appears in generated artifacts
- [x] Quick Reference extraction module with field limits enforced
- [x] Agent outputs contain specific numeric values with units
- [x] All ruff checks pass (0 errors)
- [x] All mypy type checks pass (0 errors)
- [x] All 70 tests pass (result_processing + specificity_scorer + quick_reference)
- [x] Low specificity outputs logged as warnings

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/workflows/agents/result_processing.py` | Added confidence_score to top-level findings, imported threshold constant |
| `backend/app/workflows/agents/validation/specificity_scorer.py` | New module for specificity scoring with ruff-compliant constants |
| `backend/app/workflows/agents/validation/__init__.py` | Export specificity functions |
| `backend/app/workflows/tasks/aggregation/quick_reference.py` | New module for QuickReference extraction with field limits |
| `backend/app/workflows/tasks/aggregation/__init__.py` | Export quick_reference function, sorted `__all__` |
| `backend/app/workflows/tasks/schemas/aggregated_insights.py` | Added QuickReference and GotchaItem schemas |
| `backend/app/workflows/tasks/aggregate_findings.py` | Integrated quick_reference extraction |
| `backend/app/workflows/tasks/generate_artifact.py` | Pass QuickReference to template context |
| `backend/app/workflows/tasks/templates/artifact.j2` | Added Quick Reference section template |
| `backend/app/workflows/agents/performance_analyst.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/implementation_planner.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/dependency_mapper.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/security_auditor.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/integration_feasibility.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/trend_validator.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/code_quality_critic.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/app/workflows/agents/tech_comparator.py` | Added NUMERIC SPECIFICITY and FORBIDDEN VAGUE sections |
| `backend/tests/unit/workflows/tasks/aggregation/test_quick_reference.py` | New test suite with 26 tests |
| `backend/tests/unit/workflows/agents/validation/test_specificity_scorer.py` | New test suite with 22 tests |
| `backend/tests/unit/workflows/agents/test_result_processing.py` | Updated with specificity scoring tests, cleaned imports |

---

## Technical Details

### Quick Reference Extraction Strategy

The QuickReference module maps agent findings to user-friendly fields:

| Field | Source |
|-------|--------|
| `primary_technology` | `tech_comparator.primary_tech` + version from `dependency_mapper` |
| `complexity` | `implementation_planner.estimated_time` → mapped to level |
| `prerequisites` | `dependency_mapper.peer_dependencies` or `implementation_planner.prerequisites` |
| `critical_commands` | Install commands from `dependency_mapper.installation_notes` |
| `files_to_modify` | `implementation_planner.steps[].files` |
| `gotchas` | `security_auditor.security_risks` + `code_quality_critic.code_issues` |

**Complexity Mapping:**
- ≤2 hours → Beginner
- ≤4 hours → Intermediate
- ≤8 hours → Advanced
- >8 hours or multi-day → Expert

### Specificity Scoring Formula

The specificity score is calculated using a weighted formula:

```python
overall_score = (
    0.50 * numeric_field_compliance +  # Required fields have units
    0.30 * numeric_density +            # Ratio of actual to expected numerics
    0.20 * vague_penalty                # Penalty for vague phrases
)
```

### Quality Levels

| Level | Score Range |
|-------|-------------|
| Poor | < 0.50 |
| Moderate | 0.50 - 0.70 |
| Good | 0.70 - 0.85 |
| Excellent | > 0.85 |

### Constants Added (Ruff Compliance)

**Specificity Scorer (`specificity_scorer.py`)**:
```python
# Quality level thresholds
QUALITY_EXCELLENT_THRESHOLD = 0.85
QUALITY_GOOD_THRESHOLD = 0.70
QUALITY_MODERATE_THRESHOLD = 0.50

# Scoring weights
WEIGHT_NUMERIC_COMPLIANCE = 0.50
WEIGHT_NUMERIC_DENSITY = 0.30
WEIGHT_VAGUE_PENALTY = 0.20

# Limits and thresholds
VAGUE_PENALTY_THRESHOLD = 5
DEFAULT_EXPECTED_NUMERIC_COUNT = 10
LOW_SPECIFICITY_WARNING_THRESHOLD = 0.60
```

**Quick Reference (`quick_reference.py`)**:
```python
# Field limits
MAX_PREREQUISITES = 4
MAX_CRITICAL_COMMANDS = 6
MAX_FILES_TO_MODIFY = 10
MAX_GOTCHAS = 5

# Complexity level thresholds (in hours)
COMPLEXITY_BEGINNER_MAX_HOURS = 2
COMPLEXITY_INTERMEDIATE_MAX_HOURS = 4
COMPLEXITY_ADVANCED_MAX_HOURS = 8

# Technology extraction
MIN_TECH_WORDS_FOR_NAME = 2
```

### Agent Prompt Pattern

Each agent prompt now includes:

```text
NUMERIC SPECIFICITY REQUIREMENTS:
- [field] MUST include [unit type] (e.g., "650ms p99 latency")
- ...

FORBIDDEN VAGUE LANGUAGE - Never use:
- "good performance" (quantify: "2x faster", "150ms vs 450ms")
- ...

GOOD EXAMPLE:
  [specific output with units and numbers]

BAD EXAMPLE (DO NOT USE):
  [vague output without quantification]
```

---

## Example Output Improvements

### Before (Vague)

```json
{
  "bottlenecks": ["Database queries are slow"],
  "recommendation": "Improve caching and optimize queries"
}
```

### After (Specific)

```json
{
  "bottlenecks": [
    "Database queries consume 450ms/request due to N+1 problem (23 queries/request)"
  ],
  "recommendation": "Priority 1: Redis cache (90% hit ratio, 2 hour implementation). Priority 2: Fix N+1 queries (15% improvement, 4 hours)."
}
```

---

## Related Issues

- **Issue #152:** Schema Validation Fixes (default_factory for agent schemas)
- **Issue #149:** GFM Template Enhancements
- **Issue #72:** Artifact Generation

---

*This fix ensures agent outputs contain quantified, actionable information rather than vague generalities.*

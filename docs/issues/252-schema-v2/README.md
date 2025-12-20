# Issue #252: Evaluation Dataset Schema v2.0 with Pydantic Validation

**GitHub Issue:** [#252](https://github.com/ArieGoldkin/SkillForge/issues/252)
**Status:** ✅ **COMPLETE**
**Branch:** `feature/sprint-12-eval-datasets`
**Assignee:** Yonatan
**Story Points:** 5
**Sprint:** Sprint 12
**Parent Epic:** [#251 - Evaluation Datasets v2.0](https://github.com/ArieGoldkin/SkillForge/issues/251)
**Completed:** December 10, 2025

---

## 📋 Overview

Create a comprehensive v2.0 schema for evaluation datasets with provenance tracking, scoring rubrics, and validation status. This schema enables production-grade evaluation with real-world data sources.

### Key Improvements over v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Provenance tracking | ❌ | ✅ (source, trace IDs, URLs) |
| Scoring rubrics | Basic | Weighted (correctness, completeness, quality) |
| Validation workflow | ❌ | ✅ (draft → pending_review → validated) |
| Human review | ❌ | ✅ (2/3 consensus required) |
| Edge case flags | ❌ | ✅ (difficulty, adversarial, edge_case) |
| Custom evaluators | ❌ | ✅ (LLM judge, regex, semantic similarity) |

---

## ✅ Implementation Summary

### Files Created

```
backend/app/evaluation/
├── schemas/
│   ├── __init__.py                    # Module exports
│   ├── dataset_v2_schema.json         # JSON Schema (Draft-07)
│   └── validation.py                  # Pydantic validation + CLI
├── ingestion/
│   ├── __init__.py                    # Module exports
│   └── langfuse_extractor.py         # Langfuse trace extractor
└── datasets/
    └── agent_analysis_golden_v2.json  # Example v2.0 dataset
```

### Schema Features

#### 1. Provenance Tracking
```json
{
  "provenance": {
    "source": "langfuse|github|arxiv|synthetic|production|human_crafted",
    "created_at": "2025-12-10T00:00:00Z",
    "created_by": "username",
    "source_url": "https://...",
    "langfuse_trace_id": "abc123",
    "github_issue_url": "https://github.com/...",
    "arxiv_id": "2501.12345"
  }
}
```

#### 2. Scoring Rubrics
```json
{
  "scoring_rubric": {
    "correctness": { "weight": 0.5, "thresholds": { "perfect": 1.0, "acceptable": 0.7, "failing": 0.5 } },
    "completeness": { "weight": 0.3, "required_fields": ["field1", "field2"] },
    "quality": { "weight": 0.2, "min_length": 100, "max_length": 2000, "keywords": ["term1"] }
  }
}
```

#### 3. Validation Workflow
- **draft**: Initial creation, not reviewed
- **pending_review**: Ready for human validation
- **validated**: Approved by 2+ reviewers
- **rejected**: Failed review
- **needs_update**: Requires changes

#### 4. Custom Evaluators
```json
{
  "custom_evaluators": [
    { "name": "tech_name_accuracy", "type": "regex", "config": { "pattern": "React 19|Vue 3\\.5" } },
    { "name": "security_relevance", "type": "llm_judge", "config": { "prompt": "..." } }
  ]
}
```

---

## 🧪 Validation CLI

### Single Dataset
```bash
poetry run python -m app.evaluation.schemas.validation \
  --dataset app/evaluation/datasets/agent_analysis_golden_v2.json
```

### Directory (Recursive)
```bash
poetry run python -m app.evaluation.schemas.validation \
  --directory app/evaluation/datasets/ \
  --recursive \
  --output validation_report.md
```

### Python API
```python
from app.evaluation.schemas.validation import validate_dataset, ValidationResult

result = validate_dataset("path/to/dataset.json")
print(f"Valid: {result.is_valid}")
print(f"Examples: {result.example_count}")
print(f"Errors: {result.errors}")
```

---

## 🔄 Langfuse Extractor

### CLI Usage
```bash
poetry run python -m app.evaluation.ingestion.langfuse_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --agent-type security_auditor \
  --min-confidence 0.85 \
  --date-range 2025-12-01:2025-12-10 \
  --output datasets/drafts/langfuse_security_20251210.json
```

### Python API
```python
from app.evaluation.ingestion import LangfuseExtractor, ExtractionConfig

config = ExtractionConfig(
    project_name="skillforge-prod",
    task_type="agent",
    agent_type="security_auditor",
    min_confidence=0.85
)

extractor = LangfuseExtractor()
examples = extractor.extract(config)
extractor.save_dataset(examples, "output.json")
```

---

## ✅ Acceptance Criteria

- [x] JSON Schema (Draft-07) with all v2.0 fields
- [x] Provenance tracking (source, trace IDs, URLs)
- [x] Scoring rubrics (correctness, completeness, quality)
- [x] Validation workflow (draft → validated)
- [x] Human review tracking (2/3 consensus)
- [x] Pydantic validation with CLI
- [x] Langfuse trace extractor
- [x] Example golden dataset in v2.0 format
- [x] All CI checks pass (ruff format, lint, mypy)

---

## 🔗 Dependencies

- **jsonschema**: JSON Schema validation (added to dev dependencies)
- **langfuse**: Langfuse API client (already installed via langchain)

---

## 📊 Test Results

```
✅ Format: 14 files already formatted
✅ Lint: All checks passed!
✅ Mypy: No errors in schema/validation files
✅ Validation: agent_analysis_golden_v2.json - Valid: True, 3 examples
```

---

## 🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

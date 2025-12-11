# Evaluation Dataset v2.0 - Quick Reference

**One-page guide for common tasks**

---

## Schema Overview

```json
{
  "version": "2.x.x",
  "metadata": {
    "dataset_name": "...",
    "task_type": "supervisor|agent|synthesis",
    "agent_types": [...],
    "created_at": "ISO-8601",
    "release_tag": "..."
  },
  "examples": [
    {
      "id": "unique-id",
      "inputs": { "content": "...", "content_type": "..." },
      "expected_outputs": {
        "primary": {...},
        "acceptable_alternatives": [...],
        "forbidden_outputs": [...]
      },
      "evaluation_criteria": {
        "scoring_rubric": {
          "correctness": { "weight": 0.5, "thresholds": {...} },
          "completeness": { "weight": 0.3, "required_fields": [...] },
          "quality": { "weight": 0.2, "min_length": 50, "max_length": 5000 }
        }
      },
      "provenance": {
        "source": "synthetic|langsmith|github|arxiv|production",
        "created_at": "...",
        "langsmith_trace_id": "..."
      },
      "validation": {
        "status": "draft|pending_review|validated|rejected",
        "validated_by": [...]
      },
      "metadata": {
        "difficulty": "easy|medium|hard|expert",
        "edge_case": false,
        "adversarial": false,
        "tags": [...]
      }
    }
  ]
}
```

---

## Common Commands

### 1. Validate Dataset

```bash
# Single file
python -m app.evaluation.schemas.validation \
  --dataset datasets/v2/agent/agent_analysis_golden_v2.json

# Entire directory
python -m app.evaluation.schemas.validation \
  --directory datasets/v2/ \
  --recursive \
  --output validation_report.md
```

### 2. Extract from LangSmith

```bash
python -m app.evaluation.ingestion.langsmith_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --agent-type security_auditor \
  --min-confidence 0.85 \
  --date-range 2025-12-01:2025-12-10 \
  --output datasets/drafts/langsmith_security_20251210.json
```

### 3. Review Examples (CLI)

```bash
python -m app.evaluation.validation.reviewer_cli \
  --dataset datasets/drafts/langsmith_security_20251210.json \
  --reviewer yonatangross
```

### 4. Create Release

```bash
python -m app.evaluation.versioning.tagger \
  --datasets datasets/v2/agent/*.json \
  --version-type minor \
  --changelog "Added 15 LangSmith examples"
```

### 5. Run Evaluation

```bash
# Single model
python -m app.evaluation.run_experiments \
  --dataset agent_analysis_golden_v2 \
  --model gpt-5-mini \
  --output results/gpt-5-mini_20251210.json

# Compare models
python -m app.evaluation.run_experiments \
  --dataset agent_analysis_golden_v2 \
  --models gpt-5-mini,gemini-2.5-flash,claude-sonnet-4-20250514 \
  --compare \
  --output results/comparison_20251210.json
```

---

## File Locations

```
backend/app/evaluation/
├── schemas/
│   ├── dataset_v2_schema.json      ← JSON Schema
│   └── validation.py               ← Validation tool
│
├── datasets/
│   ├── v2/                         ← Current datasets
│   │   ├── agent/
│   │   ├── supervisor/
│   │   └── synthesis/
│   ├── drafts/                     ← Work in progress
│   └── archived/                   ← Old versions
│
├── ingestion/
│   ├── langsmith_extractor.py      ← LangSmith extraction
│   ├── github_importer.py          ← GitHub issues
│   └── arxiv_importer.py           ← arXiv papers
│
├── validation/
│   ├── reviewer_cli.py             ← Review tool
│   └── approval_gate.py            ← 2/3 consensus
│
└── versioning/
    ├── tagger.py                   ← Git tags
    └── changelog.py                ← Generate CHANGELOG
```

---

## Provenance Sources

| Source | Use Case | Selection Criteria |
|--------|----------|-------------------|
| **synthetic** | Hand-crafted examples | Expert validation |
| **langsmith** | Production traces | Confidence ≥0.85, no errors |
| **github** | Bug reports, edge cases | Closed issues with labels |
| **arxiv** | Research papers | Recent papers in domain |
| **production** | Real user data | Consent + anonymization |
| **human_crafted** | Domain expert examples | Expert validation |

---

## Validation Workflow

```
DRAFT → PENDING_REVIEW → VALIDATED → RELEASED
  │           │              │           │
  └─(create)  └─(2/3 approve) └─(git tag) └─(LangSmith sync)
```

**Approval Requirements:**
- 2 of 3 reviewers must approve
- Quality score ≥ 0.7
- All required fields present
- Scoring rubric weights sum to 1.0

---

## Scoring Rubric Weights

Default weights (must sum to 1.0):

```python
{
  "correctness": 0.5,    # Most important
  "completeness": 0.3,   # Required fields
  "quality": 0.2,        # Text quality
  "latency": 0.0,        # Optional (use if needed)
  "cost": 0.0            # Optional (use if needed)
}
```

---

## CI/CD Integration

**GitHub Actions** (`.github/workflows/evaluation-dataset-validation.yml`):

```yaml
on:
  pull_request:
    paths:
      - 'backend/app/evaluation/datasets/v2/**'

jobs:
  validate:
    - name: Validate schema
      run: python -m app.evaluation.schemas.validation --directory datasets/v2/
    - name: Run regression tests
      run: pytest backend/tests/evaluation/ --dataset-version v2
```

---

## Python API Usage

### Load Dataset

```python
from app.evaluation.datasets import load_dataset_v2

dataset = load_dataset_v2("agent_analysis_golden_v2")
for example in dataset.examples:
    print(example.id, example.validation.status)
```

### Validate Dataset

```python
from app.evaluation.schemas.validation import validate_dataset

result = validate_dataset("datasets/v2/agent/agent_analysis_golden_v2.json")
if result.is_valid:
    print(f"✅ Valid: {result.example_count} examples")
else:
    for error in result.errors:
        print(f"❌ {error}")
```

### Extract from LangSmith

```python
from app.evaluation.ingestion.langsmith_extractor import (
    LangSmithExtractor,
    ExtractionConfig,
)

config = ExtractionConfig(
    project_name="skillforge-prod",
    task_type="agent",
    agent_type="security_auditor",
    min_confidence=0.85,
)

extractor = LangSmithExtractor()
examples = extractor.extract(config)
extractor.save_dataset(examples, "datasets/drafts/security.json")
```

---

## Versioning Strategy

```
MAJOR.MINOR.PATCH
  │     │     └─ Bug fixes in examples
  │     └─────── New examples added
  └───────────── Schema changes (breaking)

Examples:
  2.0.0 → 2.1.0  (added 10 examples)
  2.1.0 → 2.1.1  (fixed typo in example)
  2.1.1 → 3.0.0  (schema breaking change)
```

---

## Troubleshooting

### Schema Validation Fails

```bash
# Check specific error
python -m app.evaluation.schemas.validation \
  --dataset datasets/v2/agent/my_dataset.json

# Common issues:
# - Weights don't sum to 1.0
# - Missing required fields
# - Invalid provenance source
# - Missing validation status
```

### LangSmith Extraction Returns Empty

```bash
# Check criteria
python -m app.evaluation.ingestion.langsmith_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --min-confidence 0.5  # Lower threshold
  --max-latency-ms 10000  # Increase limit
  --limit 200  # More traces
```

### Approval Gate Blocked

```bash
# Check approval status
grep -A 5 '"validation"' datasets/v2/agent/my_dataset.json

# Need ≥2 approvals:
# "validated_by": [
#   {"reviewer": "user1", "approved": true},
#   {"reviewer": "user2", "approved": true}
# ]
```

---

## Best Practices

1. **Always validate** before committing: `make validate-datasets`
2. **Use LangSmith** for high-confidence production examples
3. **Add adversarial** examples to test robustness
4. **Version control** all datasets with Git tags
5. **Document provenance** completely (source, URL, notes)
6. **2/3 consensus** for validation approval
7. **Test regression** on every dataset update
8. **Archive old versions** before releasing new ones

---

## Resources

- **Full Architecture**: `docs/evaluation/DATASET_V2_ARCHITECTURE.md`
- **JSON Schema**: `backend/app/evaluation/schemas/dataset_v2_schema.json`
- **Example Dataset**: `backend/app/evaluation/datasets/agent_analysis_golden_v2.json`
- **CI Workflow**: `.github/workflows/evaluation-dataset-validation.yml`

---

**Last Updated**: December 10, 2025
**Maintained By**: Yonatan Gross

# Evaluation Dataset System v2.0 - Executive Summary

**Date:** December 10, 2025
**Status:** Design Complete, Ready for Implementation
**Designed By:** Backend System Architect (AI Agent)

---

## Problem Statement

SkillForge's current evaluation dataset system (v1.0) has critical limitations:

- ❌ **All synthetic data** - No real production examples
- ❌ **No schema validation** - Data quality issues
- ❌ **No versioning** - Can't reproduce evaluations
- ❌ **No provenance tracking** - Unknown example origins
- ❌ **No human validation** - Low-quality examples slip through
- ❌ **No edge cases** - Limited robustness testing

**Impact**: Cannot confidently evaluate agent performance, detect regressions, or conduct A/B testing.

---

## Solution: Evaluation Dataset System v2.0

A production-grade evaluation dataset system with:

1. **Provenance Tracking** - Know the source of every example
2. **Human Validation Workflow** - Multi-reviewer approval (2/3 consensus)
3. **Version Control** - Semantic versioning with Git tags
4. **Scoring Rubrics** - Customizable evaluation criteria per example
5. **Edge Cases & Adversarial Examples** - Systematic robustness testing
6. **Integration** - LangSmith traces, GitHub issues, arXiv papers
7. **CI/CD Automation** - Validation on every PR, regression testing

---

## Architecture Overview

```
DATA SOURCES               INGESTION                VALIDATION              RELEASE
════════════               ═════════                ══════════              ═══════

┌─────────────┐           ┌─────────────┐          ┌──────────┐           ┌─────────┐
│ LangSmith   │──────────▶│  Extractor  │─────────▶│ Reviewer │──────────▶│ Git Tag │
│ Traces      │           │  (CI ≥0.85) │          │ (2/3 OK) │           │ v2.x.x  │
└─────────────┘           └─────────────┘          └──────────┘           └─────────┘
                                 │                       │                      │
┌─────────────┐                  │                       │                      │
│ GitHub      │──────────────────┤                       │                      │
│ Issues      │                  │                       │                      │
└─────────────┘                  ▼                       ▼                      ▼
                          ┌─────────────┐          ┌──────────┐           ┌─────────┐
┌─────────────┐           │ Normalize   │          │ Approval │           │ Upload  │
│ arXiv       │──────────▶│ to v2.0     │─────────▶│ Gate     │──────────▶│ to      │
│ Papers      │           │ Schema      │          │ (quality)│           │LangSmith│
└─────────────┘           └─────────────┘          └──────────┘           └─────────┘
                                 │                       │
┌─────────────┐                  │                       │
│ Synthetic   │──────────────────┘                       │
│ (Manual)    │                                          │
└─────────────┘                                          ▼
                                                    ┌──────────┐
                                                    │ CI/CD    │
                                                    │ Tests    │
                                                    └──────────┘
```

---

## Key Features

### 1. JSON Schema v2.0

Comprehensive schema with:
- **Inputs**: Content, content type, agent type
- **Expected Outputs**: Primary + acceptable alternatives + forbidden outputs
- **Evaluation Criteria**: Weighted scoring rubric (correctness, completeness, quality)
- **Provenance**: Source type, created date, creator, source URL, trace ID
- **Validation**: Status, reviewers, quality score
- **Metadata**: Difficulty, edge_case flag, adversarial flag, tags

**File**: `/Users/yonatangross/coding/SkillForge/backend/app/evaluation/schemas/dataset_v2_schema.json`

### 2. Provenance Tracking

Every example records its origin:

| Source | Use Case | Selection Criteria |
|--------|----------|-------------------|
| `synthetic` | Hand-crafted | Expert validation |
| `langsmith` | Production traces | Confidence ≥0.85, no errors, latency <5s |
| `github` | Bug reports | Closed issues with labels: bug, security, edge-case |
| `arxiv` | Research papers | Recent papers in relevant domains |
| `production` | Real user data | Consent + PII anonymization |
| `human_crafted` | Expert examples | Domain expert validation |

### 3. Human Validation Workflow

```
DRAFT → PENDING_REVIEW → VALIDATED → RELEASED
  │           │              │           │
  └─(create)  └─(2/3 approve) └─(git tag) └─(sync)

Approval Requirements:
- 2 of 3 reviewers must approve
- Quality score ≥ 0.7
- All required fields present
- Scoring rubric weights sum to 1.0
```

### 4. Version Control

**Semantic Versioning** (2.x.x):
- **MAJOR** (2.x.x → 3.x.x): Schema changes (breaking)
- **MINOR** (2.1.x → 2.2.x): New examples added
- **PATCH** (2.1.1 → 2.1.2): Bug fixes in existing examples

**Git Tags**: `eval-datasets-v2.0.0`, `eval-datasets-v2.1.0`, etc.

**Archived Copies**: Old versions saved in `datasets/archived/` for historical reference

### 5. Scoring Rubrics

Customizable weighted evaluation criteria per example:

```json
{
  "scoring_rubric": {
    "correctness": {
      "weight": 0.5,
      "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.5}
    },
    "completeness": {
      "weight": 0.3,
      "required_fields": ["primary_tech", "alternatives", "recommendation"]
    },
    "quality": {
      "weight": 0.2,
      "min_length": 100,
      "max_length": 2000,
      "keywords": ["React Compiler", "Server Components"]
    }
  }
}
```

Weights must sum to 1.0 (validated automatically).

### 6. Edge Cases & Adversarial Examples

Systematic robustness testing with flags:

- **`edge_case: true`**: Uncommon scenarios that test boundary conditions
- **`adversarial: true`**: Deliberately misleading content to test critical thinking

**Example**: Article recommending Excel for machine learning (agent should reject despite persuasive content).

### 7. CI/CD Integration

**GitHub Actions Workflow** (`.github/workflows/evaluation-dataset-validation.yml`):

1. **Schema Validation**: Check all datasets comply with v2.0 schema
2. **Provenance Completeness**: Verify all examples have complete provenance
3. **Regression Testing**: Run evaluations against previous release, detect performance drops
4. **PR Comments**: Post validation results as PR comment

**Triggers**: On PR to `datasets/v2/**` paths

---

## Integration Points

### LangSmith Integration

**Purpose**: Extract high-quality examples from production traces

**Selection Criteria**:
- Confidence score ≥ 0.85
- No errors in trace
- Latency < 5000ms
- User feedback positive (if available)

**Command**:
```bash
python -m app.evaluation.ingestion.langsmith_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --min-confidence 0.85 \
  --output datasets/drafts/langsmith_extract.json
```

**Metadata Captured**: Trace ID, model used, latency, cost, input/output tokens

### GitHub Issues Integration

**Purpose**: Import edge cases and bug reports as adversarial examples

**Selection Criteria**:
- Labels: `bug`, `security`, `edge-case`, `false-positive`
- Status: Closed (with fix)
- Contains reproducible example

**Command**:
```bash
python -m app.evaluation.ingestion.github_importer \
  --repo ArieGoldkin/SkillForge \
  --labels "bug,security,edge-case" \
  --output datasets/drafts/github_issues.json
```

### arXiv Papers Integration

**Purpose**: Import research-backed examples for domain coverage

**Use Cases**:
- Cutting-edge tech comparisons
- Security vulnerabilities from research
- Performance optimization techniques

**Command**:
```bash
python -m app.evaluation.ingestion.arxiv_importer \
  --query "machine learning security" \
  --max-papers 10 \
  --output datasets/drafts/arxiv_ml_security.json
```

### pytest Integration

**Automatic Dataset Loading**:

```python
# backend/tests/evaluation/conftest.py
import pytest
from app.evaluation.datasets import load_dataset_v2

@pytest.fixture
def agent_golden_dataset():
    return load_dataset_v2("agent_analysis_golden_v2")

# Usage in tests
def test_tech_comparator(agent_golden_dataset):
    for example in agent_golden_dataset.examples:
        result = run_tech_comparator(example.inputs)
        score = evaluate_with_rubric(result, example)
        assert score >= 0.7, f"Example {example.id} failed"
```

---

## File Structure

```
backend/app/evaluation/
├── schemas/
│   ├── dataset_v2_schema.json         ← JSON Schema definition
│   └── validation.py                  ← Schema validation tool
│
├── datasets/
│   ├── v1/                             ← Legacy v1 datasets (deprecated)
│   ├── v2/                             ← Current v2 datasets
│   │   ├── agent/
│   │   │   ├── agent_analysis_golden_v2.json
│   │   │   ├── tech_comparator_edge_cases_v2.json
│   │   │   └── security_auditor_adversarial_v2.json
│   │   ├── supervisor/
│   │   │   └── supervisor_routing_golden_v2.json
│   │   └── synthesis/
│   │       └── synthesis_aggregation_golden_v2.json
│   ├── drafts/                         ← Work-in-progress datasets
│   └── archived/                       ← Old versions for historical reference
│
├── ingestion/                          ← Data pipeline tools
│   ├── langsmith_extractor.py         ← Extract from LangSmith traces
│   ├── github_importer.py             ← Import from GitHub issues
│   ├── arxiv_importer.py              ← Import from arXiv papers
│   └── normalizer.py                  ← Normalize to v2 schema
│
├── validation/                         ← Human validation workflow
│   ├── reviewer_cli.py                ← CLI tool for reviewers
│   ├── approval_gate.py               ← 2/3 consensus checking
│   └── quality_metrics.py             ← Quality score calculation
│
├── versioning/                         ← Version control utilities
│   ├── tagger.py                      ← Git tag creation
│   ├── changelog.py                   ← Generate CHANGELOG.md
│   └── differ.py                      ← Dataset diff tool
│
└── exporters/                          ← Export to various formats
    ├── langsmith_uploader.py          ← Upload to LangSmith
    └── pytest_adapter.py              ← Pytest fixtures
```

---

## Implementation Timeline

### Week 1: Ingestion Layer
- ✅ LangSmith trace extractor (done)
- 🔲 GitHub issue importer
- 🔲 arXiv paper importer
- 🔲 Schema normalizer

### Week 2: Validation Workflow
- 🔲 Reviewer CLI tool
- 🔲 Approval gate logic
- 🔲 Quality metrics calculation

### Week 3: Version Control
- 🔲 Git tagging script
- 🔲 Changelog generator
- 🔲 Dataset differ tool

### Week 4: CI/CD Integration
- 🔲 GitHub Actions workflow
- 🔲 Regression test framework
- 🔲 Automated LangSmith sync

### Week 5: Migration
- 🔲 Migrate v1 datasets to v2
- 🔲 Update documentation
- 🔲 Train team on new workflow

---

## Benefits Summary

| Feature | v1.0 | v2.0 |
|---------|------|------|
| **Provenance Tracking** | ❌ All synthetic | ✅ 6 sources (LangSmith/GitHub/arXiv/etc) |
| **Human Validation** | ❌ No workflow | ✅ Multi-reviewer approval (2/3) |
| **Versioning** | ❌ No versions | ✅ Semantic versioning + Git tags |
| **Scoring Rubrics** | ❌ Fixed criteria | ✅ Weighted, customizable rubrics |
| **Edge Cases** | ❌ No flags | ✅ Edge case + adversarial flags |
| **CI/CD Integration** | ❌ Manual | ✅ Automated validation + regression tests |
| **LangSmith Sync** | ❌ Manual upload | ✅ Automated sync via pipeline |

---

## Metrics & Success Criteria

### Dataset Quality Metrics

| Metric | Target | Current (v1.0) |
|--------|--------|----------------|
| Total Examples | 200+ | 41 |
| Production Examples | 50+ | 0 |
| Edge Cases | 20+ | 0 |
| Adversarial Examples | 10+ | 0 |
| Validation Rate | 100% | 0% |
| Provenance Tracking | 100% | 0% |

### Evaluation Performance Metrics

| Metric | Target |
|--------|--------|
| Regression Detection | 95%+ |
| A/B Test Confidence | ≥0.95 |
| CI/CD Runtime | <5 min |
| Schema Validation | 100% |

---

## Next Steps

1. **Review & Approve Design** (This document)
2. **Implement Week 1 Tasks** (Ingestion layer)
3. **Test with 10 Production Examples** (Validate workflow)
4. **Build Week 2 Tasks** (Validation workflow)
5. **Pilot with Team** (Get feedback)
6. **Full Rollout** (Weeks 3-5)

---

## Documentation

- **Full Architecture**: [DATASET_V2_ARCHITECTURE.md](/Users/yonatangross/coding/SkillForge/docs/evaluation/DATASET_V2_ARCHITECTURE.md)
- **Quick Reference**: [DATASET_V2_QUICK_REFERENCE.md](/Users/yonatangross/coding/SkillForge/docs/evaluation/DATASET_V2_QUICK_REFERENCE.md)
- **JSON Schema**: [dataset_v2_schema.json](/Users/yonatangross/coding/SkillForge/backend/app/evaluation/schemas/dataset_v2_schema.json)
- **Example Dataset**: [agent_analysis_golden_v2.json](/Users/yonatangross/coding/SkillForge/backend/app/evaluation/datasets/agent_analysis_golden_v2.json)
- **Validation Tool**: [validation.py](/Users/yonatangross/coding/SkillForge/backend/app/evaluation/schemas/validation.py)
- **LangSmith Extractor**: [langsmith_extractor.py](/Users/yonatangross/coding/SkillForge/backend/app/evaluation/ingestion/langsmith_extractor.py)

---

## Contact

**Designed By**: Backend System Architect (AI Agent)
**Maintained By**: Yonatan Gross
**Date**: December 10, 2025
**Status**: ✅ Design Complete, Ready for Implementation

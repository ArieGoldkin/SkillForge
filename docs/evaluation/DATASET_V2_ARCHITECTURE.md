# Evaluation Dataset v2.0 - Architecture Design

**Version:** 2.0.0
**Date:** December 10, 2025
**Status:** Design Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Data Pipeline Architecture](#data-pipeline-architecture)
3. [File/Folder Structure](#filefolder-structure)
4. [Integration Points](#integration-points)
5. [Workflow Diagrams](#workflow-diagrams)
6. [Migration Guide](#migration-guide)

---

## Overview

The Evaluation Dataset v2.0 system introduces:

- **Provenance Tracking**: Every example records its origin (synthetic, LangSmith, GitHub, arXiv, production)
- **Human Validation Workflow**: Multi-reviewer approval process with quality scoring
- **Version Control**: Semantic versioning with Git tags for dataset releases
- **Scoring Rubrics**: Weighted evaluation criteria (correctness, completeness, quality, latency, cost)
- **Edge Cases & Adversarial Examples**: Flags for robustness testing
- **Integration**: LangSmith trace extraction, GitHub issue import, CI/CD automation

---

## Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EVALUATION DATASET PIPELINE v2.0                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DATA SOURCES                   INGESTION LAYER                            │
│   ════════════                   ════════════════                            │
│                                                                             │
│   ┌──────────────┐              ┌──────────────────┐                       │
│   │  LangSmith   │─────────────▶│  Trace Extractor │                       │
│   │   Traces     │              │  (production     │                       │
│   └──────────────┘              │   examples)      │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│   ┌──────────────┐              ┌──────────────────┐                       │
│   │   GitHub     │─────────────▶│  Issue Importer  │                       │
│   │   Issues     │              │  (bug reports,   │                       │
│   └──────────────┘              │   edge cases)    │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│   ┌──────────────┐              ┌──────────────────┐                       │
│   │   arXiv      │─────────────▶│  Paper Importer  │                       │
│   │   Papers     │              │  (research       │                       │
│   └──────────────┘              │   content)       │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│   ┌──────────────┐              ┌──────────────────┐                       │
│   │  Synthetic   │─────────────▶│  Manual Creator  │                       │
│   │  (Manual)    │              │  (hand-crafted   │                       │
│   └──────────────┘              │   examples)      │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│                                 ┌──────────────────┐                       │
│                                 │   Normalizer     │                       │
│                                 │   (to v2.0       │                       │
│                                 │    schema)       │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│   VALIDATION WORKFLOW            ┌──────────────────┐                       │
│   ═══════════════════            │  Draft Dataset   │                       │
│                                  │  (status=draft)  │                       │
│   ┌──────────────────┐           └──────────────────┘                       │
│   │  Reviewer 1      │                   │                                  │
│   │  (validates      │◀──────────────────┘                                  │
│   │   quality)       │                                                      │
│   └──────────────────┘                   │                                  │
│            │                             ▼                                  │
│            │                    ┌──────────────────┐                       │
│   ┌──────────────────┐          │ Pending Review   │                       │
│   │  Reviewer 2      │          │ Dataset          │                       │
│   │  (second pass)   │◀─────────│ (2/3 approvals   │                       │
│   └──────────────────┘          │  required)       │                       │
│            │                    └──────────────────┘                       │
│            │                             │                                  │
│            ▼                             ▼                                  │
│   ┌──────────────────┐          ┌──────────────────┐                       │
│   │  Approval Gate   │─────────▶│  Validated       │                       │
│   │  (2/3 consensus) │          │  Dataset         │                       │
│   └──────────────────┘          │  (status=        │                       │
│                                 │   validated)     │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│   VERSIONING & RELEASE           ┌──────────────────┐                       │
│   ══════════════════             │  Version Tagger  │                       │
│                                  │  (semantic       │                       │
│   ┌──────────────────┐           │   versioning)    │                       │
│   │  Git Tag         │           └──────────────────┘                       │
│   │  (v2.1.0)        │◀──────────────────┘                                  │
│   └──────────────────┘                   │                                  │
│                                          ▼                                  │
│                                 ┌──────────────────┐                       │
│                                 │  Release Dataset │                       │
│                                 │  (datasets/v2/)  │                       │
│                                 └──────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│   CONSUMPTION LAYER              ┌──────────────────┐                       │
│   ═══════════════════            │  LangSmith Sync  │                       │
│                                  │  (upload to      │                       │
│   ┌──────────────────┐           │   LangSmith      │                       │
│   │  CI/CD Pipeline  │           │   datasets)      │                       │
│   │  (pytest)        │           └──────────────────┘                       │
│   └──────────────────┘                   │                                  │
│            │                             │                                  │
│            └──────────────┬──────────────┘                                  │
│                           ▼                                                │
│                  ┌──────────────────┐                                       │
│                  │  Evaluation Runs │                                       │
│                  │  (A/B testing,   │                                       │
│                  │   regression)    │                                       │
│                  └──────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File/Folder Structure

```
backend/app/evaluation/
├── schemas/
│   ├── dataset_v2_schema.json         # JSON Schema for v2.0 datasets
│   └── validation.py                  # Schema validation utilities
│
├── datasets/
│   ├── v1/                             # Legacy v1 datasets (deprecated)
│   │   ├── agent_analysis_golden_v1.json
│   │   ├── supervisor_golden_v1.json
│   │   └── synthesis_golden_v1.json
│   │
│   ├── v2/                             # Current v2 datasets
│   │   ├── agent/
│   │   │   ├── agent_analysis_golden_v2.json
│   │   │   ├── tech_comparator_edge_cases_v2.json
│   │   │   └── security_auditor_adversarial_v2.json
│   │   │
│   │   ├── supervisor/
│   │   │   ├── supervisor_routing_golden_v2.json
│   │   │   └── supervisor_edge_cases_v2.json
│   │   │
│   │   └── synthesis/
│   │       └── synthesis_aggregation_golden_v2.json
│   │
│   ├── drafts/                         # Work-in-progress datasets
│   │   ├── draft_langsmith_20251210.json
│   │   └── draft_github_issues_security.json
│   │
│   └── archived/                       # Old versions for historical reference
│       └── agent_analysis_golden_v2.0.0.json
│
├── ingestion/                          # Data pipeline ingestion tools
│   ├── __init__.py
│   ├── langsmith_extractor.py         # Extract examples from LangSmith traces
│   ├── github_importer.py             # Import from GitHub issues
│   ├── arxiv_importer.py              # Import from arXiv papers
│   ├── normalizer.py                  # Normalize to v2 schema
│   └── config.yaml                    # Pipeline configuration
│
├── validation/                         # Human validation workflow
│   ├── __init__.py
│   ├── reviewer_cli.py                # CLI tool for reviewers
│   ├── approval_gate.py               # Consensus checking (2/3 approvals)
│   └── quality_metrics.py             # Quality score calculation
│
├── versioning/                         # Version control utilities
│   ├── __init__.py
│   ├── tagger.py                      # Git tag creation
│   ├── changelog.py                   # Generate CHANGELOG.md
│   └── differ.py                      # Dataset diff tool
│
├── exporters/                          # Export to various formats
│   ├── __init__.py
│   ├── langsmith_uploader.py          # Upload to LangSmith
│   └── pytest_adapter.py              # Pytest fixtures
│
├── evaluators/                         # Evaluation functions (existing)
│   ├── correctness.py
│   ├── cost.py
│   ├── latency.py
│   └── quality.py
│
├── llm_benchmark.py                   # Benchmark runner (existing)
├── run_experiments.py                 # Experiment orchestrator (existing)
└── README.md                          # Usage documentation
```

---

## Integration Points

### 1. LangSmith Integration

**Purpose**: Extract high-quality examples from production traces

```python
# Usage: Extract examples from LangSmith
python -m app.evaluation.ingestion.langsmith_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --min-confidence 0.85 \
  --output datasets/drafts/langsmith_extract_20251210.json
```

**Selection Criteria**:
- Confidence score ≥ 0.85
- Latency < target p95
- No errors in trace
- User feedback positive (if available)

**Metadata Captured**:
- Trace ID
- Model used
- Latency
- Cost
- Input/output tokens

### 2. GitHub Issues Integration

**Purpose**: Import edge cases and bug reports as adversarial examples

```python
# Usage: Import from GitHub issues
python -m app.evaluation.ingestion.github_importer \
  --repo ArieGoldkin/SkillForge \
  --labels "bug,security,edge-case" \
  --output datasets/drafts/github_issues_20251210.json
```

**Selection Criteria**:
- Labels: `bug`, `security`, `edge-case`, `false-positive`
- Status: Closed (with fix)
- Contains reproducible example

### 3. arXiv Papers Integration

**Purpose**: Import research-backed examples for domain coverage

```python
# Usage: Import from arXiv
python -m app.evaluation.ingestion.arxiv_importer \
  --query "machine learning security" \
  --max-papers 10 \
  --output datasets/drafts/arxiv_ml_security.json
```

**Use Cases**:
- Cutting-edge tech comparisons
- Security vulnerabilities from research
- Performance optimization techniques

### 4. CI/CD Integration

**GitHub Actions Workflow** (`.github/workflows/evaluation-dataset-validation.yml`):

```yaml
name: Evaluation Dataset Validation

on:
  pull_request:
    paths:
      - 'backend/app/evaluation/datasets/v2/**'
      - 'backend/app/evaluation/schemas/**'

jobs:
  validate-datasets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install poetry
          poetry install

      - name: Validate schema compliance
        run: |
          python -m app.evaluation.schemas.validation \
            --schema schemas/dataset_v2_schema.json \
            --datasets datasets/v2/**/*.json

      - name: Check provenance completeness
        run: |
          python -m app.evaluation.validation.quality_metrics \
            --check-provenance \
            --datasets datasets/v2/**/*.json

      - name: Run regression tests
        run: |
          pytest backend/tests/evaluation/ \
            --dataset-version v2 \
            --compare-with v2.0.0

      - name: Post PR comment with validation results
        if: always()
        uses: actions/github-script@v8
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('validation_results.json', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Dataset Validation Results\n\n${results}`
            });
```

### 5. Pytest Integration

**Automatic Dataset Loading**:

```python
# backend/tests/evaluation/conftest.py
import pytest
from app.evaluation.datasets import load_dataset_v2

@pytest.fixture
def agent_golden_dataset():
    """Load v2 agent analysis golden dataset."""
    return load_dataset_v2("agent_analysis_golden_v2")

@pytest.fixture
def supervisor_golden_dataset():
    """Load v2 supervisor routing golden dataset."""
    return load_dataset_v2("supervisor_routing_golden_v2")

# Usage in tests
def test_tech_comparator_correctness(agent_golden_dataset):
    """Test tech comparator agent against golden dataset."""
    for example in agent_golden_dataset.examples:
        if example.inputs.get("agent_type") != "tech_comparator":
            continue

        # Run evaluation
        result = run_tech_comparator(example.inputs)

        # Evaluate with rubric
        score = evaluate_with_rubric(
            result,
            example.expected_outputs,
            example.evaluation_criteria
        )

        assert score >= 0.7, f"Example {example.id} failed with score {score}"
```

---

## Workflow Diagrams

### Human Validation Workflow

```
┌───────────────────────────────────────────────────────────────────────────┐
│                      HUMAN VALIDATION WORKFLOW                            │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. DRAFT CREATION                                                        │
│     ════════════════                                                      │
│     ┌─────────────────┐                                                   │
│     │ Ingest Example  │                                                   │
│     │ (any source)    │                                                   │
│     └─────────────────┘                                                   │
│             │                                                             │
│             ▼                                                             │
│     ┌─────────────────┐                                                   │
│     │ Normalize to    │                                                   │
│     │ v2 Schema       │                                                   │
│     └─────────────────┘                                                   │
│             │                                                             │
│             ▼                                                             │
│     ┌─────────────────┐                                                   │
│     │ Save to drafts/ │                                                   │
│     │ status=draft    │                                                   │
│     └─────────────────┘                                                   │
│                                                                           │
│  2. REVIEW ASSIGNMENT                                                     │
│     ══════════════════                                                    │
│     ┌─────────────────┐                                                   │
│     │ Assign 3        │                                                   │
│     │ Reviewers       │                                                   │
│     └─────────────────┘                                                   │
│             │                                                             │
│             ├──────────┬──────────┐                                       │
│             ▼          ▼          ▼                                       │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│     │Reviewer 1│ │Reviewer 2│ │Reviewer 3│                              │
│     └──────────┘ └──────────┘ └──────────┘                              │
│             │          │          │                                       │
│  3. REVIEW PROCESS                                                        │
│     ═══════════════                                                       │
│             ▼          ▼          ▼                                       │
│     ┌──────────────────────────────┐                                     │
│     │ Check Quality:               │                                     │
│     │ - Inputs realistic?          │                                     │
│     │ - Expected outputs correct?  │                                     │
│     │ - Rubric appropriate?        │                                     │
│     │ - Provenance complete?       │                                     │
│     └──────────────────────────────┘                                     │
│             │                                                             │
│             ▼                                                             │
│     ┌──────────────────────────────┐                                     │
│     │ Submit Approval:             │                                     │
│     │ - approved: true/false       │                                     │
│     │ - quality_score: 0-1         │                                     │
│     │ - comments: string           │                                     │
│     └──────────────────────────────┘                                     │
│                                                                           │
│  4. APPROVAL GATE (2/3 Consensus)                                        │
│     ══════════════════════════════                                        │
│     ┌──────────────────────────────┐                                     │
│     │ Count Approvals              │                                     │
│     └──────────────────────────────┘                                     │
│             │                                                             │
│       ┌─────┴──────┐                                                     │
│       ▼            ▼                                                     │
│  ┌────────┐   ┌────────┐                                                │
│  │ ≥ 2/3  │   │ < 2/3  │                                                │
│  │ YES    │   │ NO     │                                                │
│  └────────┘   └────────┘                                                │
│       │            │                                                     │
│       │            ▼                                                     │
│       │    ┌──────────────────┐                                          │
│       │    │ status=           │                                          │
│       │    │ needs_update      │                                          │
│       │    └──────────────────┘                                          │
│       │            │                                                     │
│       │            └──────────────┐                                      │
│       │                           ▼                                      │
│       │                   ┌──────────────┐                              │
│       │                   │ Notify       │                              │
│       │                   │ Contributor  │                              │
│       │                   └──────────────┘                              │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ status=validated │                                                   │
│  └──────────────────┘                                                   │
│       │                                                                 │
│  5. VERSIONING & RELEASE                                                │
│     ════════════════════                                                │
│       ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Calculate        │                                                   │
│  │ Version Bump     │                                                   │
│  │ (major/minor/    │                                                   │
│  │  patch)          │                                                   │
│  └──────────────────┘                                                   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Create Git Tag   │                                                   │
│  │ (v2.1.0)         │                                                   │
│  └──────────────────┘                                                   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Move to          │                                                   │
│  │ datasets/v2/     │                                                   │
│  └──────────────────┘                                                   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Sync to          │                                                   │
│  │ LangSmith        │                                                   │
│  └──────────────────┘                                                   │
│                                                                         │
└───────────────────────────────────────────────────────────────────────────┘
```

### Version Control Strategy

```
Git Repository Structure:
========================

backend/app/evaluation/datasets/
├── v2/
│   ├── agent/
│   │   └── agent_analysis_golden_v2.json  ← Always latest
│   └── supervisor/
│       └── supervisor_routing_golden_v2.json
│
└── archived/
    ├── agent_analysis_golden_v2.0.0.json  ← Tagged release
    ├── agent_analysis_golden_v2.1.0.json
    └── agent_analysis_golden_v2.2.0.json

Git Tags:
=========
eval-datasets-v2.0.0  ← Initial v2 release
eval-datasets-v2.1.0  ← +10 examples from LangSmith
eval-datasets-v2.2.0  ← +5 adversarial examples

Versioning Rules:
=================
MAJOR (2.x.x → 3.x.x):  Schema changes (breaking)
MINOR (2.1.x → 2.2.x):  New examples added
PATCH (2.1.1 → 2.1.2):  Bug fixes in existing examples
```

---

## Migration Guide

### v1.0 → v2.0 Migration

**Script**: `backend/app/evaluation/migration/migrate_v1_to_v2.py`

```python
"""Migrate v1 datasets to v2 schema."""

import json
from datetime import datetime
from pathlib import Path

def migrate_v1_to_v2(v1_path: str, v2_path: str) -> None:
    """Migrate v1 dataset to v2 schema.

    Args:
        v1_path: Path to v1 dataset JSON
        v2_path: Path to save v2 dataset JSON
    """
    # Load v1 dataset
    with open(v1_path) as f:
        v1_data = json.load(f)

    # Create v2 structure
    v2_data = {
        "version": "2.0.0",
        "metadata": {
            "dataset_name": Path(v1_path).stem + "_v2",
            "task_type": infer_task_type(v1_path),
            "agent_types": infer_agent_types(v1_data),
            "domains": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "release_tag": "v2.0.0",
            "description": f"Migrated from v1: {Path(v1_path).name}",
            "maintainers": ["migration-script"]
        },
        "examples": []
    }

    # Migrate each example
    for v1_example in v1_data:
        v2_example = {
            "id": v1_example["id"],
            "inputs": v1_example["inputs"],
            "expected_outputs": {
                "primary": v1_example["outputs"],
                "acceptable_alternatives": [],
                "forbidden_outputs": []
            },
            "evaluation_criteria": {
                "scoring_rubric": generate_default_rubric(),
                "custom_evaluators": []
            },
            "provenance": {
                "source": v1_example["metadata"].get("source", "synthetic"),
                "created_at": datetime.utcnow().isoformat() + "Z",
                "created_by": "v1-migration",
                "notes": "Migrated from v1 dataset"
            },
            "validation": {
                "status": "draft",
                "validated_by": [],
                "quality_score": None
            },
            "metadata": {
                "difficulty": v1_example["metadata"].get("complexity", "medium"),
                "edge_case": False,
                "adversarial": False,
                "tags": [],
                "notes": v1_example["metadata"].get("validation_notes", "")
            }
        }
        v2_data["examples"].append(v2_example)

    # Save v2 dataset
    with open(v2_path, 'w') as f:
        json.dump(v2_data, f, indent=2)

def generate_default_rubric():
    """Generate default scoring rubric for migrated examples."""
    return {
        "correctness": {
            "weight": 0.5,
            "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.5}
        },
        "completeness": {
            "weight": 0.3,
            "required_fields": []
        },
        "quality": {
            "weight": 0.2,
            "min_length": 50,
            "max_length": 5000,
            "keywords": []
        }
    }
```

**Usage**:
```bash
# Migrate all v1 datasets
python -m app.evaluation.migration.migrate_v1_to_v2 \
  --input-dir datasets/v1/ \
  --output-dir datasets/v2/ \
  --validate
```

---

## Usage Examples

### 1. Extract from LangSmith

```bash
# Extract high-confidence examples from production
python -m app.evaluation.ingestion.langsmith_extractor \
  --project-name skillforge-prod \
  --task-type agent \
  --agent-type security_auditor \
  --min-confidence 0.85 \
  --date-range 2025-12-01:2025-12-10 \
  --output datasets/drafts/langsmith_security_20251210.json
```

### 2. Human Review CLI

```bash
# Review draft examples
python -m app.evaluation.validation.reviewer_cli \
  --dataset datasets/drafts/langsmith_security_20251210.json \
  --reviewer yonatangross

# Interactive prompts:
# Example 1/15: agent-sec-langsmith-001
# Status: draft
# Source: langsmith (trace ID: abc123)
#
# Inputs: <displays inputs>
# Expected Outputs: <displays outputs>
#
# Approve this example? (y/n/skip): y
# Quality Score (0-1): 0.92
# Comments: Excellent real-world security example
```

### 3. Version Release

```bash
# Create new dataset release
python -m app.evaluation.versioning.tagger \
  --datasets datasets/v2/agent/*.json \
  --version-type minor \
  --changelog "Added 15 LangSmith examples, 5 adversarial cases"

# Creates:
# - Git tag: eval-datasets-v2.1.0
# - Archived copies in datasets/archived/
# - Updated CHANGELOG.md
```

### 4. CI/CD Integration Test

```bash
# Run regression tests on PR
pytest backend/tests/evaluation/ \
  --dataset-version v2.1.0 \
  --compare-baseline v2.0.0 \
  --threshold 0.02  # Allow 2% performance drop

# Output:
# ✓ correctness: 0.87 (baseline: 0.86, +1.2%)
# ✓ latency_p95: 245ms (baseline: 250ms, -2.0%)
# ✗ cost_total: $0.15 (baseline: $0.12, +25%)  ← ALERT!
```

---

## Benefits Summary

| Feature | v1.0 | v2.0 |
|---------|------|------|
| **Provenance Tracking** | ❌ All synthetic | ✅ LangSmith/GitHub/arXiv/synthetic |
| **Human Validation** | ❌ No workflow | ✅ Multi-reviewer approval |
| **Versioning** | ❌ No versions | ✅ Semantic versioning + Git tags |
| **Scoring Rubrics** | ❌ Fixed criteria | ✅ Weighted, customizable rubrics |
| **Edge Cases** | ❌ No flags | ✅ Edge case + adversarial flags |
| **CI/CD Integration** | ❌ Manual | ✅ Automated validation + regression tests |
| **LangSmith Sync** | ❌ Manual upload | ✅ Automated sync via pipeline |

---

## Next Steps

1. **Implement Ingestion Layer** (Week 1)
   - LangSmith trace extractor
   - GitHub issue importer
   - Schema normalizer

2. **Build Validation Workflow** (Week 2)
   - Reviewer CLI tool
   - Approval gate logic
   - Quality metrics calculation

3. **Version Control Automation** (Week 3)
   - Git tagging script
   - Changelog generator
   - Dataset differ tool

4. **CI/CD Integration** (Week 4)
   - GitHub Actions workflow
   - Regression test framework
   - Automated LangSmith sync

5. **Migration** (Week 5)
   - Migrate v1 datasets to v2
   - Update documentation
   - Train team on new workflow

---

**Maintained By**: Yonatan Gross
**Last Updated**: December 10, 2025
**Status**: Design Complete, Ready for Implementation

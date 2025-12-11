# Evaluation Dataset v2.0 - Architecture Diagrams

**ASCII diagrams for documentation and presentations**

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   EVALUATION DATASET SYSTEM v2.0                            │
│                   Production-Grade Evaluation Framework                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   DATA INGESTION LAYER                                                      │
│   ═══════════════════════                                                   │
│                                                                             │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────┐   │
│   │  LangSmith    │  │   GitHub      │  │    arXiv      │  │ Synthetic│   │
│   │  Traces       │  │   Issues      │  │   Papers      │  │ (Manual) │   │
│   │  (CI ≥0.85)   │  │   (bugs/edge) │  │   (research)  │  │ (expert) │   │
│   └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └─────┬────┘   │
│           │                  │                  │                │        │
│           └──────────────────┼──────────────────┼────────────────┘        │
│                              ▼                  ▼                          │
│                     ┌─────────────────────────────────┐                    │
│                     │      Schema Normalizer          │                    │
│                     │   (Convert to v2.0 Format)      │                    │
│                     └─────────────┬───────────────────┘                    │
│                                   ▼                                        │
│   VALIDATION LAYER                                                          │
│   ══════════════════                                                        │
│                                                                             │
│              ┌─────────────────────────────┐                               │
│              │     Draft Dataset           │                               │
│              │     (status=draft)          │                               │
│              └──────────┬──────────────────┘                               │
│                         │                                                  │
│                         ▼                                                  │
│              ┌─────────────────────────────┐                               │
│              │  Human Review Workflow      │                               │
│              │  ┌───────────────────────┐  │                               │
│              │  │  Reviewer 1 (approve) │  │                               │
│              │  │  Reviewer 2 (approve) │  │                               │
│              │  │  Reviewer 3 (approve) │  │                               │
│              │  └───────────────────────┘  │                               │
│              └──────────┬──────────────────┘                               │
│                         │                                                  │
│                         ▼                                                  │
│              ┌─────────────────────────────┐                               │
│              │  Approval Gate (2/3)        │                               │
│              │  - Quality score ≥ 0.7      │                               │
│              │  - Rubric weights = 1.0     │                               │
│              │  - Required fields present  │                               │
│              └──────────┬──────────────────┘                               │
│                         │                                                  │
│        ┌────────────────┴────────────────┐                                 │
│        │                                 │                                 │
│        ▼                                 ▼                                 │
│   ┌─────────┐                    ┌──────────────┐                         │
│   │Rejected │                    │  Validated   │                         │
│   │(iterate)│                    │  Dataset     │                         │
│   └─────────┘                    └──────┬───────┘                         │
│                                         │                                  │
│   VERSION CONTROL LAYER                 ▼                                  │
│   ═══════════════════════                                                  │
│                                  ┌──────────────┐                          │
│                                  │  Git Tagger  │                          │
│                                  │  (v2.x.x)    │                          │
│                                  └──────┬───────┘                          │
│                                         │                                  │
│                                         ▼                                  │
│                                  ┌──────────────┐                          │
│                                  │  Released    │                          │
│                                  │  Dataset     │                          │
│                                  └──────┬───────┘                          │
│                                         │                                  │
│   CONSUMPTION LAYER                     ▼                                  │
│   ═══════════════════                                                      │
│                                                                             │
│              ┌──────────────┐        ┌──────────────┐                      │
│              │  LangSmith   │        │  CI/CD       │                      │
│              │  Sync        │        │  Pipeline    │                      │
│              └──────┬───────┘        └──────┬───────┘                      │
│                     │                       │                              │
│                     └───────────┬───────────┘                              │
│                                 ▼                                          │
│                        ┌──────────────────┐                                │
│                        │  Evaluation Runs │                                │
│                        │  - A/B Testing   │                                │
│                        │  - Regression    │                                │
│                        │  - Model Compare │                                │
│                        └──────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Pipeline Flow

```
                      EVALUATION DATASET PIPELINE v2.0
                      ═════════════════════════════════

Stage 1: INGESTION               Stage 2: NORMALIZATION
═════════════════                 ══════════════════════

┌────────────────┐                ┌──────────────────┐
│  Production    │                │                  │
│  LangSmith     │───────────────▶│   Normalizer     │
│  Traces        │                │   (to v2.0)      │
└────────────────┘                │                  │
                                  └────────┬─────────┘
┌────────────────┐                         │
│  GitHub        │                         │
│  Issues        │─────────────────────────┤
│  (bug reports) │                         │
└────────────────┘                         │
                                           ▼
┌────────────────┐                ┌──────────────────┐
│  arXiv         │                │  Draft Dataset   │
│  Papers        │───────────────▶│  status=draft    │
│  (research)    │                │  quality=?       │
└────────────────┘                └────────┬─────────┘
                                           │
┌────────────────┐                         │
│  Synthetic     │                         │
│  (hand-crafted)│─────────────────────────┘
└────────────────┘


Stage 3: VALIDATION              Stage 4: RELEASE
════════════════════              ════════════════

┌──────────────────┐              ┌──────────────────┐
│  Human Review    │              │  Git Tag         │
│  ┌────────────┐  │              │  eval-datasets-  │
│  │ Reviewer 1 │  │              │  v2.x.x          │
│  │ Reviewer 2 │  │              └────────┬─────────┘
│  │ Reviewer 3 │  │                       │
│  └────────────┘  │                       ▼
└────────┬─────────┘              ┌──────────────────┐
         │                        │  Archive Old     │
         ▼                        │  Versions        │
┌──────────────────┐              └────────┬─────────┘
│  Approval Gate   │                       │
│  2 of 3 approve  │                       ▼
│  quality ≥ 0.7   │              ┌──────────────────┐
└────────┬─────────┘              │  Upload to       │
         │                        │  LangSmith       │
    PASS │ FAIL                   └────────┬─────────┘
         │  │                              │
         ▼  ▼                              ▼
┌──────────────────┐              ┌──────────────────┐
│  Validated       │              │  CI/CD Testing   │
│  status=validated│              │  - Regression    │
│  quality=0.7-1.0 │              │  - A/B Compare   │
└──────────────────┘              └──────────────────┘
```

---

## Example Data Flow (LangSmith → Validated Dataset)

```
   PRODUCTION TRACE                     EXTRACTED EXAMPLE
   ════════════════                     ═════════════════

┌──────────────────────┐            ┌──────────────────────┐
│ LangSmith Trace      │            │ id: agent-ls-001     │
│ ─────────────────    │            │                      │
│ trace_id: abc123     │   Extract  │ inputs:              │
│ confidence: 0.92     │   ───────▶ │   content: "..."     │
│ latency: 1.2s        │            │   agent_type: "sec"  │
│ no errors            │            │                      │
│                      │            │ expected_outputs:    │
│ inputs: {...}        │            │   primary: {...}     │
│ outputs: {...}       │            │                      │
└──────────────────────┘            │ provenance:          │
                                    │   source: langsmith  │
                                    │   trace_id: abc123   │
                                    │                      │
                                    │ validation:          │
                                    │   status: draft      │
                                    └──────────┬───────────┘
                                               │
                                               ▼
   HUMAN REVIEW                         VALIDATED EXAMPLE
   ════════════                         ═════════════════

Reviewer 1: ✓ Approve (0.9)         ┌──────────────────────┐
Reviewer 2: ✓ Approve (0.85)        │ id: agent-ls-001     │
Reviewer 3: ✓ Approve (0.88)        │                      │
                                    │ validation:          │
Approval Gate: PASS (3/3)           │   status: validated  │
Quality Avg: 0.88                   │   quality_score: 0.88│
                                    │   validated_by: [    │
            │                       │     {reviewer: r1,   │
            │                       │      approved: true},│
            ▼                       │     {reviewer: r2,   │
                                    │      approved: true},│
   GIT TAG & RELEASE                │     {reviewer: r3,   │
   ═════════════════                │      approved: true} │
                                    │   ]                  │
Tag: eval-datasets-v2.1.0           └──────────────────────┘
Changelog: "Added sec example"                 │
Archive: Copy to archived/                     │
Upload: Sync to LangSmith                      ▼
                                    ┌──────────────────────┐
                                    │ Ready for Evaluation │
                                    │ - A/B Testing        │
                                    │ - Regression Tests   │
                                    │ - Model Comparison   │
                                    └──────────────────────┘
```

---

## Scoring Rubric Structure

```
                    EVALUATION CRITERIA
                    ═══════════════════

           Weighted Scoring (must sum to 1.0)


┌──────────────────────────────────────────────────────────┐
│  CORRECTNESS (weight: 0.5)                               │
│  ════════════════════════════                            │
│                                                          │
│  Thresholds:                                             │
│    ┌────────────────────────────────┐                   │
│    │ Perfect:    ≥ 1.0   (100%)    │                   │
│    │ Acceptable: ≥ 0.7   (70%)     │                   │
│    │ Failing:    < 0.7   (<70%)    │                   │
│    └────────────────────────────────┘                   │
│                                                          │
│  Description: Accuracy of outputs vs expected            │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  COMPLETENESS (weight: 0.3)                              │
│  ════════════════════════════                            │
│                                                          │
│  Required Fields:                                        │
│    ☑ primary_tech                                        │
│    ☑ alternatives                                        │
│    ☑ comparison                                          │
│    ☑ recommendation                                      │
│    ☑ confidence_score                                    │
│                                                          │
│  Optional Fields:                                        │
│    ☐ trade_offs                                          │
│    ☐ migration_path                                      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  QUALITY (weight: 0.2)                                   │
│  ════════════════════════                                │
│                                                          │
│  Length Constraints:                                     │
│    Min: 100 characters                                   │
│    Max: 2000 characters                                  │
│                                                          │
│  Required Keywords:                                      │
│    • React Compiler                                      │
│    • Server Components                                   │
│    • Vapor Mode                                          │
│    • Virtual DOM                                         │
│    • ecosystem                                           │
└──────────────────────────────────────────────────────────┘

                TOTAL WEIGHT = 0.5 + 0.3 + 0.2 = 1.0 ✓
```

---

## Validation Status State Machine

```
                 VALIDATION STATUS STATE MACHINE
                 ═══════════════════════════════


    ┌───────┐
    │ START │
    └───┬───┘
        │
        │ (ingest)
        ▼
   ┌────────┐
   │ DRAFT  │◀────────────────────┐
   └────┬───┘                     │
        │                         │
        │ (assign reviewers)      │
        ▼                         │
   ┌─────────────────┐            │
   │ PENDING_REVIEW  │            │ (needs update)
   └─────────┬───────┘            │
             │                    │
             │ (2/3 approve)      │
             ├────────────────────┘
             │
             │ (reject)
             ▼
        ┌──────────┐
        │ REJECTED │──────────────┐
        └──────────┘              │
                                  │ (abandon)
        (quality ≥ 0.7)           │
             │                    │
             ▼                    │
      ┌───────────┐               │
      │ VALIDATED │               │
      └─────┬─────┘               │
            │                     │
            │ (git tag)           │
            ▼                     │
       ┌──────────┐               │
       │ RELEASED │               │
       └──────────┘               │
                                  │
                                  ▼
                              ┌─────────┐
                              │ ARCHIVE │
                              └─────────┘


State Transitions:
═══════════════════

DRAFT → PENDING_REVIEW:  Assign ≥2 reviewers
PENDING_REVIEW → VALIDATED:  ≥2/3 approve + quality ≥0.7
PENDING_REVIEW → NEEDS_UPDATE:  <2/3 approve
PENDING_REVIEW → REJECTED:  Critical issues found
NEEDS_UPDATE → DRAFT:  Author fixes issues
REJECTED → ARCHIVE:  Permanently rejected
VALIDATED → RELEASED:  Git tag + LangSmith sync
RELEASED → ARCHIVE:  New version released
```

---

## File Structure Tree

```
backend/app/evaluation/
│
├── schemas/
│   ├── dataset_v2_schema.json         # JSON Schema definition
│   └── validation.py                  # Schema validation utility
│
├── datasets/
│   ├── v1/                             # Legacy v1 datasets (deprecated)
│   │   ├── agent_analysis_golden_v1.json
│   │   ├── supervisor_golden_v1.json
│   │   └── synthesis_golden_v1.json
│   │
│   ├── v2/                             # Current v2 datasets
│   │   ├── agent/
│   │   │   ├── agent_analysis_golden_v2.json          ← Validated
│   │   │   ├── tech_comparator_edge_cases_v2.json     ← Validated
│   │   │   └── security_auditor_adversarial_v2.json   ← Validated
│   │   │
│   │   ├── supervisor/
│   │   │   ├── supervisor_routing_golden_v2.json      ← Validated
│   │   │   └── supervisor_edge_cases_v2.json          ← Validated
│   │   │
│   │   └── synthesis/
│   │       └── synthesis_aggregation_golden_v2.json   ← Validated
│   │
│   ├── drafts/                         # Work-in-progress datasets
│   │   ├── draft_langsmith_20251210.json              ← Draft
│   │   ├── draft_github_issues_security.json          ← Draft
│   │   └── draft_arxiv_ml_security.json               ← Draft
│   │
│   └── archived/                       # Old versions for historical reference
│       ├── agent_analysis_golden_v2.0.0.json
│       ├── agent_analysis_golden_v2.1.0.json
│       └── supervisor_routing_golden_v2.0.0.json
│
├── ingestion/                          # Data pipeline ingestion tools
│   ├── __init__.py
│   ├── langsmith_extractor.py         # Extract from LangSmith traces
│   ├── github_importer.py             # Import from GitHub issues
│   ├── arxiv_importer.py              # Import from arXiv papers
│   ├── normalizer.py                  # Normalize to v2 schema
│   └── config.yaml                    # Pipeline configuration
│
├── validation/                         # Human validation workflow
│   ├── __init__.py
│   ├── reviewer_cli.py                # CLI tool for reviewers
│   ├── approval_gate.py               # Consensus checking (2/3)
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
│   ├── __init__.py
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

## Integration Points Diagram

```
                    INTEGRATION ECOSYSTEM
                    ═════════════════════


     EXTERNAL SYSTEMS              EVALUATION SYSTEM             CONSUMERS
     ════════════════              ═════════════════             ══════════

┌─────────────────┐              ┌─────────────────┐          ┌──────────┐
│   LangSmith     │              │                 │          │  pytest  │
│   Production    │─────────────▶│   Dataset v2.0  │─────────▶│  Tests   │
│   Traces        │   Extract    │   Repository    │  Load    │          │
└─────────────────┘              │                 │          └──────────┘
                                 └────────┬────────┘
┌─────────────────┐                      │                    ┌──────────┐
│   GitHub        │                      │                    │  CI/CD   │
│   Issues        │──────────────────────┤                    │  Pipeline│
│   (bugs/edge)   │   Import             │                    │          │
└─────────────────┘                      │                    └──────────┘
                                         │
┌─────────────────┐                      │                    ┌──────────┐
│   arXiv         │                      │                    │ A/B Test │
│   Papers        │──────────────────────┤                    │ Framework│
│   (research)    │   Import             │                    │          │
└─────────────────┘                      │                    └──────────┘
                                         │
                                         ▼                    ┌──────────┐
                              ┌─────────────────┐            │ LangSmith│
                              │   Git Version   │───────────▶│ Dataset  │
                              │   Control       │   Sync     │          │
                              │   (tags)        │            └──────────┘
                              └─────────────────┘


   Data Flow Types:
   ════════════════
   ───────▶  Extract/Import (ingest data)
   ═══════▶  Load (consume data)
   ───────▶  Sync (synchronize)
```

---

## Comparison: v1.0 vs v2.0

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FEATURE COMPARISON                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  FEATURE                         v1.0              v2.0                 │
│  ════════                        ═════              ═════                │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Data Sources                                                    │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ Synthetic (manual)         ✓                   ✓               │    │
│  │ Production traces          ✗                   ✓ (LangSmith)   │    │
│  │ Bug reports                ✗                   ✓ (GitHub)      │    │
│  │ Research papers            ✗                   ✓ (arXiv)       │    │
│  │ Real user data             ✗                   ✓ (with consent)│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Quality Assurance                                               │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ Schema validation          ✗                   ✓ (JSON Schema) │    │
│  │ Human review               ✗                   ✓ (2/3 consensus)│   │
│  │ Quality scoring            ✗                   ✓ (0-1 scale)   │    │
│  │ Provenance tracking        ✗                   ✓ (6 sources)   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Version Control                                                 │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ Semantic versioning        ✗                   ✓ (2.x.x)        │    │
│  │ Git tags                   ✗                   ✓               │    │
│  │ Archived versions          ✗                   ✓               │    │
│  │ Changelog                  ✗                   ✓ (automated)   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Evaluation Features                                             │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ Scoring rubrics            Fixed               ✓ (customizable) │    │
│  │ Edge case flags            ✗                   ✓               │    │
│  │ Adversarial examples       ✗                   ✓               │    │
│  │ Difficulty levels          ✓                   ✓ (4 levels)    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Automation                                                      │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ CI/CD integration          ✗                   ✓ (GitHub Actions)│   │
│  │ Regression testing         ✗                   ✓               │    │
│  │ LangSmith sync             Manual              ✓ (automated)   │    │
│  │ PR validation              ✗                   ✓               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Scale                                                           │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │ Total examples             41                  200+ (target)    │    │
│  │ Production examples        0                   50+ (target)     │    │
│  │ Edge cases                 0                   20+ (target)     │    │
│  │ Adversarial examples       0                   10+ (target)     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

**Generated**: December 10, 2025
**Version**: 2.0.0
**Status**: Design Complete

# Issue #380: Enable Langfuse Dataset Sync for Experiments

**Status:** 📋 Planned
**Branch:** `issue/380-dataset-sync`
**Milestone:** Langfuse Migration Phase 2
**Priority:** 🔵 MEDIUM
**Estimated Effort:** 2-3 hours
**Dependencies:** Issue #372 (Langfuse Migration) - ✅ Complete

---

## Summary

Enable full Langfuse dataset sync for `LLMBenchmark` experiments by removing `local_mode=True` default and implementing dataset creation, versioning, and JSON Schema validation. This allows golden datasets to be visible in Langfuse UI for experiment tracking and A/B testing.

## Key Features

- Dataset creation with automatic versioning (Dec 2025 Langfuse feature)
- `--sync-datasets` flag for `run_experiments.py`
- JSON Schema validation for dataset integrity
- Dataset item versioning tracking
- Experiment comparison in Langfuse UI
- Backwards compatibility with local mode

## Current State

### ✅ What's Working

- `LLMBenchmark` class with `local_mode=True` (bypasses Langfuse)
- Local experiment execution with cost/latency metrics
- Golden datasets in `backend/app/evaluation/datasets/golden/`
  - `supervisor.json` (11 examples)
  - `agent_analysis.json` (15 examples)
  - `synthesis.json` (12 examples)
- Dataset loader with v1.0 and v2.0 format support
- CLI script `run_experiments.py` with preflight checks

### ❌ What's Missing

- No Langfuse dataset sync (lines 448-457 in `llm_benchmark.py`)
- No `--sync-datasets` CLI flag
- No dataset versioning implementation
- No JSON Schema validation
- Experiments only run locally (not visible in Langfuse UI)
- No dataset documentation in Langfuse

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               LANGFUSE DATASET SYNC ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LOCAL MODE (Current - Issue #380 default)                      │
│  ══════════                                                      │
│  run_experiments.py --all                                        │
│       ↓                                                          │
│  LLMBenchmark(local_mode=True)                                   │
│       ↓                                                          │
│  Load golden/supervisor.json → Local list[dict]                 │
│       ↓                                                          │
│  Run target_fn on each example                                   │
│       ↓                                                          │
│  Aggregate metrics locally                                       │
│       ↓                                                          │
│  Return ExperimentResults (NO Langfuse UI visibility)            │
│                                                                 │
│                                                                 │
│  LANGFUSE MODE (Issue #380 Goal)                                │
│  ═════════════                                                   │
│  run_experiments.py --all --sync-datasets                        │
│       ↓                                                          │
│  LLMBenchmark(local_mode=False)                                  │
│       ↓                                                          │
│  1. Load golden/supervisor.json → Local list[dict]              │
│       ↓                                                          │
│  2. Create Langfuse Dataset (if not exists)                      │
│       ├─ langfuse.create_dataset("supervisor_baseline_v1")      │
│       └─ Metadata: {version, created_by, task_type}             │
│       ↓                                                          │
│  3. Upload Examples to Langfuse                                  │
│       ├─ langfuse.create_dataset_item(...)                      │
│       ├─ Auto-versioning (Dec 2025 feature)                     │
│       └─ Track changes over time                                │
│       ↓                                                          │
│  4. Run Langfuse Experiments                                     │
│       ├─ langfuse.evaluate(...)                                 │
│       ├─ Target function executed per example                   │
│       └─ Traces linked to dataset items                         │
│       ↓                                                          │
│  5. View Results in Langfuse UI                                  │
│       ├─ Datasets Tab → View dataset items                       │
│       ├─ Experiments Tab → Compare model runs                    │
│       └─ Analytics → Cost, latency, accuracy trends              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Checklist

### Phase 1: Dataset Sync Implementation (1.5 hours)

- [ ] **Update LLMBenchmark constructor**
  - Change `local_mode=False` default (currently `True`)
  - Add `sync_datasets` parameter (default: `True`)
  - Document mode differences in docstring

- [ ] **Implement dataset creation logic** (1 hour)
  - Extract dataset creation code from `run_experiment()` (lines 461-478)
  - Create `_create_or_sync_dataset()` method
  - Add dataset naming convention: `{dataset_name}_{task_type}_v1`
  - Implement version detection and incremental updates
  - Handle duplicate example detection

- [ ] **Add JSON Schema validation** (30 min)
  - Create `schemas/dataset_schema.json` with JSON Schema
  - Validate examples before upload:
    - Required fields: `inputs`, `outputs`
    - Optional fields: `metadata`
    - Type checking for nested objects
  - Log validation errors with line numbers

### Phase 2: CLI Integration (30 min)

- [ ] **Update `run_experiments.py`**
  - Add `--sync-datasets` flag (default: `False` for backwards compat)
  - Add `--force-sync` flag to re-upload existing datasets
  - Update help text with dataset sync explanation
  - Pass `sync_datasets` to `LLMBenchmark` constructor

- [ ] **Add dataset inspection commands**
  - `--list-langfuse-datasets` - List datasets in Langfuse
  - `--inspect-dataset <name>` - Show dataset metadata
  - `--delete-dataset <name>` - Delete dataset (with confirmation)

### Phase 3: Dataset Versioning (30 min)

- [ ] **Implement versioning strategy**
  - Append timestamp or content hash to dataset name
  - Check if dataset exists before creating
  - Compare local vs Langfuse dataset item count
  - Only upload new/changed examples (incremental sync)

- [ ] **Track dataset metadata**
  - Store creation timestamp
  - Store Python/SDK version
  - Store git commit hash
  - Store dataset JSON Schema version

### Phase 4: Testing (30 min)

- [ ] **Unit tests** - `test_dataset_sync.py`
  - Test dataset creation from golden data
  - Test duplicate detection
  - Test JSON Schema validation (valid/invalid examples)
  - Test versioning logic

- [ ] **Integration tests** - `test_langfuse_datasets.py`
  - Test full sync flow (local → Langfuse)
  - Test incremental sync (only new examples)
  - Verify dataset visible in Langfuse UI
  - Test experiment linking to dataset

- [ ] **Manual validation**
  - Enable Langfuse: `LANGFUSE_ENABLED=true`
  - Run: `python -m app.evaluation.run_experiments --all --sync-datasets`
  - Verify in Langfuse UI:
    - [ ] Datasets tab shows 3 datasets (supervisor, agent, synthesis)
    - [ ] Dataset items match golden dataset counts
    - [ ] Experiment runs appear in Experiments tab
    - [ ] Dataset item versioning tracked (Dec 2025 feature)

## Dataset Naming Convention

```
Format: {dataset_name}_{task_type}_{version}

Examples:
  supervisor_baseline_v1     Golden supervisor routing dataset
  agent_analysis_v1          Golden agent analysis dataset
  synthesis_v1               Golden synthesis dataset

Versioning:
  v1, v2, v3...   Incremental versions (manual)
  _20251219      Timestamp-based (automatic)
  _abc123        Content hash-based (automatic)
```

## JSON Schema Structure

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LLM Evaluation Dataset",
  "type": "object",
  "required": ["version", "metadata", "examples"],
  "properties": {
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version (e.g., '2.0.0')"
    },
    "metadata": {
      "type": "object",
      "required": ["task_type", "description"],
      "properties": {
        "task_type": {
          "type": "string",
          "enum": ["supervisor", "agent", "synthesis"]
        },
        "description": {
          "type": "string"
        },
        "created_at": {
          "type": "string",
          "format": "date-time"
        },
        "created_by": {
          "type": "string"
        }
      }
    },
    "examples": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["inputs", "outputs"],
        "properties": {
          "inputs": {
            "type": "object",
            "description": "Input parameters for task"
          },
          "outputs": {
            "type": "object",
            "description": "Expected output/reference"
          },
          "metadata": {
            "type": "object",
            "description": "Optional metadata (tags, categories)"
          }
        }
      }
    }
  }
}
```

## Code Patterns

### Dataset Creation Pattern

```python
from langfuse import get_client

async def _create_or_sync_dataset(
    self,
    dataset_name: str,
    task_type: str,
    examples: list[dict[str, Any]],
) -> str:
    """Create or update Langfuse dataset.

    Returns:
        Langfuse dataset ID
    """
    langfuse = get_client()

    # Create unique dataset name with task type
    lf_dataset_name = f"{dataset_name}_{task_type}_v1"

    # Check if dataset exists
    try:
        dataset = langfuse.get_dataset(name=lf_dataset_name)
        logger.info(
            "dataset_exists",
            name=lf_dataset_name,
            item_count=len(dataset.items),
        )
        return dataset.id
    except Exception:
        # Dataset doesn't exist, create it
        pass

    # Create dataset
    dataset = langfuse.create_dataset(
        name=lf_dataset_name,
        description=f"Golden dataset for {task_type} task evaluation",
        metadata={
            "task_type": task_type,
            "version": "1.0.0",
            "created_by": "evaluation-pipeline",
            "git_commit": get_git_commit(),
        },
    )

    logger.info(
        "dataset_created",
        name=lf_dataset_name,
        dataset_id=dataset.id,
    )

    # Upload examples (auto-versioned in Dec 2025!)
    for idx, example in enumerate(examples):
        try:
            langfuse.create_dataset_item(
                dataset_id=dataset.id,
                input=example.get("inputs", {}),
                expected_output=example.get("outputs", {}),
                metadata={
                    **example.get("metadata", {}),
                    "index": idx,
                },
            )
        except Exception as e:
            logger.warning(
                "dataset_item_creation_failed",
                index=idx,
                error=str(e),
            )

    return dataset.id
```

### CLI Usage Pattern

```bash
# List available datasets
python -m app.evaluation.run_experiments --list-datasets

# Run experiments with dataset sync
python -m app.evaluation.run_experiments \
  --all \
  --sync-datasets \
  --output results.json

# Run specific task with Langfuse sync
python -m app.evaluation.run_experiments \
  --task supervisor \
  --sync-datasets

# Force re-sync existing datasets
python -m app.evaluation.run_experiments \
  --all \
  --sync-datasets \
  --force-sync

# List Langfuse datasets
python -m app.evaluation.run_experiments --list-langfuse-datasets
```

## Acceptance Criteria

### Functional Requirements

- [ ] `--sync-datasets` flag added to `run_experiments.py`
- [ ] Golden datasets uploadable to Langfuse
- [ ] Datasets visible in Langfuse UI (Datasets tab)
- [ ] Experiments linked to datasets (Experiments tab)
- [ ] Dataset item versioning tracked automatically
- [ ] JSON Schema validation passes for all golden datasets
- [ ] Incremental sync only uploads new examples

### Data Quality

- [ ] All golden datasets pass JSON Schema validation
- [ ] Dataset metadata includes task_type, version, created_at
- [ ] Example count matches between local and Langfuse
- [ ] No duplicate examples uploaded
- [ ] Dataset versioning tracked in Langfuse UI

### Code Quality

- [ ] All modified files pass linting: `ruff format --check && ruff check && ty check`
- [ ] Test coverage ≥80% maintained
- [ ] Unit tests for dataset sync logic
- [ ] Integration tests with real Langfuse instance
- [ ] Documentation updated

### User Experience

- [ ] CLI help text clear and actionable
- [ ] Error messages provide recovery steps
- [ ] Progress output during dataset upload
- [ ] Dataset sync completion confirmation
- [ ] Langfuse URL printed after sync

## Files to Modify

### Core Implementation (3 files)

1. **`backend/app/evaluation/llm_benchmark.py`**
   - Change `local_mode=False` default
   - Extract dataset sync logic to `_create_or_sync_dataset()`
   - Add versioning and duplicate detection
   - Add JSON Schema validation call

2. **`backend/app/evaluation/run_experiments.py`**
   - Add `--sync-datasets` flag
   - Add `--force-sync` flag
   - Add `--list-langfuse-datasets` command
   - Pass flags to `LLMBenchmark` constructor

3. **`backend/app/evaluation/datasets/__init__.py`**
   - Add `validate_dataset_schema()` function
   - Add `get_dataset_hash()` for versioning
   - Export validation utilities

### Schema & Tests (3 new files)

4. **`backend/app/evaluation/schemas/dataset_schema.json`** (NEW)
   - JSON Schema for dataset validation
   - Enforce required fields and types

5. **`backend/tests/unit/evaluation/test_dataset_sync.py`** (NEW)
   - Test dataset creation logic
   - Test duplicate detection
   - Test JSON Schema validation
   - Test versioning

6. **`backend/tests/integration/evaluation/test_langfuse_datasets.py`** (NEW)
   - Test full sync flow
   - Test incremental sync
   - Verify Langfuse UI visibility

## Current Golden Datasets

| Dataset | Path | Examples | Description |
|---------|------|----------|-------------|
| Supervisor | `golden/supervisor.json` | 11 | Agent routing decisions |
| Agent Analysis | `golden/agent_analysis.json` | 15 | Tech comparator analysis |
| Synthesis | `golden/synthesis.json` | 12 | Multi-agent aggregation |

**Total:** 38 golden examples across 3 task types

## Example Langfuse Dataset Structure

```python
# After sync, datasets appear in Langfuse UI:

Dataset: supervisor_baseline_v1
  ├─ Metadata
  │   ├─ task_type: "supervisor"
  │   ├─ version: "1.0.0"
  │   ├─ created_by: "evaluation-pipeline"
  │   └─ created_at: "2025-12-19T10:30:00Z"
  │
  ├─ Items (11 examples)
  │   ├─ Item 0: FastAPI OAuth2 article
  │   ├─ Item 1: React Server Components tutorial
  │   ├─ Item 2: Kubernetes deployment article
  │   └─ ... (8 more)
  │
  └─ Experiments (linked runs)
      ├─ supervisor_gemini-2.5-flash-lite_20251219_103045
      ├─ supervisor_deepseek-v3_20251219_103125
      └─ supervisor_gpt-4o-mini_20251219_103205
```

## Migration Path

### Step 1: Enable Langfuse (if not already)

```bash
# .env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
```

### Step 2: Test dataset sync locally

```bash
cd backend

# Validate datasets against JSON Schema
python -m app.evaluation.datasets validate

# Dry run (no upload)
python -m app.evaluation.run_experiments --dry-run --sync-datasets

# Upload to Langfuse
python -m app.evaluation.run_experiments --all --sync-datasets
```

### Step 3: Verify in Langfuse UI

1. Open `http://localhost:3000`
2. Navigate to **Datasets** tab
3. Verify datasets:
   - `supervisor_baseline_v1` (11 items)
   - `agent_analysis_v1` (15 items)
   - `synthesis_v1` (12 items)
4. Click dataset → View items → Verify inputs/outputs

### Step 4: Run experiment

```bash
python -m app.evaluation.run_experiments \
  --task supervisor \
  --models gemini-2.5-flash-lite,gpt-4o-mini \
  --output results.json
```

### Step 5: Compare in Langfuse UI

1. Navigate to **Experiments** tab
2. Find experiment runs (e.g., `supervisor_gemini-2.5-flash-lite_...`)
3. Click **Compare** to see side-by-side metrics
4. View cost, latency, accuracy breakdown

## Benefits of Dataset Sync

### For Development

- **Visual debugging**: See dataset items in Langfuse UI
- **Version tracking**: Automatic versioning on every change
- **Experiment history**: Compare runs over time
- **Collaboration**: Share datasets across team

### For Evaluation

- **Linked experiments**: Traces linked to dataset items
- **Dataset evolution**: Track how golden set improves
- **A/B testing**: Compare models on same dataset
- **Reproducibility**: Pin dataset version in experiments

### For Compliance

- **Audit trail**: Track who created/modified datasets
- **Data lineage**: See dataset → experiment → trace flow
- **Schema enforcement**: JSON Schema validation
- **Rollback support**: Revert to previous dataset version

## Related Issues

- **#372**: Langfuse Migration (dependency, complete)
- **#378**: Session & User Tracking (complementary)
- **#383**: Token/Cost Tracking (uses same experiments)
- **#379**: Prompt Management (dataset versioning patterns)

## Resources

- [Langfuse Dataset API](https://langfuse.com/docs/datasets/overview)
- [Dataset Item Versioning (Dec 2025)](https://langfuse.com/changelog/2025-12-15-dataset-item-versioning)
- [Langfuse Experiments](https://langfuse.com/docs/datasets/experiments)
- [JSON Schema Documentation](https://json-schema.org/understanding-json-schema/)
- [LLMBenchmark Implementation](../../../backend/app/evaluation/llm_benchmark.py)

---

**Created:** December 19, 2025
**Author:** Claude Code
**Last Updated:** December 19, 2025

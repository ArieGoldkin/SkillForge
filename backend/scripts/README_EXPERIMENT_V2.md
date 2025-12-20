# Langfuse Experiment Runner v2

## Quick Start

### 1. Test Your Setup

Before running experiments, verify your Langfuse setup:

```bash
cd backend
poetry run python scripts/test_langfuse_pattern.py
```

This will check:
- Environment variables are set
- Langfuse SDK can connect
- Dataset exists and has items
- `item.run()` context manager works
- Scoring works

### 2. Create Dataset (First Time Only)

```bash
poetry run python scripts/run_langfuse_experiment_v2.py --create-dataset
```

This creates the `skillforge-golden-analysis` dataset in Langfuse from your golden data.

### 3. Run a Quick Test Experiment

```bash
poetry run python scripts/run_langfuse_experiment_v2.py --quick
```

Evaluates 3 examples to verify everything works.

### 4. Run Full Experiment

```bash
# All examples
poetry run python scripts/run_langfuse_experiment_v2.py --full

# Limit to specific number
poetry run python scripts/run_langfuse_experiment_v2.py --full --max-examples 10

# Custom experiment name
poetry run python scripts/run_langfuse_experiment_v2.py --full --experiment-name "baseline-v1"
```

## Environment Setup

Required environment variables (in `.env`):

```bash
# Langfuse configuration
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# Optional: Gemini API key for G-Eval
GOOGLE_API_KEY=...
```

## What Changed from v1

### v1 Issues (BROKEN)

- ❌ Generated random trace IDs never linked to dataset items
- ❌ Used fabricated API methods (`create_experiment()`, `log_experiment_run()`)
- ❌ Scores submitted to orphaned traces
- ❌ Results didn't appear in Langfuse UI under Datasets > Runs

### v2 Fixes (CORRECT)

- ✅ Uses `langfuse.get_dataset()` to fetch dataset with items
- ✅ Uses `item.run()` context manager for proper trace linking
- ✅ Scores submitted via `observation.score()` on the observation object
- ✅ Results appear in Langfuse UI under Datasets > Runs

## Verification

After running an experiment, check Langfuse UI:

1. **Datasets Tab**
   - Navigate to `skillforge-golden-analysis` dataset
   - Should see all dataset items

2. **Runs Tab** (under dataset)
   - Should see experiment run (e.g., `g_eval_quality_v1734719823`)
   - Each item shows evaluation trace
   - Click on a trace to see scores

3. **Scores Tab**
   - Filter by score names: `g_eval_overall`, `g_eval_completeness`, etc.
   - Should see scores linked to traces

## Architecture

```
run_langfuse_experiment_v2.py
│
├── create_langfuse_dataset()
│   ├── Load golden dataset (evaluation/datasets)
│   ├── Create Langfuse dataset
│   └── Add dataset items
│
└── run_experiment()
    ├── Fetch dataset from Langfuse
    ├── For each dataset item:
    │   ├── item.run(run_name=experiment_name)  # Context manager
    │   ├── Run g_eval_score()
    │   ├── observation.end(output=...)
    │   └── observation.score(...)  # Per-criterion scores
    └── langfuse.flush()
```

## Experiment Results

Results are stored in multiple places:

1. **Langfuse UI** - Full interactive exploration
2. **Return value** - Python dict with summary
3. **Logs** - Structured logging via `get_logger()`

Example return value:

```python
{
    "status": "success",
    "experiment_name": "g_eval_quality_v1734719823",
    "example_count": 10,
    "successful_count": 10,
    "average_score": 0.78,
    "results": [
        {
            "item_id": "abc123",
            "agent_type": "tech_comparator",
            "overall": 0.85,
            "confidence": 0.92,
            "criteria": {
                "completeness": {"score": 4, "normalized": 0.75},
                "accuracy": {"score": 5, "normalized": 1.0},
                "coherence": {"score": 4, "normalized": 0.75},
                "depth": {"score": 4, "normalized": 0.75}
            }
        },
        ...
    ]
}
```

## Troubleshooting

### "Dataset not found"

Run dataset creation first:
```bash
poetry run python scripts/run_langfuse_experiment_v2.py --create-dataset
```

### "Langfuse not enabled"

Check your `.env`:
```bash
LANGFUSE_ENABLED=true  # Must be 'true', not 'false'
```

### "Connection refused"

Make sure Langfuse is running:
```bash
# Check if Langfuse is accessible
curl http://localhost:3000/api/public/health
```

### Scores not appearing in UI

1. Check experiment completed successfully (no errors)
2. Wait a few seconds for Langfuse to process
3. Refresh Langfuse UI
4. Check if `langfuse.flush()` was called

## Files

- `run_langfuse_experiment_v2.py` - Main experiment runner (v2)
- `run_langfuse_experiment.py` - Original script (v1 - DEPRECATED)
- `test_langfuse_pattern.py` - Setup verification test
- `LANGFUSE_EXPERIMENT_FIX.md` - Detailed explanation of fixes
- `README_EXPERIMENT_V2.md` - This file

## Next Steps

1. Run test: `poetry run python scripts/test_langfuse_pattern.py`
2. Create dataset: `--create-dataset`
3. Quick test: `--quick`
4. Full experiment: `--full`
5. Analyze results in Langfuse UI
6. Iterate on prompts/models based on scores

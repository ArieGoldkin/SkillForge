# Langfuse Experiment Script Fix

## Problem Summary

The original `run_langfuse_experiment.py` script had fundamental issues:

1. **Random trace IDs**: Generated UUIDs that were never linked to dataset items
2. **Fabricated API methods**: Called `langfuse.create_experiment()` and `log_experiment_run()` which don't exist in the SDK
3. **No dataset item linkage**: Scores were submitted without proper association to dataset items
4. **Results not in UI**: Experiments didn't appear under Datasets > Runs in Langfuse

## The Correct Pattern (from Langfuse docs)

### Method 1: Using `item.run()` context manager (RECOMMENDED)

```python
from langfuse import Langfuse

langfuse = Langfuse()
dataset = langfuse.get_dataset("my-dataset")

for item in dataset.items:
    with item.run(run_name="my-experiment") as observation:
        # Your evaluation logic here
        output = evaluate(item.input)

        # End with output
        observation.end(output=output)

        # Score the observation
        observation.score(name="accuracy", value=0.9)
```

### Method 2: Using `dataset.run_experiment()` (alternative)

```python
def my_task(*, item, **kwargs):
    return evaluate(item.input)

result = dataset.run_experiment(
    name="My Experiment",
    task=my_task
)
```

## What Changed in v2

### ✅ File: `run_langfuse_experiment_v2.py`

#### 1. Proper Dataset Fetching

**Old (v1) - BROKEN:**
```python
# Used custom LangfuseClient wrapper
langfuse = get_langfuse_client()  # Our custom wrapper
lf_dataset = langfuse.create_dataset(...)  # Returns basic object
```

**New (v2) - CORRECT:**
```python
# Use real Langfuse SDK directly
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

# Fetch dataset with items
lf_dataset = langfuse.get_dataset(DATASET_NAME)
all_items = list(lf_dataset.items)
```

#### 2. Proper Trace Linking

**Old (v1) - BROKEN:**
```python
# Generated random UUID that's never linked
trace_id = str(uuid.uuid4())

g_eval_result = await g_eval_score(
    ...,
    trace_id=trace_id,  # This trace_id is orphaned!
)
```

**New (v2) - CORRECT:**
```python
# Use item.run() context manager
with item.run(run_name=experiment_name) as observation:
    # G-Eval runs within this context
    g_eval_result = await g_eval_score(
        ...,
        trace_id=None,  # Uses current trace from context
    )

    # End observation with output
    observation.end(output={...})

    # Score directly on observation
    observation.score(
        name="g_eval_overall",
        value=g_eval_result.overall,
    )
```

#### 3. Proper Score Submission

**Old (v1) - BROKEN:**
```python
# Scores submitted via submit_langfuse_score() helper
# with orphaned trace_id
_submit_g_eval_scores_to_langfuse(
    criteria_scores=...,
    overall=...,
    trace_id=trace_id,  # Random UUID, not linked to dataset
)
```

**New (v2) - CORRECT:**
```python
# Scores submitted directly on observation object
# within item.run() context
for criterion, score_obj in g_eval_result.criteria_scores.items():
    observation.score(
        name=f"g_eval_{criterion}",
        value=score_obj.normalized,
        comment=score_obj.reasoning[:200],
    )

observation.score(
    name="g_eval_overall",
    value=g_eval_result.overall,
    comment=f"Weighted average across {len(criteria)} criteria",
)
```

## Key Differences

| Aspect | v1 (BROKEN) | v2 (CORRECT) |
|--------|-------------|--------------|
| **Client** | Custom `get_langfuse_client()` wrapper | Direct `Langfuse()` SDK |
| **Dataset access** | `create_dataset()` only | `get_dataset()` with `.items` |
| **Trace creation** | Random `uuid.uuid4()` | `item.run()` context manager |
| **Trace linking** | None (orphaned traces) | Automatic via context manager |
| **Score submission** | Helper function with random ID | `observation.score()` directly |
| **UI visibility** | Traces not linked to dataset | Appears under Datasets > Runs |

## Usage

### Create Dataset

```bash
cd backend
poetry run python scripts/run_langfuse_experiment_v2.py --create-dataset
```

### Run Quick Experiment (3 examples)

```bash
poetry run python scripts/run_langfuse_experiment_v2.py --quick
```

### Run Full Experiment

```bash
# All examples
poetry run python scripts/run_langfuse_experiment_v2.py --full

# Limit to 10 examples
poetry run python scripts/run_langfuse_experiment_v2.py --full --max-examples 10

# Custom experiment name
poetry run python scripts/run_langfuse_experiment_v2.py --full --experiment-name "quality-test-v1"
```

### Dry Run (preview without executing)

```bash
poetry run python scripts/run_langfuse_experiment_v2.py --full --dry-run
```

## Expected Results

After running v2 script:

1. **Langfuse UI → Datasets tab**
   - Dataset: `skillforge-golden-analysis`
   - Click on dataset to see items

2. **Langfuse UI → Datasets → Runs tab**
   - Experiment run: `g_eval_quality_v{timestamp}` or custom name
   - Each dataset item shows evaluation trace
   - Scores appear under each trace

3. **Langfuse UI → Scores tab**
   - `g_eval_overall` - Weighted average score
   - `g_eval_completeness` - Completeness criterion
   - `g_eval_accuracy` - Accuracy criterion
   - `g_eval_coherence` - Coherence criterion
   - `g_eval_depth` - Depth criterion

## Verification

To verify the experiment worked:

```python
from langfuse import Langfuse

langfuse = Langfuse()
dataset = langfuse.get_dataset("skillforge-golden-analysis")

# Check runs
runs = list(dataset.runs)
print(f"Dataset has {len(runs)} experiment runs")

# Check latest run
if runs:
    latest_run = runs[0]
    print(f"Latest run: {latest_run.name}")
    print(f"Items evaluated: {len(list(latest_run.items))}")
```

## Migration Plan

1. **Test v2 script**:
   ```bash
   poetry run python scripts/run_langfuse_experiment_v2.py --quick --dry-run
   ```

2. **Run small experiment**:
   ```bash
   poetry run python scripts/run_langfuse_experiment_v2.py --quick
   ```

3. **Verify in Langfuse UI**:
   - Check Datasets tab
   - Check Runs tab under dataset
   - Check Scores tab

4. **Once verified, replace v1**:
   ```bash
   mv scripts/run_langfuse_experiment.py scripts/run_langfuse_experiment_v1_DEPRECATED.py
   mv scripts/run_langfuse_experiment_v2.py scripts/run_langfuse_experiment.py
   ```

## References

- Langfuse Datasets: https://langfuse.com/docs/datasets/overview
- Python SDK Reference: https://langfuse.com/docs/sdk/python
- Dataset Experiments: https://langfuse.com/docs/datasets/python-decorator

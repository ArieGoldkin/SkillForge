# ExperimentRunner - CI/CD Automation for Langfuse Experiments

**Issue #428 - Phase 4.1: Langfuse-First Architecture Migration**

## Overview

The `ExperimentRunner` provides automated experiment execution for CI/CD pipelines. It orchestrates running experiments on Langfuse datasets, logging results, and collecting comprehensive statistics.

## Features

1. **Async/await pattern** - Efficient parallel execution
2. **Configurable parallelism** - Semaphore-based throttling to control concurrency
3. **Graceful error handling** - Partial failures don't stop the entire experiment
4. **Progress logging** - Structured logging with `structlog` integration
5. **Comprehensive statistics** - Success rate, average scores, throughput metrics
6. **Full Langfuse integration** - Seamless experiment tracking and result logging

## Architecture

```
User Code          ExperimentRunner        LangfuseClient       Langfuse
    |                     |                      |                 |
    | run_experiment()    |                      |                 |
    +-------------------->|                      |                 |
    |                     | get_dataset()        |                 |
    |                     +--------------------->|---------------->|
    |                     | get_dataset_items()  |                 |
    |                     +--------------------->|---------------->|
    |                     | create_experiment()  |                 |
    |                     +--------------------->|---------------->|
    |                     |                      |                 |
    |                     | (parallel execution) |                 |
    |                     | evaluator_fn()       |                 |
    |                     | evaluator_fn()       |                 |
    |                     | evaluator_fn()       |                 |
    |                     |                      |                 |
    |                     | log_experiment_run() |                 |
    |                     +--------------------->|---------------->|
    |                     |                      |                 |
    |    results          |                      |                 |
    |<--------------------+                      |                 |
```

## Quick Start

### Basic Usage

```python
from app.core.langfuse_client import get_langfuse_api_client
from app.evaluation.experiment_runner import ExperimentRunner

async def my_evaluator(item: dict) -> dict:
    """Evaluate a single dataset item."""
    # Your evaluation logic here
    result = await your_model.generate(item["input"])
    return {
        "output": result,
        "scores": {"accuracy": 0.95, "relevance": 0.88}
    }

# Initialize
client = get_langfuse_api_client()
runner = ExperimentRunner(client)

# Run experiment
summary = await runner.run_experiment(
    dataset_name="golden-dataset",
    experiment_name="v2.0-quality-test",
    evaluator_fn=my_evaluator,
    max_parallel=5,
)

# Check results
print(f"Success rate: {summary.success_rate:.1%}")
print(f"Average scores: {summary.average_scores}")
```

### With Metadata and Description

```python
summary = await runner.run_experiment(
    dataset_name="golden-dataset",
    experiment_name="production-validation",
    evaluator_fn=my_evaluator,
    max_parallel=10,
    description="Pre-deployment quality validation",
    metadata={
        "version": "2.1.0",
        "environment": "staging",
        "git_sha": "abc123",
    },
)
```

## API Reference

### ExperimentRunner

#### `__init__(langfuse_client: LangfuseClient | None)`

Initialize the runner with a Langfuse client.

**Parameters:**
- `langfuse_client`: LangfuseClient instance or None for dry-run mode

#### `run_experiment(...)` → `ExperimentSummary`

Run an experiment on a Langfuse dataset.

**Parameters:**
- `dataset_name` (str): Name of dataset in Langfuse
- `experiment_name` (str): Name for this experiment run
- `evaluator_fn` (Callable): Async function that evaluates a dataset item
- `max_parallel` (int, optional): Maximum concurrent evaluations (default: 5)
- `description` (str, optional): Experiment description
- `metadata` (dict, optional): Additional experiment metadata

**Returns:**
- `ExperimentSummary`: Comprehensive statistics about the experiment run

**Raises:**
- `LangfuseClientError`: If dataset doesn't exist or can't be accessed

**Example:**
```python
async def evaluator(item: dict) -> dict:
    return {"output": "result", "scores": {"quality": 0.9}}

summary = await runner.run_experiment(
    dataset_name="test-dataset",
    experiment_name="baseline-v1",
    evaluator_fn=evaluator,
)
```

### ExperimentSummary

Summary statistics returned from an experiment run.

**Attributes:**
- `experiment_id` (str | None): Langfuse experiment ID
- `dataset_name` (str): Dataset that was tested
- `experiment_name` (str): Name of the experiment
- `total_items` (int): Total number of dataset items
- `successful_runs` (int): Number of successful evaluations
- `failed_runs` (int): Number of failed evaluations
- `success_rate` (float): Percentage of successful runs (0.0 to 1.0)
- `average_scores` (dict[str, float]): Average scores across all runs
- `total_duration_ms` (float): Total processing time in milliseconds
- `items_per_second` (float): Processing throughput
- `errors` (list[str]): List of error messages from failed runs

### ExperimentRunResult

Result from processing a single dataset item.

**Attributes:**
- `dataset_item_id` (str): ID of the dataset item
- `success` (bool): Whether the evaluation succeeded
- `trace_id` (str): Langfuse trace ID for this run
- `duration_ms` (float): Processing duration in milliseconds
- `output` (str | dict | None): Model output (if successful)
- `scores` (dict[str, float] | None): Evaluation scores (if successful)
- `error` (str | None): Error message (if failed)

## Evaluator Function Contract

Your evaluator function must follow this contract:

```python
async def evaluator(item: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single dataset item.

    Args:
        item: Dataset item with fields like:
            - "id": str - Item identifier
            - "input": dict - Input data for evaluation
            - "expected_output": dict - Expected output (optional)
            - ... other custom fields

    Returns:
        Dict with required keys:
            - "output": str | dict - Model/system output
            - "scores": dict[str, float] (optional) - Evaluation scores

    Raises:
        Any exception will be caught and recorded as a failed run
    """
    pass
```

### Evaluator Examples

#### Simple Evaluator
```python
async def simple_evaluator(item: dict) -> dict:
    """Basic evaluator that always returns same score."""
    return {
        "output": f"Processed {item['id']}",
        "scores": {"quality": 1.0}
    }
```

#### LLM-based Evaluator
```python
async def llm_evaluator(item: dict) -> dict:
    """Evaluate using an LLM."""
    input_data = item["input"]
    expected = item.get("expected_output")

    # Generate output
    actual = await llm.generate(input_data)

    # Evaluate quality
    quality_score = await llm_as_judge.evaluate(actual, expected)

    return {
        "output": actual,
        "scores": {
            "quality": quality_score,
            "relevance": calculate_relevance(actual, expected),
        }
    }
```

#### Multi-metric Evaluator
```python
async def comprehensive_evaluator(item: dict) -> dict:
    """Evaluate multiple quality dimensions."""
    result = await process_item(item)

    return {
        "output": result,
        "scores": {
            "accuracy": calculate_accuracy(result, item["expected"]),
            "relevance": calculate_relevance(result, item["query"]),
            "completeness": check_completeness(result),
            "coherence": measure_coherence(result),
        }
    }
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Quality Validation

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily validation

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          poetry install

      - name: Run experiment
        env:
          LANGFUSE_ENABLED: true
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
          LANGFUSE_HOST: ${{ secrets.LANGFUSE_HOST }}
        run: |
          poetry run python -m app.evaluation.run_ci_experiment

      - name: Check quality thresholds
        run: |
          # Exit with error if quality is below threshold
          poetry run python -m app.evaluation.check_thresholds
```

### Example CI Script

```python
# app/evaluation/run_ci_experiment.py
import asyncio
import sys
from app.core.langfuse_client import get_langfuse_api_client
from app.evaluation.experiment_runner import ExperimentRunner

async def main():
    client = get_langfuse_api_client()
    runner = ExperimentRunner(client)

    summary = await runner.run_experiment(
        dataset_name="golden-dataset",
        experiment_name=f"ci-validation-{os.getenv('GITHUB_SHA', 'local')}",
        evaluator_fn=your_evaluator,
        max_parallel=10,
    )

    # Fail CI if quality thresholds not met
    if summary.success_rate < 0.95:
        print(f"FAIL: Success rate {summary.success_rate:.1%} < 95%")
        sys.exit(1)

    avg_quality = summary.average_scores.get("quality", 0.0)
    if avg_quality < 0.9:
        print(f"FAIL: Average quality {avg_quality:.2f} < 0.9")
        sys.exit(1)

    print("PASS: All quality thresholds met")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Tuning

### Parallelism

Control concurrency based on your environment:

```python
# Local development - conservative
summary = await runner.run_experiment(..., max_parallel=2)

# CI/CD - moderate
summary = await runner.run_experiment(..., max_parallel=5)

# Production benchmarking - aggressive
summary = await runner.run_experiment(..., max_parallel=20)
```

### Batch Size

The runner automatically handles pagination with configurable batch size (default: 100 items per page).

## Error Handling

The runner implements graceful degradation:

1. **Item failures** - Individual item failures don't stop the experiment
2. **Logging failures** - Failed logs are recorded but don't affect experiment execution
3. **Experiment creation failures** - Runner continues in dry-run mode
4. **Dataset not found** - Raises `LangfuseClientError` immediately

### Handling Partial Failures

```python
summary = await runner.run_experiment(...)

if summary.failed_runs > 0:
    print(f"⚠️  {summary.failed_runs} items failed:")
    for error in summary.errors[:5]:  # Show first 5 errors
        print(f"  - {error}")

    # Decide whether to fail CI based on failure rate
    failure_rate = summary.failed_runs / summary.total_items
    if failure_rate > 0.1:  # More than 10% failed
        print("Too many failures, marking experiment as failed")
        sys.exit(1)
```

## Testing

The module includes comprehensive unit tests:

```bash
# Run tests
poetry run pytest tests/unit/evaluation/test_experiment_runner.py -v

# Run specific test
poetry run pytest tests/unit/evaluation/test_experiment_runner.py::TestExperimentRunner::test_run_experiment_success -v

# Run with coverage
poetry run pytest tests/unit/evaluation/test_experiment_runner.py --cov=app.evaluation.experiment_runner --cov-report=html
```

## Observability

All operations are logged with structured logging:

```python
# Starting experiment
[info] experiment_starting dataset=golden-dataset experiment=v1.0 max_parallel=5

# Dataset loaded
[info] dataset_items_fetched dataset=golden-dataset total_items=100

# Processing items
[info] processing_items total_items=100 max_parallel=5

# Item processed
[debug] item_processed_successfully item_id=item-1 duration_ms=123.45 scores={'quality': 0.9}

# Experiment completed
[info] experiment_completed experiment=v1.0 total_items=100 successful=98 failed=2 success_rate=98.0% duration_ms=5432.10
```

## Common Use Cases

### 1. Regression Testing
```python
# Run before every deployment to ensure quality doesn't degrade
summary = await runner.run_experiment(
    dataset_name="regression-suite",
    experiment_name=f"regression-{version}",
    evaluator_fn=production_evaluator,
)
assert summary.success_rate >= 0.98
```

### 2. A/B Testing
```python
# Compare two model versions
summary_a = await runner.run_experiment(
    dataset_name="golden-dataset",
    experiment_name="model-a",
    evaluator_fn=model_a_evaluator,
)

summary_b = await runner.run_experiment(
    dataset_name="golden-dataset",
    experiment_name="model-b",
    evaluator_fn=model_b_evaluator,
)

# Choose winner
if summary_b.average_scores["quality"] > summary_a.average_scores["quality"]:
    print("Model B wins!")
```

### 3. Performance Benchmarking
```python
# Measure throughput improvements
summary = await runner.run_experiment(
    dataset_name="benchmark-dataset",
    experiment_name="performance-test",
    evaluator_fn=optimized_evaluator,
    max_parallel=20,
)

print(f"Throughput: {summary.items_per_second:.1f} items/sec")
print(f"Avg latency: {summary.total_duration_ms / summary.total_items:.0f}ms")
```

## Troubleshooting

### Issue: Dataset not found
```
LangfuseClientError: Dataset 'my-dataset' not found in Langfuse
```

**Solution:** Ensure dataset exists in Langfuse UI or create it programmatically.

### Issue: Low throughput
```
Throughput: 2.3 items/sec (expected: 10+ items/sec)
```

**Solutions:**
1. Increase `max_parallel` parameter
2. Optimize evaluator function to reduce async overhead
3. Check network latency to Langfuse server

### Issue: All evaluations failing
```
failed_runs=100 successful_runs=0
```

**Solutions:**
1. Check evaluator function returns correct format: `{"output": ..., "scores": {...}}`
2. Review error messages in `summary.errors`
3. Test evaluator function in isolation first

## Related Documentation

- [Langfuse API Documentation](https://langfuse.com/docs/api)
- [LangfuseClient Reference](/app/core/langfuse_client.py)
- [Example Experiment](/app/evaluation/example_experiment.py)
- [Test Suite](/tests/unit/evaluation/test_experiment_runner.py)

## Version History

- **v1.0.0** (Issue #428 Phase 4.1) - Initial implementation
  - Async parallel execution
  - Graceful error handling
  - Comprehensive statistics
  - Full Langfuse integration

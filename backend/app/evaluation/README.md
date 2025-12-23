# Evaluation Framework

Multi-provider LLM benchmarking and retrieval evaluation system for SkillForge.

## Overview

This module provides:
1. **LLM Benchmarking** - A/B testing across GPT-4o-mini, Claude Sonnet 4, Gemini Flash, and DeepSeek V3
2. **Retrieval Evaluation** - IR metrics (Recall@5, MRR, NDCG@5) with difficulty-based thresholds
3. **Quality Gates** - CI/CD integration with pass/warn/fail status
4. **Golden Datasets** - Curated examples for supervisor, agent, and synthesis tasks

## Architecture

```
evaluation/
├── __init__.py              # Public exports (LLMBenchmark)
├── llm_benchmark.py         # Multi-model benchmark runner
├── run_experiments.py       # CLI for running experiments
├── generate_config.py       # Generate optimal model config from results
│
├── evaluators/              # Metric evaluators
│   ├── correctness.py       # Task-specific correctness scoring
│   ├── quality.py           # LLM-as-judge quality evaluation
│   ├── latency.py           # Response time metrics
│   └── cost.py              # Token usage & cost tracking
│
├── pipeline/                # CI/CD evaluation pipeline
│   ├── runner.py            # EvaluationRunner - main pipeline
│   └── thresholds.py        # Difficulty-based quality thresholds
│
├── datasets/                # Golden dataset management
│   └── __init__.py          # Dataset loading utilities
│
├── ingestion/               # Dataset generation tools
│   ├── github_importer.py        # Import from GitHub issues
│   ├── pii_anonymizer.py         # PII detection and masking
│   ├── adversarial_generator.py  # Adversarial test generation
│   ├── edge_case_generator.py    # Edge case generation
│   └── cutting_edge_generator.py # Latest tech examples
│
├── validation/              # Inter-annotator agreement
│   ├── agreement.py         # Cohen's Kappa, Krippendorff's Alpha
│   ├── consensus.py         # Majority voting resolution
│   ├── manager.py           # Validation workflow orchestration
│   └── models.py            # Pydantic schemas
│
├── metrics/                 # Regression detection
│   └── regression.py        # Statistical regression detection
│
└── schemas/                 # Shared Pydantic models
    └── validation.py        # Validation schemas
```

## Quick Start

### Run LLM Benchmark

```python
from app.evaluation import LLMBenchmark

benchmark = LLMBenchmark(project_name="skillforge-eval")

# Compare models on supervisor task
comparison = await benchmark.compare_models(
    task_type="supervisor",
    model_ids=["gemini-2.5-flash", "gpt-4o-mini", "claude-sonnet-4-20250514"],
    dataset_name="golden/supervisor",
)

print(f"Winner by accuracy: {comparison.winner_by_metric['accuracy']}")
print(f"Winner by latency: {comparison.winner_by_metric['latency']}")
print(f"Winner by cost: {comparison.winner_by_metric['cost']}")
```

### Run Retrieval Evaluation (CI/CD)

```python
from app.evaluation.pipeline.runner import EvaluationRunner
from app.evaluation.pipeline.thresholds import ThresholdStatus

runner = EvaluationRunner(db_session, embedding_service)
result = await runner.run_from_fixtures(Path("tests/fixtures/eval"))

# Check if CI should pass
if result.overall_status == ThresholdStatus.FAIL:
    print(result.to_markdown())  # Detailed failure report
    sys.exit(1)
```

## Quality Thresholds

Difficulty-based thresholds for retrieval quality (5% warning margin):

| Difficulty | Recall@5 | MRR | NDCG@5 |
|------------|----------|-----|--------|
| trivial    | 95%      | 0.90 | 0.92  |
| easy       | 85%      | 0.80 | 0.82  |
| medium     | 75%      | 0.70 | 0.72  |
| hard       | 65%      | 0.60 | 0.62  |
| adversarial| 50%      | 0.45 | 0.48  |

## Benchmark Tasks

### 1. Supervisor Routing
Tests the supervisor's ability to select optimal agents for analysis.
- **Input**: Content summary, URL type
- **Output**: List of agent names to run
- **Evaluator**: Agent selection correctness

### 2. Agent Analysis
Tests individual agent structured output quality.
- **Input**: Content + analysis question
- **Output**: Structured analysis (recommendations, findings)
- **Evaluator**: LLM-as-judge quality scoring

### 3. Synthesis
Tests aggregation of multiple agent findings.
- **Input**: Multiple agent outputs
- **Output**: Executive summary, key findings, recommendations
- **Evaluator**: Coherence, coverage, conflict resolution

## Model Support

| Provider | Models | Token Tracking | Cost Estimation |
|----------|--------|----------------|-----------------|
| OpenAI   | gpt-4o-mini, gpt-4o, gpt-5-mini | tiktoken | Per-token pricing |
| Anthropic| claude-sonnet-4, claude-haiku-4.5 | Anthropic API | Per-token pricing |
| Google   | gemini-2.5-flash, gemini-3-flash | Vertex API | Per-character pricing |
| xAI      | grok-4.1-fast, grok-3 | tiktoken | Per-token pricing |
| DeepSeek | deepseek-v3 | tiktoken | Per-token pricing |

## CI/CD Integration

The evaluation pipeline integrates with GitHub Actions:

```yaml
# .github/workflows/eval.yml
- name: Run Evaluation Pipeline
  run: |
    cd backend
    poetry run python -m app.evaluation.pipeline.runner \
      --fixtures tests/fixtures/eval \
      --output eval-results.json

- name: Check Thresholds
  run: |
    if [ "$(jq -r '.overall_status' eval-results.json)" != "pass" ]; then
      echo "Evaluation failed!"
      exit 1
    fi
```

## Dataset Management

### Create Golden Dataset

Golden datasets are created from successful production runs tracked in Langfuse.
Use the evaluation pipeline to extract and curate examples:

```python
# Golden datasets are stored in evaluation/datasets/golden/
# See data/golden_dataset_backup.json for the curated dataset
from app.evaluation.datasets import load_golden_dataset

# Load existing golden dataset
dataset = load_golden_dataset("supervisor")
```

### Anonymize PII

```python
from app.evaluation.ingestion import PIIAnonymizer

anonymizer = PIIAnonymizer()
clean_examples = anonymizer.process_batch(examples)
```

### Generate Adversarial Cases

```python
from app.evaluation.ingestion import AdversarialGenerator

generator = AdversarialGenerator()
adversarial = generator.generate_for_task("supervisor", base_examples)
```

## Related Issues

- #257 - Evaluation Pipeline (main tracking issue)
- #309-339 - Multimodal evaluation (future)

## Development

```bash
# Run evaluation tests
cd backend
poetry run pytest tests/unit/evaluation/ -v

# Run benchmark experiment
poetry run python -m app.evaluation.run_experiments \
  --task supervisor \
  --models gemini-2.5-flash gpt-4o-mini \
  --dataset golden/supervisor
```

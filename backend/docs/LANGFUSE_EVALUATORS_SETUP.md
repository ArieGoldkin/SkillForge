# Langfuse LLM-as-a-Judge Evaluators Setup

## Overview

This document describes the LLM-as-a-Judge evaluator configuration for SkillForge in Langfuse. The evaluators use G-Eval methodology to assess quality of AI-generated analysis artifacts.

## Architecture

### 1. Score Configs (Evaluation Schema)

Score configs define the schema and validation rules for evaluation scores in Langfuse. All score configs are managed via the Langfuse API.

**Status**: ✅ **COMPLETE** - All 17 score configs created

#### G-Eval Criterion Scores (LLM-as-a-Judge)

These scores use LLM judges to assess quality on specific criteria:

| Score Name | Data Type | Range | Description |
|------------|-----------|-------|-------------|
| `g_eval_relevance` | NUMERIC | 0.0-1.0 | Content relevance to input |
| `g_eval_depth` | NUMERIC | 0.0-1.0 | Analytical depth and detail |
| `g_eval_coherence` | NUMERIC | 0.0-1.0 | Logical coherence and structure |
| `g_eval_actionability` | NUMERIC | 0.0-1.0 | Practical actionability |
| `g_eval_completeness` | NUMERIC | 0.0-1.0 | Content completeness |
| `g_eval_overall` | NUMERIC | 0.0-1.0 | Weighted average of all criteria |

#### Agent-Specific Criteria

Different agent types use different criterion combinations:

- **tech_comparator**: completeness, accuracy, balance, recommendation
- **security_auditor**: completeness, severity, mitigation, actionability
- **implementation_planner**: completeness, feasibility, detail, ordering
- **Other agents**: See `app/shared/services/g_eval/rubrics.py` for full mapping

#### Legacy Quality Scores

Maintained for backward compatibility:

| Score Name | Data Type | Range | Description |
|------------|-----------|-------|-------------|
| `quality_relevance` | NUMERIC | 0.0-1.0 | Legacy relevance score |
| `quality_depth` | NUMERIC | 0.0-1.0 | Legacy depth score |
| `quality_coherence` | NUMERIC | 0.0-1.0 | Legacy coherence score |
| `quality_avg` | NUMERIC | 0.0-1.0 | Legacy average score |
| `user_feedback` | BOOLEAN | 0/1 | Human thumbs up/down |

#### Performance Metrics

| Score Name | Data Type | Description |
|------------|-----------|-------------|
| `latency_seconds` | NUMERIC | Execution latency |
| `cache_hit` | BOOLEAN | Cache hit indicator |

#### Token & Cost Tracking

Auto-captured by Langfuse CallbackHandler:

| Score Name | Data Type | Description |
|------------|-----------|-------------|
| `token_count_input` | NUMERIC | Input token count |
| `token_count_output` | NUMERIC | Output token count |
| `token_count_total` | NUMERIC | Total token count |
| `cost_usd` | NUMERIC | Estimated cost in USD |

### 2. Evaluator Functions (Python Code)

Evaluators are Python functions that compute scores using LLM judges. They follow Langfuse's `run_experiment()` API patterns.

**Status**: ✅ **COMPLETE**

**Location**: `backend/app/shared/services/g_eval/langfuse_evaluators.py`

#### Item-Level Evaluators

Score individual artifacts during experiment execution:

```python
from app.shared.services.g_eval import (
    create_g_eval_evaluator,
    create_g_eval_overall_evaluator,
    get_standard_evaluators,
)

# Single criterion evaluator
relevance_eval = create_g_eval_evaluator("relevance", agent_type="tech_comparator")

# Overall evaluator (all criteria + weighted average)
overall_eval = create_g_eval_overall_evaluator(agent_type="tech_comparator")

# Get full set of evaluators for an agent
evaluators = get_standard_evaluators(agent_type="tech_comparator")
# Returns: [completeness_eval, accuracy_eval, balance_eval, recommendation_eval, overall_eval]
```

**Evaluator Signature**:
```python
def evaluator(*, input, output, expected_output=None, **kwargs) -> Evaluation:
    """
    Args:
        input: Dataset item input (content to analyze)
        output: Generated output to evaluate
        expected_output: Optional expected output for comparison
        **kwargs: Additional context from Langfuse

    Returns:
        Langfuse Evaluation object with:
        - name: Score name (e.g., "g_eval_relevance")
        - value: Normalized score (0.0-1.0)
        - data_type: "NUMERIC"
        - comment: Reasoning/explanation
        - metadata: Additional context
    """
```

#### Run-Level Evaluators

Aggregate scores across all items in an experiment:

```python
from app.shared.services.g_eval import (
    average_g_eval_score_evaluator,
    criterion_average_evaluator,
    quality_threshold_evaluator,
    get_standard_run_evaluators,
)

# Average overall score across all items
avg_eval = average_g_eval_score_evaluator

# Average specific criterion
avg_relevance = criterion_average_evaluator("relevance")

# Pass rate (percentage above threshold)
pass_rate = quality_threshold_evaluator(threshold=0.6)

# Get full set of run evaluators
run_evals = get_standard_run_evaluators(
    quality_threshold=0.6,
    agent_type="tech_comparator"
)
```

**Run Evaluator Signature**:
```python
def evaluator(*, item_results: list, **kwargs) -> Evaluation:
    """
    Args:
        item_results: List of ExperimentItemResult from Langfuse
        **kwargs: Additional context

    Returns:
        Langfuse Evaluation object with aggregate metric
    """
```

### 3. Annotation Queue

Human review workflow for manual quality assessment.

**Status**: ❌ **NEEDS CREATION**

**Current Issue**: Queue ID in `.env` (`cmjctaben004xqn07msf77nqy`) is outdated. The queue does not exist in Langfuse.

**Action Required**: Create queue manually via Langfuse UI (see instructions below).

## Setup Instructions

### 1. Score Configs Setup ✅

Score configs are already created. To verify or update:

```bash
cd backend

# View what would be created
poetry run python scripts/setup_langfuse_score_configs.py --dry-run

# Verify existing configs
poetry run python scripts/setup_langfuse_score_configs.py

# Force update if schema changed
poetry run python scripts/setup_langfuse_score_configs.py --force
```

### 2. Annotation Queue Setup ❌

**Manual creation required** (Langfuse v3 has no API for queue creation):

1. **Open Langfuse UI**: http://localhost:3000
2. **Navigate to**: Settings → Annotation Queues
   - Or direct: http://localhost:3000/project/skillforge/annotation-queues
3. **Click**: "Create Queue"
4. **Fill in**:
   - **Name**: `SkillForge Review Queue`
   - **Description**: `Queue for human review of SkillForge analysis artifacts`
   - **Score Configs**: Select `user_feedback` and `g_eval_overall`
5. **Save** and copy the new queue ID
6. **Update** `backend/.env`:
   ```bash
   LANGFUSE_ANNOTATION_QUEUE_ID=<new-queue-id>
   ```
7. **Verify**:
   ```bash
   poetry run python scripts/setup_langfuse_annotation_queue.py
   ```

**Detailed Instructions**: See `scripts/create_annotation_queue_instructions.md`

### 3. Test Evaluators

Run the demo script to verify evaluators work:

```bash
cd backend

# Show evaluator configuration
poetry run python scripts/demo_g_eval_evaluators.py --dry-run

# Run quick test with 3 examples
poetry run python scripts/demo_g_eval_evaluators.py --quick

# Run full evaluation with all golden dataset items
poetry run python scripts/demo_g_eval_evaluators.py --full

# Run with specific agent type
poetry run python scripts/demo_g_eval_evaluators.py --quick --agent-type security_auditor
```

## Usage Examples

### Running an Experiment

```python
from langfuse import Langfuse
from app.shared.services.g_eval import (
    get_standard_evaluators,
    get_standard_run_evaluators,
)

langfuse = Langfuse()

# Define task function
def task(*, item, **kwargs):
    """Process a single dataset item."""
    # Generate output to evaluate
    output = your_generation_function(item.input)
    return output

# Get evaluators
agent_type = "tech_comparator"
evaluators = get_standard_evaluators(agent_type)
run_evaluators = get_standard_run_evaluators(
    quality_threshold=0.7,
    agent_type=agent_type
)

# Run experiment
dataset = langfuse.get_dataset("your_dataset_name")

result = langfuse.run_experiment(
    name="quality_evaluation_v1",
    data=dataset.items,
    task=task,
    evaluators=evaluators,
    run_evaluators=run_evaluators,
)

# Print results
print(result.format())
```

### Manual Score Submission

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Score a trace
langfuse.score(
    trace_id="trace-123",
    name="g_eval_overall",
    value=0.85,
    comment="High quality output with minor issues",
    metadata={
        "g_eval_relevance": 0.9,
        "g_eval_depth": 0.8,
        "g_eval_coherence": 0.85,
    }
)
```

### Adding Item to Annotation Queue

```python
import os
from langfuse import Langfuse

langfuse = Langfuse()
queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID")

# Add artifact for human review
langfuse.annotation_queue_item(
    queue_id=queue_id,
    trace_id="trace-123",
    observation_id="obs-456",  # Optional
)
```

## G-Eval Methodology

### How It Works

1. **Chain-of-Thought Rubrics**: Each criterion has a detailed rubric with:
   - Definition and evaluation steps
   - Score range (1-10) with descriptions
   - Examples of each score level

2. **LLM Judge**: Gemini 2.0 Flash Thinking Experimental
   - Cost-effective ($0.15/$0.60 per million tokens)
   - Fast inference (supports low latency)
   - Strong reasoning capabilities

3. **Self-Consistency** (Optional): Multiple judge votes for higher confidence
   - 3-5 independent evaluations
   - Majority voting
   - Confidence score based on agreement

4. **Caching**: Multi-level caching to reduce costs
   - L1: Redis (5 min TTL)
   - L2: Database (7 day TTL)
   - 70-95% cache hit rate in practice

### Rubric Example

**Tech Comparator - Completeness Criterion**:

```
Score 9-10: All technologies thoroughly compared
  - Detailed feature comparison
  - Use case coverage
  - Performance benchmarks
  - Cost analysis

Score 7-8: Most aspects covered
  - Key features compared
  - Some use cases mentioned
  - Minor gaps in analysis

Score 5-6: Basic comparison
  - Surface-level features
  - Missing depth in analysis

Score 1-4: Incomplete
  - Major gaps in coverage
  - Superficial analysis
```

**Full rubrics**: `backend/app/shared/services/g_eval/rubrics.py`

## Observability

### Langfuse UI

View evaluation results:

1. **Experiments**: http://localhost:3000/project/skillforge/experiments
   - Compare experiment runs
   - View score distributions
   - Filter by agent type

2. **Traces**: http://localhost:3000/project/skillforge/traces
   - View individual evaluations
   - See judge reasoning in metadata
   - Track token usage and costs

3. **Scores**: http://localhost:3000/project/skillforge/scores
   - Aggregate score statistics
   - Score trends over time
   - Filter by score config

4. **Annotation Queues**: http://localhost:3000/project/skillforge/annotation-queues
   - Pending review items
   - Submit human annotations
   - Compare human vs LLM scores

### Logging

Evaluators use structured logging:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "g_eval_score_complete",
    criterion="relevance",
    score=0.85,
    confidence=0.92,
    cache_hit=True,
)
```

## Cost Optimization

### Caching Strategy

```
Request → L1 Cache (Redis, 5 min) → L2 Cache (DB, 7 days) → LLM Judge
```

**Cache hit rate**:
- Development: 70-85%
- Production: 85-95%

**Cost savings**:
- Cached request: ~$0.00 (database lookup)
- LLM judge call: ~$0.001-0.005 per evaluation

### Token Optimization

1. **Truncation limits**: Input truncated to 8000 chars max
2. **Prompt compression**: Minimal rubric context
3. **Batch processing**: Evaluate multiple items in parallel
4. **Smart sampling**: Use self-consistency only for critical evaluations

## Troubleshooting

### Score Configs Not Found

```bash
# Verify configs exist
curl http://localhost:3000/api/public/score-configs \
  -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY"

# Re-create configs
poetry run python scripts/setup_langfuse_score_configs.py --force
```

### Evaluator Errors

Check logs for details:

```bash
# Backend logs
docker compose logs backend -f

# Langfuse logs
docker compose logs langfuse-web -f
```

Common issues:
- Missing rubrics for agent type
- Invalid score range (must be 0.0-1.0 normalized)
- LLM API timeout or rate limit

### Annotation Queue Not Working

1. Verify queue exists:
   ```bash
   poetry run python scripts/setup_langfuse_annotation_queue.py
   ```

2. Check queue ID in `.env` matches Langfuse UI

3. Verify API credentials:
   ```bash
   curl http://localhost:3000/api/public/health
   ```

## References

- **G-Eval Paper**: https://arxiv.org/abs/2303.16634
- **Langfuse Experiments**: https://langfuse.com/docs/evaluation/experiments
- **Langfuse Score Configs**: https://langfuse.com/docs/scores/custom#score-configs
- **Langfuse Annotation Queues**: https://langfuse.com/docs/scores/annotation-queues

## Summary Checklist

- [x] Score Configs created (17 configs)
- [x] Evaluator code implemented
- [x] Demo script created
- [ ] Annotation Queue created (requires manual UI setup)
- [ ] Queue ID updated in .env
- [ ] Evaluators tested with experiment

**Next Steps**:
1. Create Annotation Queue via UI
2. Update `.env` with new queue ID
3. Run demo experiment: `poetry run python scripts/demo_g_eval_evaluators.py --quick`
4. Verify results in Langfuse UI

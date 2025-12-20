# Multi-Provider LLM Strategy: Evaluation-Driven Model Selection

**Date:** December 9, 2025
**Branch:** `feature/221-hierarchical-chunking`
**Related Issues:** #219 (Eval harness), #221 (Hierarchical chunking)
**Approach:** Data-driven model selection via systematic benchmarking

---

## Executive Summary

Instead of guessing which model is "best" for each task, we will:
1. **Build golden datasets** for each task type (supervisor, analysis, synthesis)
2. **Run A/B experiments** across multiple providers using Langfuse
3. **Measure quality, latency, and cost** with automated evaluators
4. **Select winners** based on actual performance data
5. **Auto-configure** the system with winning models per task

---

## 1. Latest Models (December 2025)

### Pricing Table (per 1M tokens)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    DECEMBER 2025 LLM PRICING (SOURCE: IntuitionLabs)          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  PROVIDER    │ MODEL              │ INPUT   │ OUTPUT  │ NOTES                ║
║  ────────────┼────────────────────┼─────────┼─────────┼──────────────────────║
║  OpenAI      │ GPT-5              │ $1.25   │ $10.00  │ Flagship, agents     ║
║              │ GPT-5 mini         │ $0.25   │ $2.00   │ Balanced             ║
║              │ GPT-5 nano         │ $0.05   │ $0.40   │ Simple tasks         ║
║              │ GPT-4.1            │ $3.00   │ $12.00  │ Fine-tuning base     ║
║              │ GPT-4o             │ $5.00   │ $20.00  │ Vision/multimodal    ║
║              │ GPT-4o mini        │ $0.60   │ $2.40   │ Lite multimodal      ║
║  ────────────┼────────────────────┼─────────┼─────────┼──────────────────────║
║  Anthropic   │ Claude Opus 4.1    │ $15.00  │ $75.00  │ Top reasoning        ║
║              │ Claude Sonnet 4.5  │ $3.00   │ $15.00  │ Coding/agents ⭐     ║
║              │ Claude Haiku 4.5   │ ~$0.25  │ ~$1.25  │ Fast throughput      ║
║  ────────────┼────────────────────┼─────────┼─────────┼──────────────────────║
║  Google      │ Gemini 3 Pro       │ $2.50   │ $15.00  │ GPQA leader (86.4%)  ║
║              │ Gemini 2.5 Pro     │ $1.25   │ $10.00  │ Multi-modal, 1M ctx  ║
║              │ Gemini 2.5 Flash   │ $0.15   │ $0.60   │ Fast, cheap ⭐       ║
║  ────────────┼────────────────────┼─────────┼─────────┼──────────────────────║
║  xAI         │ Grok 3             │ $3.00   │ $15.00  │ Reasoning            ║
║              │ Grok 3 Fast        │ $5.00   │ $25.00  │ Low latency          ║
║              │ Grok 3 Mini        │ $0.30   │ $0.50   │ Lightweight          ║
║  ────────────┼────────────────────┼─────────┼─────────┼──────────────────────║
║  DeepSeek    │ V3.2-Exp           │ $0.28   │ $0.42   │ 90% cheaper! 🔥      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Key Insights from Benchmarks

| Benchmark | Leader | Score | Runner-up |
|-----------|--------|-------|-----------|
| **GPQA (Reasoning)** | Gemini 3 Pro | 86.4% | GPT-5 |
| **SWE-bench (Coding)** | Claude Sonnet 4.5 | 72.5% | GPT-4.1 |
| **MMLU (General)** | GPT-5 | ~90% | Claude Opus 4.1 |
| **Cost Efficiency** | DeepSeek V3.2 | 90% cheaper | Gemini Flash |

**But these are GENERAL benchmarks - we need to test on OUR tasks!**

---

## 2. Evaluation Framework Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM EVALUATION FRAMEWORK ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     GOLDEN DATASETS (Langfuse)                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│       │                                                                     │
│       ├─▶ supervisor-golden-v1 (50 examples)                               │
│       │     • Input: content samples (articles, videos, repos)             │
│       │     • Expected: correct agent selection                            │
│       │     • Metadata: content_type, complexity, expected_agents          │
│       │                                                                     │
│       ├─▶ agent-analysis-golden-v1 (30 examples per agent type)            │
│       │     • Input: content for specific analysis                         │
│       │     • Expected: quality findings (human-labeled)                   │
│       │     • Metadata: agent_type, key_insights_expected                  │
│       │                                                                     │
│       └─▶ synthesis-golden-v1 (20 examples)                                │
│             • Input: multi-agent findings                                  │
│             • Expected: coherent synthesis                                 │
│             • Metadata: quality_criteria, key_points                       │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     BENCHMARK RUNNER                                   │ │
│  │                     backend/app/evaluation/llm_benchmark.py            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│       │                                                                     │
│       ├─▶ run_benchmark(task_type, models, dataset)                        │
│       │     ├─▶ For each model in models:                                  │
│       │     │     ├─▶ Run task with model                                  │
│       │     │     ├─▶ Collect outputs                                      │
│       │     │     ├─▶ Run evaluators                                       │
│       │     │     └─▶ Record to Langfuse experiment                       │
│       │     └─▶ Compare results across models                              │
│       │                                                                     │
│       └─▶ Models to test:                                                  │
│             • gemini-2.5-flash (fast, cheap)                               │
│             • gpt-5-mini (balanced)                                        │
│             • claude-haiku-4.5 (fast quality)                              │
│             • grok-3-mini (alternative)                                    │
│             • deepseek-v3.2 (cost leader)                                  │
│             • claude-sonnet-4.5 (quality leader)                           │
│             • gpt-5 (premium)                                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     EVALUATORS                                         │ │
│  │                     backend/app/evaluation/evaluators/                 │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│       │                                                                     │
│       ├─▶ correctness_evaluator.py                                         │
│       │     • Supervisor: Did it select the right agents?                  │
│       │     • Agent: Are key insights present?                             │
│       │     • Synthesis: Are all findings integrated?                      │
│       │                                                                     │
│       ├─▶ quality_evaluator.py (LLM-as-Judge)                             │
│       │     • Uses Claude Opus 4.1 as judge                                │
│       │     • Scores: relevance, depth, accuracy, coherence                │
│       │     • Returns 0.0-1.0 quality score                                │
│       │                                                                     │
│       ├─▶ latency_evaluator.py                                            │
│       │     • Measures time-to-first-token                                 │
│       │     • Measures total response time                                 │
│       │     • Buckets: fast (<2s), medium (2-5s), slow (>5s)              │
│       │                                                                     │
│       └─▶ cost_evaluator.py                                               │
│             • Counts input/output tokens                                   │
│             • Calculates cost using model pricing                          │
│             • Tracks cost per task type                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                     RESULTS & CONFIG GENERATION                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│       │                                                                     │
│       ├─▶ Store experiments in Langfuse                                   │
│       │                                                                     │
│       ├─▶ Generate comparison report (Markdown)                            │
│       │     • Table: Model × Task × Metrics                                │
│       │     • Recommendations per task                                     │
│       │     • Cost analysis                                                │
│       │                                                                     │
│       └─▶ Generate model_config.json                                       │
│             {                                                               │
│               "supervisor": "gemini-2.5-flash",  // Winner                 │
│               "agent_analysis": "gpt-5-mini",    // Winner                 │
│               "synthesis": "claude-sonnet-4.5",  // Winner                 │
│               "fallback_chain": {                                          │
│                 "gemini-2.5-flash": ["gpt-5-mini", "grok-3-mini"],        │
│                 "claude-sonnet-4.5": ["gpt-5", "gemini-3-pro"]            │
│               }                                                            │
│             }                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Plan

### Phase 1: Model Registry Update (Day 1, Morning)

**File:** `backend/app/core/model_registry.py` (NEW)

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ModelInfo:
    provider: str
    model_id: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    context_window: int
    latency_tier: Literal["fast", "medium", "slow"]
    capabilities: list[str]
    api_key_field: str

MODEL_REGISTRY: dict[str, ModelInfo] = {
    # OpenAI
    "gpt-5": ModelInfo(
        provider="openai", model_id="gpt-5",
        input_cost_per_1m=1.25, output_cost_per_1m=10.00,
        context_window=128_000, latency_tier="medium",
        capabilities=["reasoning", "coding", "agents"],
        api_key_field="OPENAI_API_KEY"
    ),
    "gpt-5-mini": ModelInfo(
        provider="openai", model_id="gpt-5-mini",
        input_cost_per_1m=0.25, output_cost_per_1m=2.00,
        context_window=128_000, latency_tier="fast",
        capabilities=["balanced", "coding"],
        api_key_field="OPENAI_API_KEY"
    ),
    # ... (all models from pricing table)
}
```

### Phase 2: Golden Datasets (Day 1, Afternoon)

**Location:** `backend/app/evaluation/datasets/`

**Supervisor Dataset (50 examples):**
```python
# Example structure
{
    "inputs": {
        "content": "React vs Vue comparison article...",
        "content_type": "article"
    },
    "outputs": {
        "expected_agents": ["tech_comparator", "implementation_planner"],
        "reasoning": "Article compares frameworks, needs comparison and planning"
    },
    "metadata": {
        "complexity": "medium",
        "content_length": 5000
    }
}
```

**Agent Analysis Dataset (30 per agent, 240 total):**
```python
{
    "inputs": {
        "content": "Security vulnerability in JWT handling...",
        "agent_type": "security_auditor"
    },
    "outputs": {
        "key_findings": ["JWT expiry not validated", "No rate limiting"],
        "severity": "high",
        "recommendations": ["Add expiry check", "Implement rate limiting"]
    }
}
```

**Synthesis Dataset (20 examples):**
```python
{
    "inputs": {
        "agent_findings": [
            {"agent": "security_auditor", "findings": {...}},
            {"agent": "tech_comparator", "findings": {...}}
        ]
    },
    "outputs": {
        "executive_summary": "The analyzed content shows...",
        "key_points": ["Point 1", "Point 2"],
        "coherence_criteria": "All agent findings integrated"
    }
}
```

### Phase 3: Benchmark Runner (Day 2, Morning)

**File:** `backend/app/evaluation/llm_benchmark.py`

```python
from langfuse import Client
from app.core.model_registry import MODEL_REGISTRY
from app.core.model_factory import get_chat_model

class LLMBenchmark:
    def __init__(self, task_type: str, dataset_name: str):
        self.task_type = task_type
        self.dataset_name = dataset_name
        self.client = Client()

    async def run_experiment(
        self,
        models: list[str],
        evaluators: list[Callable]
    ) -> dict[str, ExperimentResults]:
        """Run A/B experiment across multiple models."""
        results = {}

        for model_name in models:
            # Create experiment in Langfuse
            experiment_name = f"{self.task_type}-{model_name}-{datetime.now().isoformat()}"

            # Run evaluation
            experiment_results = await self.client.aevaluate(
                target=lambda inputs: self._run_task(inputs, model_name),
                data=self.dataset_name,
                evaluators=evaluators,
                experiment_prefix=experiment_name,
            )

            results[model_name] = experiment_results

        return results

    def compare_results(self, results: dict) -> ModelComparison:
        """Compare results and determine winner."""
        # Score = quality * 0.5 + (1 / latency_normalized) * 0.3 + (1 / cost_normalized) * 0.2
        ...
```

### Phase 4: Evaluators (Day 2, Afternoon)

**File:** `backend/app/evaluation/evaluators/correctness.py`

```python
def supervisor_correctness_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict
) -> dict:
    """Evaluate if supervisor selected correct agents."""
    expected = set(reference_outputs["expected_agents"])
    actual = set(outputs.get("agents", []))

    precision = len(expected & actual) / len(actual) if actual else 0
    recall = len(expected & actual) / len(expected) if expected else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    return {
        "key": "correctness",
        "score": f1,
        "comment": f"Precision: {precision:.2f}, Recall: {recall:.2f}"
    }
```

**File:** `backend/app/evaluation/evaluators/quality.py`

```python
from openevals.llm import create_llm_as_judge

QUALITY_PROMPT = '''
You are evaluating the quality of an LLM's output for a {task_type} task.

Input: {inputs}
Output: {outputs}
Reference: {reference_outputs}

Score the output on:
1. Relevance (0-1): Does it address the task?
2. Depth (0-1): Is the analysis thorough?
3. Accuracy (0-1): Are the claims correct?
4. Coherence (0-1): Is it well-structured?

Return average score (0-1).
'''

quality_evaluator = create_llm_as_judge(
    prompt=QUALITY_PROMPT,
    feedback_key="quality",
    model="anthropic:claude-opus-4.1",  # Use best model as judge
    continuous=True,
)
```

### Phase 5: Integration & Config Generation (Day 3)

**File:** `backend/app/evaluation/config_generator.py`

```python
def generate_model_config(experiment_results: dict) -> dict:
    """Generate optimal model config from experiment results."""
    config = {}

    for task_type, models in experiment_results.items():
        # Sort by composite score
        ranked = sorted(
            models.items(),
            key=lambda x: x[1]["composite_score"],
            reverse=True
        )

        config[task_type] = {
            "primary": ranked[0][0],
            "fallbacks": [m[0] for m in ranked[1:3]],
            "scores": {m[0]: m[1]["composite_score"] for m in ranked}
        }

    return config
```

**Generated Config Example:**
```json
{
  "task_models": {
    "supervisor": {
      "primary": "gemini-2.5-flash",
      "fallbacks": ["gpt-5-mini", "grok-3-mini"],
      "scores": {
        "gemini-2.5-flash": 0.91,
        "gpt-5-mini": 0.88,
        "grok-3-mini": 0.84
      }
    },
    "agent_analysis": {
      "primary": "gpt-5-mini",
      "fallbacks": ["claude-haiku-4.5", "gemini-2.5-flash"],
      "scores": {...}
    },
    "synthesis": {
      "primary": "claude-sonnet-4.5",
      "fallbacks": ["gpt-5", "gemini-3-pro"],
      "scores": {...}
    }
  },
  "experiment_metadata": {
    "run_date": "2025-12-09",
    "dataset_versions": {
      "supervisor": "v1",
      "agent_analysis": "v1",
      "synthesis": "v1"
    },
    "total_examples": 310
  }
}
```

---

## 4. File Structure

```
backend/app/evaluation/                    # NEW DIRECTORY
├── __init__.py
├── llm_benchmark.py                       # Main benchmark runner
├── config_generator.py                    # Generate model config from results
├── datasets/
│   ├── __init__.py
│   ├── supervisor_golden_v1.json          # 50 examples
│   ├── agent_analysis_golden_v1.json      # 240 examples (30 × 8 agents)
│   └── synthesis_golden_v1.json           # 20 examples
├── evaluators/
│   ├── __init__.py
│   ├── correctness.py                     # Task-specific correctness
│   ├── quality.py                         # LLM-as-judge quality
│   ├── latency.py                         # Timing metrics
│   └── cost.py                            # Token/cost tracking
└── results/
    └── .gitkeep                           # Experiment results stored here

backend/app/core/
├── model_registry.py                      # NEW: Model metadata
└── model_factory.py                       # UPDATED: Task-aware routing

backend/scripts/
└── run_llm_benchmark.py                   # CLI to run benchmarks

docs/evaluation/
└── LLM_MODEL_COMPARISON.md                # Generated comparison report
```

---

## 5. Sprint 8 Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ISSUE #219 SCOPE EXPANSION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ORIGINAL SCOPE (Embeddings Only):                                         │
│  ├─▶ Recall@k/MRR for search quality                                       │
│  ├─▶ A/B: text-embedding-3-small vs -3-large                               │
│  └─▶ Labeled eval set with queries + relevant chunk ids                    │
│                                                                             │
│  EXPANDED SCOPE (Add LLM Evaluation):                                       │
│  ├─▶ LLM Task Benchmarking                                                 │
│  │     ├─▶ Supervisor correctness                                          │
│  │     ├─▶ Agent finding quality                                           │
│  │     └─▶ Synthesis coherence                                             │
│  │                                                                          │
│  ├─▶ Model A/B Testing                                                      │
│  │     ├─▶ 7 models across 4 providers                                     │
│  │     ├─▶ Track: latency, cost, quality                                   │
│  │     └─▶ Store in Langfuse experiments                                  │
│  │                                                                          │
│  └─▶ Auto-Configuration                                                     │
│        ├─▶ Generate optimal model config                                   │
│        └─▶ Fallback chains based on results                                │
│                                                                             │
│  SHARED INFRASTRUCTURE:                                                     │
│  ├─▶ Langfuse datasets (already have 3)                                   │
│  ├─▶ Langfuse experiments                                                 │
│  └─▶ Evaluator patterns (openevals compatible)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Dataset Coverage** | 310+ examples | Count examples in golden datasets |
| **Model Coverage** | 7+ models tested | Benchmark all target models |
| **Experiment Reproducibility** | 100% | Same config → same ranking |
| **Quality Improvement** | Measurable | Before/after comparison |
| **Cost Visibility** | Per-task breakdown | Track in experiment metadata |

---

## 7. Timeline

| Day | Focus | Deliverables |
|-----|-------|--------------|
| **Day 1 AM** | Model Registry | `model_registry.py` with Dec 2025 models |
| **Day 1 PM** | Golden Datasets | 50 supervisor, 30 agent examples |
| **Day 2 AM** | Benchmark Runner | `llm_benchmark.py` with Langfuse integration |
| **Day 2 PM** | Evaluators | correctness, quality, latency, cost evaluators |
| **Day 3 AM** | Run Experiments | Full A/B test across all models |
| **Day 3 PM** | Results & Config | Comparison report, `model_config.json` |

---

## 8. Questions Answered

**Q: How do we know which model should be for which task?**
A: Run A/B experiments with golden datasets and measure quality/latency/cost.

**Q: How do we evaluate it?**
A: Four evaluators: correctness (exact match), quality (LLM-as-judge), latency, cost.

**Q: Where is the best model for each job?**
A: Generated in `model_config.json` based on experiment results.

**Q: How do we test it?**
A: Langfuse experiments with reproducible datasets.

**Q: Which is better, who is doing the best job?**
A: Composite score = quality×0.5 + speed×0.3 + cost×0.2 → ranked comparison.

---

**Ready to implement?** This plan provides:
- ✅ Data-driven model selection (not guessing)
- ✅ Latest December 2025 models and pricing
- ✅ Langfuse integration for experiments
- ✅ Connects to Issue #219 (eval harness)
- ✅ Automated config generation from results
- ✅ Fallback chains based on actual performance

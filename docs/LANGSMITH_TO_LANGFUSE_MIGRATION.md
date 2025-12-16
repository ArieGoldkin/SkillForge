# 🔄 LangSmith → Langfuse Migration Analysis
**Date:** December 16, 2025  
**Status:** Assessment & Planning

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║          🔍 LANGSMITH USAGE AUDIT & LANGFUSE MIGRATION ROADMAP                ║
║                                                                              ║
║                    SkillForge Codebase Analysis                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 📊 Executive Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  DIFFICULTY ASSESSMENT: ⚠️  MODERATE (6/10)                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Complexity Factors:                                                  │  │
│  │  • 437+ usage points (decorators, get_current_run_tree)             │  │
│  │  • Custom robust_traceable wrapper                                  │  │
│  │  • Generator filtering workaround                                    │  │
│  │  • Evaluation dataset extraction from traces                         │  │
│  │  • Metrics service integration                                       │  │
│  │  • Test suite with 100+ mocked LangSmith calls                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Estimated Effort: 3-5 days                                                │
│  Risk Level: Medium                                                        │
│  Breaking Changes: Low (API compatible)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ LangSmith Usage Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  📍 USAGE LOCATIONS (1348+ matches found)                                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  1. CORE TRACING INFRASTRUCTURE                                     │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ backend/app/core/tracing.py                                │  │  │
│  │     │   • robust_traceable() decorator wrapper                   │  │  │
│  │     │   • Wraps langsmith.traceable                              │  │  │
│  │     │   • Used in 50+ workflow nodes                             │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  2. LANGGRAPH NODE INSTRUMENTATION (50+ nodes)                      │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/nodes/agents/                  │  │  │
│  │     │   • tech_comparator_node.py                                │  │  │
│  │     │   • security_auditor_node.py                               │  │  │
│  │     │   • performance_analyst_node.py                             │  │  │
│  │     │   • dependency_mapper_node.py                              │  │  │
│  │     │   • trend_validator_node.py                                │  │  │
│  │     │   • integration_feasibility_node.py                         │  │  │
│  │     │   • code_quality_critic_node.py                            │  │  │
│  │     │   • implementation_planner_node.py                         │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  3. TUTOR WORKFLOW NODES (8 nodes)                                 │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/tutor/workflows/nodes/                             │  │  │
│  │     │   • ask_socratic.py                                        │  │  │
│  │     │   • assess_readiness.py                                    │  │  │
│  │     │   • conduct_review.py                                      │  │  │
│  │     │   • deliver_lesson.py                                      │  │  │
│  │     │   • final_challenge.py                                     │  │  │
│  │     │   • generate_syllabus.py                                   │  │  │
│  │     │   • guide_reflection.py                                    │  │  │
│  │     │   • rephrase_explain.py                                    │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  4. AGENT INVOCATION & STREAMING                                   │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/agents/                        │  │  │
│  │     │   • invocation.py (get_current_run_tree)                  │  │  │
│  │     │   • streaming.py (get_current_run_tree)                   │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  5. QUALITY GATE NODE                                               │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ domains/analysis/workflows/nodes/quality_gate_node.py     │  │  │
│  │     │   • Uses langsmith.schemas.Example, Run                   │  │  │
│  │     │   • get_current_run_tree() for metadata                   │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  6. EVALUATION SYSTEM                                               │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ evaluation/ingestion/langsmith_extractor.py                 │  │  │
│  │     │   • LangSmithExtractor class                               │  │  │
│  │     │   • Extracts traces → evaluation datasets                  │  │  │
│  │     │   • Client() for querying traces                          │  │  │
│  │     │                                                             │  │  │
│  │     │ evaluation/evaluators/                                     │  │  │
│  │     │   • quality.py (uses Run, Example schemas)                 │  │  │
│  │     │   • cost.py (uses Run, Example schemas)                   │  │  │
│  │     │   • correctness.py (uses Run, Example schemas)            │  │  │
│  │     │   • latency.py (uses Run, Example schemas)                 │  │  │
│  │     │                                                             │  │  │
│  │     │ evaluation/llm_benchmark.py                                 │  │  │
│  │     │   • Client() for metrics extraction                       │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  7. METRICS SERVICE                                                 │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ services/metrics/langsmith.py                             │  │  │
│  │     │   • LangSmithMetricsService                               │  │  │
│  │     │   • Client() for querying experiment metrics              │  │  │
│  │     │   • get_agent_metrics(), get_workflow_metrics()            │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  8. CONFIGURATION & CLIENT SETUP                                    │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ core/langsmith_config.py                                  │  │  │
│  │     │   • get_langsmith_client()                                │  │  │
│  │     │   • Generator filtering workaround                        │  │  │
│  │     │   • hide_inputs/hide_outputs filters                     │  │  │
│  │     │                                                             │  │  │
│  │     │ main.py                                                   │  │  │
│  │     │   • Client() initialization check                         │  │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  9. TEST SUITE (100+ test files)                                   │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ tests/unit/core/test_tracing.py                           │  │  │
│  │     │ tests/unit/services/test_langsmith_metrics.py             │  │
│  │     │ tests/unit/evaluation/test_langsmith_extractor.py        │  │
│  │     │ tests/unit/workflows/nodes/test_quality_gate_node.py      │  │
│  │     │ tests/unit/workflows/agents/test_invocation.py            │  │
│  │     │ tests/conftest.py (LANGSMITH_TRACING=false)               │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Migration Architecture Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  LANGSMITH (Current)                    LANGFUSE (Target)                  │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ @traceable          │              │ @observe            │            │
│  │ (langsmith)         │    ────>     │ (langfuse)          │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ get_current_run_   │              │ get_client()        │            │
│  │ tree()             │    ────>     │ .update_current_    │            │
│  │                    │              │  trace()            │            │
│  │                    │              │ .update_current_    │            │
│  │                    │              │  span()             │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ Client()            │              │ Langfuse()          │            │
│  │ - hide_inputs       │    ────>     │ - public_key        │            │
│  │ - hide_outputs      │              │ - secret_key        │            │
│  │                     │              │ - base_url          │            │
│  └─────────────────────┘              └─────────────────────┘            │
│           │                                      │                         │
│           │                                      │                         │
│           v                                      v                         │
│  ┌─────────────────────┐              ┌─────────────────────┐            │
│  │ schemas.Run        │              │ Trace/Span objects  │            │
│  │ schemas.Example    │    ────>     │ (native Python)     │            │
│  │                    │              │                     │            │
│  └─────────────────────┘              └─────────────────────┘            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Detailed Migration Plan

### Phase 1: Core Infrastructure (Day 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.1: Replace robust_traceable Decorator                             │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/core/tracing.py                                         │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import traceable                                    │  │
│  │                                                                     │  │
│  │ def robust_traceable(...):                                         │  │
│  │     traced_func = traceable(                                       │  │
│  │         run_type=run_type,                                         │  │
│  │         name=name or func.__name__,                                │  │
│  │         tags=tags or [],                                           │  │
│  │         metadata=metadata or {},                                   │  │
│  │     )                                                               │  │
│  │     return traced_func(func)                                        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import observe                                       │  │
│  │                                                                     │  │
│  │ def robust_traceable(                                               │  │
│  │     name: str | None = None,                                        │  │
│  │     run_type: RunType = "chain",                                    │  │
│  │     tags: list[str] | None = None,                                  │  │
│  │     metadata: dict[str, str | int | float | bool] | None = None,    │  │
│  │     **observe_kwargs: object,                                       │  │
│  │ ) -> Callable:                                                      │  │
│  │     def decorator(func):                                            │  │
│  │         # Map run_type to as_type                                   │  │
│  │         as_type_map = {                                             │  │
│  │             "chain": "chain",                                      │  │
│  │             "tool": "tool",                                        │  │
│  │             "llm": "generation",                                   │  │
│  │             "retriever": "retriever",                              │  │
│  │             "embedding": "embedding",                              │  │
│  │         }                                                           │  │
│  │         as_type = as_type_map.get(run_type, "chain")                │  │
│  │                                                                     │  │
│  │         observed_func = observe(                                    │  │
│  │             name=name or func.__name__,                             │  │
│  │             as_type=as_type,                                       │  │
│  │             tags=tags or [],                                       │  │
│  │             metadata=metadata or {},                               │  │
│  │             **observe_kwargs,                                      │  │
│  │         )                                                           │  │
│  │         return observed_func(func)                                 │  │
│  │     return decorator                                                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  BREAKING CHANGES:                                                      │
│     • run_type="llm" → as_type="generation"                                │
│     • Metadata structure may differ slightly                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.2: Replace get_current_run_tree() Calls                            │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import get_current_run_tree                          │  │
│  │                                                                     │  │
│  │ run_tree = get_current_run_tree()                                   │  │
│  │ if run_tree:                                                        │  │
│  │     run_tree.metadata["analysis_id"] = str(analysis_id)            │  │
│  │     run_tree.tags.append("parallel-execution")                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()                                            │  │
│  │ if langfuse:                                                        │  │
│  │     langfuse.update_current_trace(                                  │  │
│  │         metadata={"analysis_id": str(analysis_id)},                │  │
│  │         tags=["parallel-execution"],                                │  │
│  │     )                                                               │  │
│  │     langfuse.update_current_span(                                  │  │
│  │         metadata={"analysis_id": str(analysis_id)},                │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • Separate trace vs span updates                                     │
│     • Tags passed as list, not appended                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 1.3: Replace Client Configuration                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/core/langsmith_config.py → langfuse_config.py          │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import Client                                        │  │
│  │                                                                     │  │
│  │ _langsmith_client = Client(                                         │  │
│  │     hide_inputs=hide_inputs_with_generator_filter,                 │  │
│  │     hide_outputs=hide_outputs_with_generator_filter,                │  │
│  │ )                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import Langfuse                                       │  │
│  │                                                                     │  │
│  │ _langfuse_client = Langfuse(                                       │  │
│  │     public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),                    │  │
│  │     secret_key=os.getenv("LANGFUSE_SECRET_KEY"),                    │  │
│  │     base_url=os.getenv("LANGFUSE_BASE_URL",                         │  │
│  │                      "https://cloud.langfuse.com"),                 │  │
│  │     environment=os.getenv("ENVIRONMENT", "development"),             │  │
│  │     # Generator filtering handled automatically                     │  │
│  │ )                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ✅ IMPROVEMENTS:                                                           │
│     • No need for generator filtering workaround                          │
│     • Better environment/release tracking                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: Evaluation System (Day 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 2.1: Replace LangSmithExtractor                                      │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/evaluation/ingestion/langsmith_extractor.py            │
│  → langfuse_extractor.py                                                  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import Client                                        │  │
│  │                                                                     │  │
│  │ client = Client()                                                   │  │
│  │ runs = client.list_runs(                                             │  │
│  │     project_name=config.project_name,                               │  │
│  │     start_time=config.date_start,                                   │  │
│  │     end_time=config.date_end,                                       │  │
│  │     filter=f"eq(tags, '{config.agent_type}')",                      │  │
│  │ )                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import Langfuse                                       │  │
│  │                                                                     │  │
│  │ langfuse = Langfuse()                                              │  │
│  │                                                                     │  │
│  │ # Query traces via API                                              │  │
│  │ traces = langfuse.trace.get_many(                                   │  │
│  │     name=config.agent_type,                                         │  │
│  │     from_timestamp=config.date_start,                               │  │
│  │     to_timestamp=config.date_end,                                    │  │
│  │     tags=[config.agent_type],                                       │  │
│  │     limit=config.limit,                                             │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ for trace in traces.data:                                           │  │
│  │     # Extract example from trace                                    │  │
│  │     example = convert_trace_to_example(trace)                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  API DIFFERENCES:                                                       │
│     • Different query syntax (get_many vs list_runs)                      │
│     • Trace structure differs from Run structure                           │
│     • Need to map trace fields to example format                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 2.2: Replace Evaluator Schemas                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Files:                                                                    │
│    • evaluation/evaluators/quality.py                                     │
│    • evaluation/evaluators/cost.py                                         │
│    • evaluation/evaluators/correctness.py                                 │
│    • evaluation/evaluators/latency.py                                      │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith.schemas import Example, Run                           │  │
│  │                                                                     │  │
│  │ def evaluate(run: Run, example: Example) -> float:                  │  │
│  │     # Access run.outputs, run.inputs, etc.                          │  │
│  │     return score                                                    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import Trace, Span                                    │  │
│  │                                                                     │  │
│  │ def evaluate(trace: Trace, span: Span | None = None) -> float:      │  │
│  │     # Access trace.input, trace.output, etc.                       │  │
│  │     # Langfuse uses different field names                           │  │
│  │     return score                                                    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  FIELD MAPPING:                                                         │
│     • run.inputs → trace.input                                            │
│     • run.outputs → trace.output                                          │
│     • run.metadata → trace.metadata                                        │
│     • run.tags → trace.tags                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 3: Metrics Service (Day 2-3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 3.1: Replace LangSmithMetricsService                                 │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/services/metrics/langsmith.py                          │
│  → langfuse_metrics.py                                                    │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith import Client                                        │  │
│  │                                                                     │  │
│  │ client = Client()                                                   │  │
│  │ runs = client.list_runs(                                             │  │
│  │     project_name=project,                                           │  │
│  │     start_time=start_time,                                          │  │
│  │     end_time=end_time,                                              │  │
│  │     filter=f"eq(tags, '{agent_type}')",                            │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Aggregate metrics from runs                                      │  │
│  │ success_rate = sum(1 for r in runs if r.status == "success") / len │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import Langfuse                                       │  │
│  │                                                                     │  │
│  │ langfuse = Langfuse()                                              │  │
│  │                                                                     │  │
│  │ traces = langfuse.trace.get_many(                                   │  │
│  │     tags=[agent_type],                                              │  │
│  │     from_timestamp=start_time,                                      │  │
│  │     to_timestamp=end_time,                                          │  │
│  │ )                                                                   │  │
│  │                                                                     │  │
│  │ # Aggregate metrics from traces                                    │  │
│  │ success_rate = sum(1 for t in traces.data                          │  │
│  │                  if t.status == "COMPLETED") / len(traces.data)     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • Different status values (COMPLETED vs success)                       │
│     • Different pagination model                                           │
│     • May need to use Langfuse Analytics API for aggregation              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 4: Quality Gate Node (Day 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 4.1: Update Quality Gate Node                                        │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  File: backend/app/domains/analysis/workflows/nodes/quality_gate_node.py  │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langsmith.schemas import Example, Run                          │  │
│  │ from langsmith import get_current_run_tree                          │  │
│  │                                                                     │  │
│  │ run_tree = get_current_run_tree()                                   │  │
│  │ if run_tree:                                                        │  │
│  │     # Create Example for evaluation                                 │  │
│  │     example = Example(                                               │  │
│  │         inputs={"content": content},                                │  │
│  │         outputs={"artifact": artifact},                              │  │
│  │     )                                                               │  │
│  │     run = Run(                                                       │  │
│  │         inputs={"content": content},                                 │  │
│  │         outputs={"artifact": artifact},                             │  │
│  │         start_time=datetime.now(UTC),                                  │  │
│  │         trace_id=uuid4(),                                            │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ from langfuse import get_client                                     │  │
│  │                                                                     │  │
│  │ langfuse = get_client()                                            │  │
│  │ if langfuse:                                                        │  │
│  │     # Create dataset item for evaluation                            │  │
│  │     langfuse.create_dataset_item(                                   │  │
│  │         dataset_name="quality-gate-eval",                            │  │
│  │         input={"content": content},                                  │  │
│  │         expected_output={"artifact": artifact},                      │  │
│  │     )                                                               │  │
│  │                                                                     │  │
│  │     # Score current trace                                           │  │
│  │     langfuse.score_trace(                                           │  │
│  │         name="quality_score",                                       │  │
│  │         value=score,                                                 │  │
│  │         data_type="NUMERIC",                                         │  │
│  │     )                                                               │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • No need to manually create Run/Example objects                      │
│     • Use dataset items for evaluation examples                           │
│     • Scoring API is different                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 5: Test Suite Updates (Day 4)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  STEP 5.1: Update Test Mocks                                               │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Files to Update:                                                          │
│    • tests/unit/core/test_tracing.py                                      │
│    • tests/unit/services/test_langsmith_metrics.py                         │
│    • tests/unit/evaluation/test_langsmith_extractor.py                    │
│    • tests/unit/workflows/nodes/test_quality_gate_node.py                 │
│    • tests/unit/workflows/agents/test_invocation.py                        │
│    • tests/conftest.py                                                    │
│                                                                             │
│  BEFORE (LangSmith):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ @patch("langsmith.get_current_run_tree")                            │  │
│  │ @patch("langsmith.schemas.Run")                                      │  │
│  │ @patch("langsmith.schemas.Example")                                  │  │
│  │ def test_something(mock_run_tree, mock_run, mock_example):          │  │
│  │     mock_run_tree.return_value = Mock(...)                           │  │
│  │     # Test code                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  AFTER (Langfuse):                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ @patch("langfuse.get_client")                                       │  │
│  │ @patch("langfuse.Trace")                                             │  │
│  │ @patch("langfuse.Span")                                              │  │
│  │ def test_something(mock_client, mock_trace, mock_span):              │  │
│  │     mock_client.return_value = Mock(...)                              │  │
│  │     # Test code                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ⚠️  CHANGES:                                                               │
│     • Update all @patch decorators                                        │
│     • Update mock return values to match Langfuse API                     │
│     • Update conftest.py to disable Langfuse tracing                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Differences & Challenges

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🔴 CRITICAL DIFFERENCES                                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  1. DECORATOR API                                                          │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: @traceable(run_type="llm")                          │  │
│     │ Langfuse:  @observe(as_type="generation")                      │  │
│     │                                                                │  │
│     │ ⚠️  Need to map run_type → as_type                            │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  2. METADATA UPDATES                                                       │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: run_tree.metadata["key"] = value                    │  │
│     │ Langfuse:  langfuse.update_current_trace(metadata={...})       │  │
│     │                                                                │  │
│     │ ⚠️  Different API pattern (setter vs method)                  │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  3. CLIENT INITIALIZATION                                                  │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Client() (uses env vars)                            │  │
│     │ Langfuse:  Langfuse(public_key=..., secret_key=...)            │  │
│     │                                                                │  │
│     │ ⚠️  Need to update environment variables                        │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  4. TRACE QUERYING                                                         │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: client.list_runs(filter="eq(tags, 'x')")             │  │
│     │ Langfuse:  langfuse.trace.get_many(tags=["x"])                 │  │
│     │                                                                │  │
│     │ ⚠️  Different query syntax                                      │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  5. SCHEMA OBJECTS                                                         │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Run, Example (Pydantic models)                      │  │
│     │ Langfuse:  Trace, Span (native Python dicts)                  │  │
│     │                                                                │  │
│     │ ⚠️  Different field names and structure                        │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  6. GENERATOR FILTERING                                                    │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ LangSmith: Required hide_inputs/hide_outputs workaround        │  │
│     │ Langfuse:  Handles generators automatically                    │  │
│     │                                                                │  │
│     │ ✅ Can remove generator filtering code!                        │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Benefits of Migration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎁 ADVANTAGES OF LANGFUSE                                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  ✅ Open Source & Self-Hostable                                            │
│     • Full control over data and infrastructure                           │
│     • No vendor lock-in                                                    │
│     • Can run on-premises or cloud                                         │
│                                                                             │
│  ✅ Better Generator Handling                                               │
│     • No need for hide_inputs/hide_outputs workaround                     │
│     • Automatic handling of async generators                               │
│                                                                             │
│  ✅ Modern API Design                                                       │
│     • More intuitive decorator API (@observe)                              │
│     • Better separation of trace vs span updates                           │
│     • Native Python objects (no Pydantic overhead)                        │
│                                                                             │
│  ✅ Enhanced Features                                                       │
│     • Built-in prompt management                                           │
│     • Better dataset management                                            │
│     • Advanced scoring mechanisms                                          │
│     • Media file support                                                   │
│                                                                             │
│  ✅ Native MCP Server for Prompts                                           │
│     • Dedicated MCP server for accessing Langfuse prompts                  │
│     • Automatic MCP tracing with context propagation                       │
│     • Direct integration with Claude Desktop/Cursor/Windsurf                │
│     • Works with existing MCP servers (context7, memory, etc.)            │
│     • Note: LangSmith exposes agents as MCP tools, Langfuse provides      │
│       MCP server for prompt access                                          │
│                                                                             │
│  ✅ Cost Savings                                                            │
│     • Self-hosted = no per-trace costs                                     │
│     • Open source = no licensing fees                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏠 Local Self-Hosted Setup (FREE)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎯 SETUP: FREE LOCAL LANGFUSE INSTANCE                                      │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  We're using Langfuse self-hosted locally (FREE, no cloud costs!)         │
│                                                                             │
│  STEP 1: Add Langfuse to docker-compose.yml                                │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Langfuse service has been added to docker-compose.yml with:               │
│    • PostgreSQL database (separate from SkillForge DB)                    │
│    • Web UI on http://localhost:3000                                       │
│    • API on http://localhost:3000/api                                     │
│    • Persistent volumes for data                                          │
│                                                                             │
│  STEP 2: Start Langfuse                                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│  ```bash                                                                   │
│  # Start Langfuse service                                                  │
│  docker-compose up -d langfuse                                            │
│                                                                             │
│  # Check logs                                                              │
│  docker-compose logs -f langfuse                                          │
│                                                                             │
│  # Verify it's running                                                     │
│  curl http://localhost:3000/api/public/health                             │
│  ```                                                                        │
│                                                                             │
│  STEP 3: Initial Setup                                                     │
│  ────────────────────────────────────────────────────────────────────────  │
│  1. Open http://localhost:3000 in browser                                 │
│  2. Create admin account (first user becomes admin)                        │
│  3. Create a project                                                       │
│  4. Generate API keys (Settings → API Keys)                               │
│  5. Copy public_key and secret_key                                        │
│                                                                             │
│  STEP 4: Update Environment Variables                                      │
│  ────────────────────────────────────────────────────────────────────────  │
│  Add to backend/.env:                                                      │
│  ```env                                                                    │
│  # Langfuse (Local Self-Hosted)                                            │
│  LANGFUSE_PUBLIC_KEY=pk-lf-...                                            │
│  LANGFUSE_SECRET_KEY=sk-lf-...                                            │
│  LANGFUSE_BASE_URL=http://langfuse:3000  # Internal Docker network        │
│  LANGFUSE_TRACING_ENABLED=true                                            │
│  ```                                                                        │
│                                                                             │
│  Note: Use http://langfuse:3000 for backend service (Docker network)        │
│        Use http://localhost:3000 for browser access                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📦 Dependency Changes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  pyproject.toml Updates                                                     │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  REMOVE:                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ langsmith = "^1.0.0"  # Remove this                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ADD:                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ langfuse = "^3.0.0"  # Add Langfuse SDK v3                          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ENVIRONMENT VARIABLES (Local Self-Hosted):                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ # Remove                                                             │  │
│  │ LANGCHAIN_TRACING_V2=true                                            │  │
│  │ LANGSMITH_API_KEY=...                                                │  │
│  │                                                                       │  │
│  │ # Add (Local Self-Hosted)                                            │  │
│  │ LANGFUSE_PUBLIC_KEY=pk-lf-...  # From Langfuse UI                    │  │
│  │ LANGFUSE_SECRET_KEY=sk-lf-...  # From Langfuse UI                    │  │
│  │ LANGFUSE_BASE_URL=http://langfuse:3000  # Docker internal network    │  │
│  │ LANGFUSE_TRACING_ENABLED=true                                        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ✅ BENEFITS OF LOCAL SETUP:                                                │
│     • FREE - No per-trace costs                                            │
│     • Full data control - All traces stored locally                         │
│     • No internet required - Works offline                                  │
│     • Fast - No network latency                                            │
│     • Privacy - Data never leaves your machine                              │
│     • MCP Support - Native MCP server for prompts and tracing              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Migration Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE 1: PREPARATION                                                      │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Set up Langfuse instance (local self-hosted via docker-compose)       │
│  [ ] Create API keys (public_key, secret_key) from Langfuse UI            │
│  [ ] Update environment variables                                         │
│  [ ] Install langfuse package                                              │
│  [ ] Clone Langfuse MCP server: git clone langfuse/mcp-server-langfuse    │
│  [ ] Build MCP server: npm install && npm run build                       │
│  [ ] Configure MCP server in .mcp.json (for prompt access from IDE)      │
│  [ ] Create feature branch: issue/XXX-langfuse-migration                   │
│                                                                             │
│  PHASE 2: CORE INFRASTRUCTURE                                              │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Replace robust_traceable decorator                                    │
│  [ ] Replace get_current_run_tree() calls                                 │
│  [ ] Replace Client() initialization                                       │
│  [ ] Remove generator filtering code                                        │
│  [ ] Update langsmith_config.py → langfuse_config.py                       │
│                                                                             │
│  PHASE 3: WORKFLOW NODES                                                    │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Update 8 agent nodes                                                  │
│  [ ] Update 8 tutor nodes                                                  │
│  [ ] Update quality gate node                                              │
│  [ ] Update agent invocation/streaming                                     │
│                                                                             │
│  PHASE 4: EVALUATION SYSTEM                                                │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Replace LangSmithExtractor → LangfuseExtractor                        │
│  [ ] Update evaluator schemas (quality, cost, correctness, latency)       │
│  [ ] Update llm_benchmark.py                                               │
│                                                                             │
│  PHASE 5: METRICS SERVICE                                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Replace LangSmithMetricsService → LangfuseMetricsService              │
│  [ ] Update metrics aggregation logic                                       │
│                                                                             │
│  PHASE 6: TEST SUITE                                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Update test mocks (100+ files)                                        │
│  [ ] Update conftest.py                                                   │
│  [ ] Run full test suite                                                   │
│  [ ] Verify coverage ≥80%                                                 │
│                                                                             │
│  PHASE 7: VALIDATION                                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Run integration tests                                                │
│  [ ] Verify traces appear in Langfuse UI                                   │
│  [ ] Verify metrics are correct                                            │
│  [ ] Verify evaluation extraction works                                    │
│  [ ] Test MCP tracing (if using MCP tools)                                 │
│  [ ] Verify MCP prompt server access (if configured)                       │
│  [ ] Performance testing (no regressions)                                   │
│                                                                             │
│  PHASE 8: DEPLOYMENT                                                       │
│  ────────────────────────────────────────────────────────────────────────  │
│  [ ] Update documentation                                                  │
│  [ ] Create migration guide for team                                       │
│  [ ] Deploy to staging                                                     │
│  [ ] Monitor for 24-48 hours                                               │
│  [ ] Deploy to production                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Best Practices (December 2025)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎯 MIGRATION BEST PRACTICES                                                │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  1. INCREMENTAL MIGRATION                                                   │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Start with core tracing infrastructure                        │  │
│     │ • Migrate one workflow at a time                                │  │
│     │ • Keep LangSmith running in parallel during transition          │  │
│     │ • Use feature flags to toggle between providers                  │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  2. TESTING STRATEGY                                                        │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Run both LangSmith and Langfuse in parallel                   │  │
│     │ • Compare trace outputs for consistency                         │  │
│     │ • Verify all test cases pass                                    │  │
│     │ • Test with real workflows before full migration                │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  3. DATA MIGRATION                                                          │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Export existing LangSmith traces (if needed)                  │  │
│     │ • Import historical data to Langfuse (optional)                  │  │
│     │ • Keep LangSmith data for historical reference                  │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  4. MONITORING                                                              │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Monitor trace volume and latency                              │  │
│     │ • Set up alerts for missing traces                              │  │
│     │ • Track error rates during migration                            │  │
│     │ • Verify cost tracking accuracy                                 │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  5. ROLLBACK PLAN                                                           │
│     ┌─────────────────────────────────────────────────────────────────┐  │
│     │ • Keep LangSmith code in feature branch                         │  │
│     │ • Use feature flags for easy rollback                           │  │
│     │ • Document rollback procedure                                    │  │
│     │ • Test rollback process before production                       │  │
│     └─────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Model Context Protocol (MCP) Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  🎯 MCP SUPPORT IN LANGFUSE - HOW TO UTILIZE IT                            │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Both LangSmith and Langfuse support MCP (Model Context Protocol), but     │
│  Langfuse offers a dedicated MCP server for prompt management.             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  WHAT IS MCP?                                                       │  │
│  │  ────────────────────────────────────────────────────────────────  │  │
│  │                                                                     │  │
│  │  Model Context Protocol (MCP) is an open standard developed by    │  │
│  │  Anthropic that enables AI agents to securely connect to external │  │
│  │  data sources and tools. It standardizes how AI applications       │  │
│  │  communicate with external services, making it easier to build    │  │
│  │  context-aware AI agents.                                           │  │
│  │                                                                     │  │
│  │  Key Benefits:                                                      │  │
│  │    • Standardized protocol for agent-tool communication            │  │
│  │    • Secure connection to external data sources                     │  │
│  │    • Works with Claude Desktop, Cursor, and other MCP clients      │  │
│  │    • Enables AI agents to access prompts, traces, and datasets      │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  LANGFUSE MCP FEATURES                                               │  │
│  │  ────────────────────────────────────────────────────────────────  │  │
│  │                                                                     │  │
│  │  1. MCP SERVER FOR PROMPT MANAGEMENT                                │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ Langfuse provides an MCP server that enables AI agents  │  │
│  │     │ to access and manage prompts directly from Claude Desktop,│  │
│  │     │ Cursor, or other MCP clients.                             │  │
│  │     │                                                             │  │
│  │     │ Features:                                                  │  │
│  │     │   • Access prompts from Langfuse Prompt Management        │  │
│  │     │   • Version control and prompt history                     │  │
│  │     │   • Collaborative prompt management                        │  │
│  │     │   • Direct integration with AI agent workflows              │  │
│  │     │                                                             │  │
│  │     │ Use Case for SkillForge:                                   │  │
│  │     │   Our 8 specialized agents (tech_comparator,               │  │
│  │     │   security_auditor, etc.) can access shared prompts        │  │
│  │     │   directly from Langfuse, ensuring consistency and         │  │
│  │     │   enabling prompt versioning across the team.              │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  2. MCP TRACING & OBSERVABILITY                                     │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │ Langfuse supports tracing MCP applications, allowing     │  │
│  │     │ you to monitor agent interactions with external tools     │  │
│  │     │ and data sources.                                         │  │
│  │     │                                                             │  │
│  │     │ Features:                                                  │  │
│  │     │   • Automatic tracing of MCP client and server operations│  │
│  │     │   • Context propagation via MCP _meta field               │  │
│  │     │   • Link client and server traces for full visibility     │  │
│  │     │   • OpenTelemetry integration (W3C Trace Context)         │  │
│  │     │                                                             │  │
│  │     │ Use Case for SkillForge:                                   │  │
│  │     │   When our agents use MCP tools (like context7 for        │  │
│  │     │   documentation, postgres for database queries), we can   │  │
│  │     │   trace these interactions in Langfuse, providing full    │  │
│  │     │   observability of agent workflows.                        │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  3. SETUP & CONFIGURATION                                            │  │
│  │     ┌───────────────────────────────────────────────────────────┐  │  │
│  │     │                                                             │  │
│  │     │ STEP 1: Clone and Build Langfuse MCP Server               │  │
│  │     │   ```bash                                                 │  │
│  │     │   git clone https://github.com/langfuse/mcp-server-langfuse.git│  │
│  │     │   cd mcp-server-langfuse                                   │  │
│  │     │   npm install                                             │  │
│  │     │   npm run build                                           │  │
│  │     │   ```                                                     │  │
│  │     │                                                             │  │
│  │     │   Note: The built server will be at `build/index.js`      │  │
│  │     │   You'll need the absolute path to this file for config.   │  │
│  │     │                                                             │  │
│  │     │ STEP 2: Configure for Cursor IDE                          │  │
│  │     │   Add to `.mcp.json` or `mcp.json`:                       │  │
│  │     │   ```json                                                 │  │
│  │     │   {                                                       │  │
│  │     │     "mcpServers": {                                       │  │
│  │     │       "langfuse-prompts": {                               │  │
│  │     │         "command": "node",                                │  │
│  │     │         "args": ["<absolute-path>/build/index.js"],       │  │
│  │     │         "env": {                                         │  │
│  │     │           "LANGFUSE_PUBLIC_KEY": "pk-lf-...",            │  │
│  │     │           "LANGFUSE_SECRET_KEY": "sk-lf-...",            │  │
│  │     │           "LANGFUSE_BASEURL": "http://localhost:3000"    │  │
│  │     │         }                                                 │  │
│  │     │       }                                                   │  │
│  │     │     }                                                     │  │
│  │     │   }                                                       │  │
│  │     │   ```                                                     │  │
│  │     │                                                             │  │
│  │     │ STEP 3: Configure for Claude Desktop                      │  │
│  │     │   Add to `claude_desktop_config.json`:                    │  │
│  │     │   ```json                                                 │  │
│  │     │   {                                                       │  │
│  │     │     "mcpServers": {                                       │  │
│  │     │       "langfuse": {                                      │  │
│  │     │         "command": "node",                                │  │
│  │     │         "args": ["<absolute-path>/build/index.js"],       │  │
│  │     │         "env": {                                         │  │
│     │           "LANGFUSE_PUBLIC_KEY": "your-public-key",        │  │
│     │           "LANGFUSE_SECRET_KEY": "your-secret-key",        │  │
│  │     │           "LANGFUSE_BASEURL": "http://localhost:3000"    │  │
│  │     │         }                                                 │  │
│  │     │       }                                                   │  │
│  │     │     }                                                     │  │
│  │     │   }                                                       │  │
│  │     │   ```                                                     │  │
│  │     │                                                             │  │
│  │     │ STEP 4: Configure for Claude Code (CLI)                   │  │
│  │     │   ```bash                                                 │  │
│  │     │   claude mcp add \                                        │  │
│  │     │     --transport http \                                    │  │
│  │     │     langfuse-docs \                                       │  │
│  │     │     https://langfuse.com/api/mcp \                        │  │
│  │     │     --scope user                                          │  │
│  │     │   ```                                                     │  │
│  │     │                                                             │  │
│  │     │ STEP 5: Configure for Windsurf                            │  │
│  │     │   ```json                                                 │  │
│  │     │   {                                                       │  │
│  │     │     "mcpServers": {                                       │  │
│  │     │       "langfuse-docs": {                                  │  │
│  │     │         "command": "npx",                                 │  │
│  │     │         "args": ["mcp-remote", "https://langfuse.com/api/mcp"]│  │
│  │     │       }                                                   │  │
│  │     │     }                                                     │  │
│  │     │   }                                                       │  │
│  │     │   ```                                                     │  │
│  │     │                                                             │  │
│  │     │ Use Case for SkillForge:                                   │  │
│  │     │   Developers can access Langfuse prompts directly from   │  │
│  │     │   Cursor/Claude Desktop, making it easier to work with    │  │
│  │     │   agent prompts during development.                       │  │
│  │     └───────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  MCP TRACING IMPLEMENTATION FOR SKILLFORGE                           │  │
│  │  ────────────────────────────────────────────────────────────────  │  │
│  │                                                                     │  │
│  │  SkillForge already uses MCP servers (context7, memory,            │  │
│  │  sequential-thinking). With Langfuse, we can trace these MCP       │  │
│  │  interactions automatically.                                      │  │
│  │                                                                     │  │
│  │  HOW MCP TRACING WORKS:                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ • MCP client and server operations produce separate traces   │  │
│  │  │   by default (helps establish service boundaries)            │  │
│  │  │ • Context propagation via MCP _meta field:                   │  │
│  │  │   1. Extract OpenTelemetry trace context on client side     │  │
│  │  │   2. Inject into MCP _meta field in tool calls              │  │
│  │  │   3. Extract and restore context on server side             │  │
│  │  │   4. All server operations inherit client's trace context   │  │
│  │  │ • Uses W3C Trace Context format for distributed tracing      │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  AFTER (Langfuse - Native MCP Support):                            │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ • Automatic MCP tracing via context propagation             │  │
│  │  │ • Full visibility into agent-tool interactions               │  │
│  │  │ • Linked traces for client and server operations            │  │
│  │  │ • OpenTelemetry integration for distributed tracing          │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  Implementation Steps:                                             │  │
│  │  1. Configure MCP context propagation in agent code               │  │
│  │  2. Inject OpenTelemetry trace context into MCP _meta field       │  │
│  │  3. Langfuse automatically links client and server traces         │  │
│  │  4. View complete agent workflow in Langfuse UI                   │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  MCP PROMPT SERVER BENEFITS                                         │  │
│  │  ────────────────────────────────────────────────────────────────  │  │
│  │                                                                     │  │
│  │  SkillForge's 8 specialized agents can benefit from Langfuse's    │  │
│  │  MCP Prompt Server:                                                │  │
│  │                                                                     │  │
│  │  • Centralized Prompt Management:                                  │  │
│  │    All agent prompts stored in Langfuse, accessible via MCP       │  │
│  │                                                                     │  │
│  │  • Version Control:                                                 │  │
│  │    Track prompt versions, A/B test different prompts              │  │
│  │                                                                     │  │
│  │  • Collaborative Editing:                                           │  │
│  │    Team members can update prompts in Langfuse UI                  │  │
│  │                                                                     │  │
│  │  • Direct Agent Access:                                             │  │
│  │    Agents fetch prompts directly via MCP, no code changes needed │  │
│  │                                                                     │  │
│  │  • Prompt Analytics:                                                │  │
│  │    See which prompts perform best across different agents          │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  COMPARISON: LANGSMITH VS LANGFUSE MCP SUPPORT                      │  │
│  │  ────────────────────────────────────────────────────────────────  │  │
│  │                                                                     │  │
│  │  LangSmith MCP Support:                                             │  │
│  │    ✅ Exposes agents as MCP tools via Agent Server                 │  │
│  │    ✅ MCP endpoint at /mcp (Streamable HTTP transport)            │  │
│  │    ✅ Custom authentication middleware support                     │  │
│  │    ✅ Works with MCP-compliant clients                            │  │
│  │    ❌ No dedicated MCP server for prompt management               │  │
│  │                                                                     │  │
│  │  Langfuse MCP Support:                                              │  │
│  │    ✅ Dedicated MCP server for prompt management                  │  │
│  │    ✅ MCP tracing with context propagation                        │  │
│  │    ✅ OpenTelemetry integration (W3C Trace Context)                │  │
│  │    ✅ Direct integration with Claude Desktop/Cursor/Windsurf       │  │
│  │    ✅ Works seamlessly with existing MCP servers                  │  │
│  │                                                                     │  │
│  │  KEY DIFFERENCE:                                                    │  │
│  │    LangSmith exposes YOUR agents as MCP tools.                     │  │
│  │    Langfuse provides an MCP server to access ITS prompts.          │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 References

- **Langfuse Python SDK v3 Docs:** https://langfuse.com/docs/sdk/python
- **Langfuse Migration Guide:** https://langfuse.com/docs/sdk/python/sdk-v3#upgrade-from-v2
- **Langfuse vs LangSmith:** https://langfuse.com/faq/all/langsmith-alternative
- **Langfuse Self-Hosting:** https://langfuse.com/docs/deployment/self-host
- **Langfuse MCP Server:** https://langfuse.com/docs/prompts/features/mcp-server
- **Langfuse MCP Server GitHub:** https://github.com/langfuse/mcp-server-langfuse
- **Langfuse MCP Tracing:** https://langfuse.com/docs/observability/features/mcp-tracing
- **Model Context Protocol:** https://modelcontextprotocol.io/
- **LangSmith MCP Support:** https://docs.langchain.com/langsmith/server-mcp
- **LangSmith MCP Support:** https://docs.langchain.com/langsmith/server-mcp

---

## 📝 Notes

- **Generator Filtering:** Can be removed entirely (Langfuse handles this automatically)
- **Test Coverage:** Ensure ≥80% coverage maintained after migration
- **Breaking Changes:** Minimal - mostly API surface changes
- **Performance:** Should be similar or better (less overhead from generator filtering)
- **MCP Support:** Langfuse provides dedicated MCP server for prompt access (different from LangSmith's agent-as-MCP-tool approach)
- **MCP Integration:** SkillForge can leverage Langfuse MCP server for prompt management and MCP tracing for agent-tool interactions

---

**Last Updated:** December 16, 2025  
**Next Steps:** Create feature branch and begin Phase 1 migration


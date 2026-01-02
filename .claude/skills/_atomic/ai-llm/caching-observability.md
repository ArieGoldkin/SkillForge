---
name: caching-observability
description: Langfuse cost tracking and cache monitoring
version: 1.0.0
tags: [llm, caching, langfuse, monitoring]
size: atomic
domain: ai-llm
---

# LLM Cache Observability

## Langfuse Cost Tracking

```python
from langfuse.decorators import observe, langfuse_context
from uuid import UUID

@observe(as_type="generation")
async def call_llm_with_cache(
    prompt: str,
    agent_type: str,
    analysis_id: UUID | None = None
) -> str:
    """LLM call with automatic cost tracking."""

    # Link to parent trace for cost rollup
    if analysis_id:
        langfuse_context.update_current_trace(
            name=f"{agent_type}_generation",
            session_id=str(analysis_id),
            tags=[agent_type, "cached"],
            metadata={"analysis_id": str(analysis_id)}
        )

    # Check caches
    cache_key = hash_content(prompt)
    if cache_key in lru_cache:
        langfuse_context.update_current_observation(
            metadata={"cache_layer": "L1", "cache_hit": True}
        )
        return lru_cache[cache_key]

    similar = await redis_cache.find_similar(prompt, agent_type)
    if similar:
        langfuse_context.update_current_observation(
            metadata={"cache_layer": "L2", "cache_hit": True}
        )
        return similar.response

    # LLM call - Langfuse tracks automatically
    response = await llm.generate(prompt)

    langfuse_context.update_current_observation(
        metadata={
            "cache_layer": "L3/L4",
            "cache_hit": False,
            "prompt_cache_hit": response.usage.cache_read_input_tokens > 0
        }
    )

    return response.content
```

## Trace Hierarchy for Multi-Agent

```python
class AnalysisWorkflow:
    @observe(as_type="trace")
    async def run_analysis(self, url: str, analysis_id: UUID) -> dict:
        """Parent trace - aggregates all child costs.

        Trace Hierarchy:
        run_analysis (trace)
        ├── tech_comparator_generation
        ├── security_auditor_generation
        └── synthesis_generation
        """

        langfuse_context.update_current_trace(
            name="content_analysis",
            session_id=str(analysis_id),
            tags=["multi-agent"],
            metadata={"url": url, "agent_count": 8}
        )

        # Each agent creates child generation
        findings = {}
        for agent in self.agents:
            result = await self.run_agent(agent, content, analysis_id)
            findings[agent.name] = result

        return findings

    @observe(as_type="generation")
    async def run_agent(self, agent, content, analysis_id):
        langfuse_context.update_current_observation(
            name=f"{agent.name}_generation",
            metadata={"agent_type": agent.name}
        )
        return await agent.analyze(content)
```

## Cost Queries

```python
from langfuse import Langfuse

async def get_analysis_costs(analysis_id: UUID) -> dict:
    langfuse = Langfuse()

    traces = langfuse.get_traces(session_id=str(analysis_id), limit=1)
    if not traces.data:
        return {"error": "Not found"}

    trace = traces.data[0]
    return {
        "total_cost": trace.total_cost,
        "input_tokens": trace.usage.input_tokens,
        "output_tokens": trace.usage.output_tokens,
        "cache_read_tokens": trace.usage.cache_read_input_tokens,
    }

async def get_costs_by_agent() -> list[dict]:
    langfuse = Langfuse()

    generations = langfuse.get_generations(limit=1000)

    costs = {}
    for gen in generations.data:
        agent = gen.metadata.get("agent_type", "unknown")
        if agent not in costs:
            costs[agent] = {"total": 0, "count": 0, "cache_hits": 0}

        costs[agent]["total"] += gen.calculated_total_cost or 0
        costs[agent]["count"] += 1
        if gen.metadata.get("cache_hit"):
            costs[agent]["cache_hits"] += 1

    return [
        {**v, "agent": k, "hit_rate": v["cache_hits"] / v["count"]}
        for k, v in costs.items()
    ]
```

## Key Metrics

```python
@dataclass
class CacheMetrics:
    # Hit rates
    l1_hit_rate: float
    l2_hit_rate: float
    l3_hit_rate: float
    combined_hit_rate: float

    # Latency
    l1_avg_latency_ms: float
    l2_avg_latency_ms: float
    l3_avg_latency_ms: float

    # Cost
    estimated_cost_saved_usd: float
    total_requests: int

    # Quality
    false_positive_rate: float
    false_negative_rate: float
```

## Dashboard Views

**Cost Dashboard:**
- Total cost by day/week/month
- Cost breakdown by model
- Cost attribution by agent
- Top 10 expensive traces

**Cache Effectiveness:**
- L1/L2/L3 hit rates
- Cost savings from each layer
- False positive rate

**Agent Performance:**
- Average cost per agent
- Token usage distribution
- Cache hit rate by agent

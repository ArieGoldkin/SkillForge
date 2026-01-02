---
name: langgraph-langfuse
description: Observability for LangGraph workflows with Langfuse
version: 1.0.0
tags: [ai, langgraph, langfuse, observability, tracing, monitoring]
size: atomic
domain: ai-llm
---

# LangGraph + Langfuse Observability

## Setup

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

langfuse = Langfuse(
    host="https://cloud.langfuse.com",
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY")
)
```

## Trace Workflow Nodes

```python
@observe(name="supervisor_node")
def supervisor_node(state: AnalysisState) -> AnalysisState:
    """Traced supervisor node."""
    completed = set(state["agents_completed"])
    available = [a for a in ALL_AGENTS if a not in completed]
    next_agent = available[0] if available else "quality_gate"

    # Log routing decision to Langfuse
    langfuse_context.update_current_observation(
        output={"next": next_agent},
        metadata={
            "completed_count": len(completed),
            "remaining_count": len(available)
        }
    )

    return {"next": next_agent}
```

## Trace Full Workflow

```python
@observe(name="content_analysis")
async def analyze_content(url: str) -> AnalysisResult:
    """Traced end-to-end workflow."""

    # Trace metadata
    langfuse_context.update_current_trace(
        name="content_analysis",
        user_id="system",
        metadata={"url": url, "workflow": "8-agent-supervisor"}
    )

    # Child spans
    with langfuse_context.observe(name="fetch_content") as span:
        content = await fetch_url(url)
        span.metadata = {"content_size": len(content)}

    with langfuse_context.observe(name="generate_embedding") as span:
        embedding = await embed_text(content)
        span.usage = {"input_tokens": len(content) // 4, "model": "voyage-code-2"}

    findings = await run_supervisor_workflow(content)

    return AnalysisResult(findings=findings)
```

## Track LLM Costs

```python
@observe(name="llm_call")
async def call_llm(prompt: str, model: str) -> str:
    response = await anthropic.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024
    )

    # Log usage for cost tracking
    langfuse_context.update_current_observation(
        usage={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": model
        }
    )

    return response.content[0].text
```

## Agent-Level Tracing

```python
@observe(name="agent")
def create_traced_agent(agent_name: str):
    """Create a traced agent node."""

    @observe(name=agent_name)
    async def agent_node(state: AnalysisState) -> AnalysisState:
        langfuse_context.update_current_observation(
            metadata={
                "agent": agent_name,
                "analysis_id": state["analysis_id"]
            }
        )

        findings = await run_agent(agent_name, state["content"])

        langfuse_context.update_current_observation(
            output={"finding_count": len(findings)},
            usage={"total_tokens": sum(f.token_count for f in findings)}
        )

        return {"findings": findings}

    return agent_node
```

## Langfuse Dashboard Views

- **Trace waterfall**: See parallel agent execution
- **Token usage by agent**: Which agents use most tokens
- **Cost tracking per analysis**: Total cost breakdown
- **Latency breakdown**: Time spent in each node
- **Prompt/completion inspection**: Debug LLM calls

## Best Practices

- **`@observe()` on nodes**: Every workflow node should be traced
- **Track usage**: Log input/output tokens for cost analysis
- **Metadata**: Include analysis_id, agent_name for filtering
- **Child spans**: Use `with langfuse_context.observe()` for sub-operations
- **Error tracking**: Langfuse captures exceptions automatically

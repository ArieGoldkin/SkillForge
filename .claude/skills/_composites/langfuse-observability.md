---
name: langfuse-observability
description: Complete LLM observability with Langfuse
version: 1.0.0
type: composite
includes:
  - ai-llm/langfuse-tracing
  - ai-llm/langfuse-cost
  - ai-llm/langfuse-prompts
  - ai-llm/langfuse-evaluation
  - ai-llm/langfuse-sessions
  - ai-llm/langgraph-langfuse
trigger: "**/langfuse/**/*.py"
---

# Langfuse Observability

Complete guide for LLM observability with self-hosted Langfuse.

## When to Use

- Setting up LLM observability from scratch
- Debugging slow or incorrect LLM responses
- Tracking token usage and costs
- Managing prompts in production
- Evaluating LLM output quality

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    LANGFUSE OBSERVABILITY                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │  TRACING    │────▶│    COST     │────▶│  EVALUATION │    │
│  │  @observe   │     │   tokens    │     │   scores    │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│         │                                       │           │
│         ▼                                       ▼           │
│  ┌─────────────┐                        ┌─────────────┐    │
│  │   PROMPTS   │                        │  SESSIONS   │    │
│  │  versioning │                        │  analytics  │    │
│  └─────────────┘                        └─────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Included Skills

1. **langfuse-tracing** - @observe decorator, spans, nested traces
2. **langfuse-cost** - Token tracking, pricing, budget monitoring
3. **langfuse-prompts** - Prompt versioning, linking, A/B testing
4. **langfuse-evaluation** - Scores, quality metrics, datasets
5. **langfuse-sessions** - Session grouping, user analytics
6. **langgraph-langfuse** - LangGraph workflow integration

## Quick Start

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

langfuse = Langfuse()

@observe(name="content_analysis")
async def analyze_content(content: str, user_id: str) -> dict:
    # Set trace metadata
    langfuse_context.update_current_trace(
        user_id=user_id,
        session_id=f"session_{uuid4()}",
        metadata={"content_length": len(content)}
    )

    # Nested span for retrieval
    @observe(name="retrieval")
    async def retrieve():
        chunks = await vector_db.search(content)
        return chunks

    # Nested span for generation
    @observe(name="generation")
    async def generate(context):
        response = await llm.generate(prompt)
        langfuse_context.update_current_observation(
            model="claude-sonnet-4-20250514",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )
        return response

    context = await retrieve()
    result = await generate(context)

    # Score the result
    langfuse_context.score(name="quality", value=0.85)

    return result
```

## SkillForge Integration

```
backend/app/shared/services/langfuse/
├── client.py          # Langfuse client setup
├── prompt_manager.py  # Cached prompt fetching
└── tracing.py         # Workflow tracing utilities
```

## See Also

- [langfuse-tracing](../_atomic/ai-llm/langfuse-tracing.md)
- [langfuse-cost](../_atomic/ai-llm/langfuse-cost.md)
- [langfuse-prompts](../_atomic/ai-llm/langfuse-prompts.md)
- [langfuse-evaluation](../_atomic/ai-llm/langfuse-evaluation.md)
- [langfuse-sessions](../_atomic/ai-llm/langfuse-sessions.md)
- [langgraph-langfuse](../_atomic/ai-llm/langgraph-langfuse.md)

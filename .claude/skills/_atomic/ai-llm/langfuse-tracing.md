---
name: langfuse-tracing
description: Distributed tracing with @observe decorator and spans
version: 1.0.0
tags: [langfuse, tracing, observability, spans, decorators]
size: atomic
domain: ai-llm
---

# Langfuse Tracing

## Setup

```python
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host="https://cloud.langfuse.com"  # or self-hosted
)
```

## @observe Decorator

```python
@observe()  # Automatic tracing
async def analyze_content(content: str) -> dict:
    """Traced function - creates span automatically."""

    # Nested spans for sub-operations
    @observe(name="retrieval")
    async def retrieve_context():
        chunks = await vector_db.search(content)
        langfuse_context.update_current_observation(
            metadata={"chunks_retrieved": len(chunks)}
        )
        return chunks

    @observe(name="generation")
    async def generate_analysis(context):
        response = await llm.generate(prompt)
        langfuse_context.update_current_observation(
            input=content[:500],
            output=response[:500],
            model="claude-sonnet-4-20250514",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        )
        return response

    context = await retrieve_context()
    return await generate_analysis(context)
```

## Result in Langfuse UI

```
analyze_content (2.3s, $0.045)
├── retrieval (0.1s)
│   └── metadata: {chunks_retrieved: 5}
└── generation (2.2s, $0.045)
    └── model: claude-sonnet-4-20250514
    └── tokens: 1500 input, 1000 output
```

## Manual Span Creation

```python
# For non-decorated functions
with langfuse_context.observe(name="custom_operation") as span:
    result = perform_operation()
    span.metadata = {"result_size": len(result)}
```

## Trace Metadata

```python
@observe(name="workflow")
async def run_workflow(analysis_id: str):
    # Set trace-level metadata
    langfuse_context.update_current_trace(
        name="content_analysis",
        user_id="user_123",
        session_id=f"session_{analysis_id}",
        metadata={
            "analysis_id": analysis_id,
            "workflow": "8-agent-supervisor"
        },
        tags=["production", "skillforge"]
    )

    # ... workflow logic
```

## Best Practices

- **Decorate all async functions** that do I/O or LLM calls
- **Use nested @observe** for sub-operations
- **Log metadata** for filtering in UI
- **Set user_id and session_id** for analytics
- **Tag production vs staging** traces

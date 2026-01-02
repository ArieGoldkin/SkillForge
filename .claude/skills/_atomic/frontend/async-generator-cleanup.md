---
name: async-generator-cleanup
description: Python aclosing() for async generator resource cleanup
version: 1.0.0
tags: [python, async, streaming, cleanup]
size: atomic
domain: frontend
---

# Async Generator Cleanup

## The Problem

```python
# ❌ DANGEROUS: Generator not closed if exception occurs
async def stream_analysis():
    async for chunk in external_api_stream():
        yield process(chunk)  # May leak resources

# ❌ ALSO DANGEROUS: Manual close is error-prone
gen = stream_analysis()
try:
    async for chunk in gen:
        process(chunk)
finally:
    await gen.aclose()  # Easy to forget
```

## The Solution: `aclosing()`

```python
from contextlib import aclosing

# ✅ CORRECT: Guaranteed cleanup
async def stream_analysis():
    async with aclosing(external_api_stream()) as stream:
        async for chunk in stream:
            yield process(chunk)

# ✅ CORRECT: At consumption site
async def consume_stream():
    async with aclosing(stream_analysis()) as gen:
        async for chunk in gen:
            handle(chunk)
```

## LLM Streaming Example

```python
from contextlib import aclosing
from langchain_core.runnables import RunnableConfig

async def stream_llm_response(prompt: str, config: RunnableConfig | None = None):
    """Stream LLM tokens with guaranteed cleanup."""
    async with aclosing(llm.astream(prompt, config=config)) as stream:
        async for chunk in stream:
            yield chunk.content

# Consumption
async def generate_response(user_input: str):
    async with aclosing(stream_llm_response(user_input)) as response:
        async for token in response:
            yield token
```

## When to Use

| Scenario | Use aclosing() |
|----------|----------------|
| External API streaming | ✅ Always |
| Database streaming | ✅ Always |
| File streaming | ✅ Always |
| Simple in-memory generators | ⚠️ Optional |

## Anti-Patterns

```python
# ❌ NEVER: Consuming without aclosing
async for chunk in stream_analysis():
    process(chunk)

# ❌ NEVER: Assuming GC handles cleanup
gen = stream_analysis()
# gen goes out of scope without close
```

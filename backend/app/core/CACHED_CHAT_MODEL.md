# CachedChatModel - Transparent LLM Caching Wrapper

## Overview

`CachedChatModel` is a transparent wrapper for any LangChain chat model that adds automatic L1 (in-memory) caching on top of LangChain's built-in L2 (Redis semantic) caching. It maintains full compatibility with LangChain's `BaseChatModel` interface while providing significant performance improvements through intelligent caching.

## Features

- **Transparent caching**: Drop-in replacement for any LangChain chat model
- **Two-tier cache**: L1 (in-memory) + L2 (Redis semantic via LangChain)
- **Full LangChain compatibility**: Works with `with_structured_output()`, `with_fallbacks()`, LCEL chains
- **Graceful degradation**: Cache failures never block LLM calls
- **Deterministic cache keys**: SHA256 hash of message content + agent type
- **Automatic LRU eviction**: Prevents memory bloat (configurable size)

## Performance

| Metric | Target | Description |
|--------|--------|-------------|
| L1 cache hit | < 1ms | In-memory lookup |
| L2 cache hit | < 10ms | Redis semantic cache (via LangChain) |
| Cache miss overhead | < 5ms | Key generation + cache check |
| Memory usage | ~100KB/1K responses | L1 cache only |

## Expected Cache Hit Rates

- **Agent analysis**: 40-70% (similar content patterns)
- **Supervisor routing**: 60-80% (deterministic decisions)
- **Synthesis tasks**: 20-40% (more unique combinations)

## Usage

### Basic Usage

```python
from app.core.cached_chat_model import CachedChatModel
from app.core.model_factory import get_chat_model
from langchain_core.messages import HumanMessage

# Wrap any LangChain chat model
base_model = get_chat_model()
cached_model = CachedChatModel(
    model=base_model,
    agent_type="tech_explainer",  # For cache namespacing
    cache_enabled=True,
)

# Use like any LangChain model
response = await cached_model.ainvoke([HumanMessage(content="Explain FastAPI")])

# Second identical call hits L1 cache (< 1ms)
response = await cached_model.ainvoke([HumanMessage(content="Explain FastAPI")])
```

### With Structured Output

```python
from pydantic import BaseModel

class TechExplanation(BaseModel):
    topic: str
    summary: str
    key_points: list[str]

# Works seamlessly with structured output
structured_model = cached_model.with_structured_output(TechExplanation)
result = await structured_model.ainvoke([HumanMessage(content="Explain React")])
```

### With Fallbacks

```python
# Create fallback model chain
primary = CachedChatModel(model=get_chat_model(), agent_type="primary")
fallback = CachedChatModel(model=get_chat_model(task_type="supervisor"), agent_type="fallback")

# Apply fallback (works with caching on both models)
with_fallback = primary.with_fallbacks([fallback])
response = await with_fallback.ainvoke([HumanMessage(content="Hello")])
```

### In LCEL Chains

```python
from langchain_core.output_parsers import StrOutputParser

# Use in LCEL chains
chain = cached_model | StrOutputParser()
result = await chain.ainvoke([HumanMessage(content="Hello")])
```

### Disable Caching for Testing

```python
# Disable caching (useful for tests)
uncached_model = CachedChatModel(
    model=get_chat_model(),
    cache_enabled=False,  # Bypass cache
)
```

### Clear Cache

```python
# Clear L1 cache for a specific model instance
cached_model.clear_cache()
```

## Configuration

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `BaseChatModel` | (required) | The wrapped LangChain chat model |
| `agent_type` | `str` | `"default"` | Agent identifier for cache namespacing |
| `cache_enabled` | `bool` | `True` | Enable/disable caching |

### Cache Size

The L1 cache size is configured via a module constant:

```python
# In cached_chat_model.py
_L1_CACHE_SIZE = 100  # ~1MB total (10KB per entry)
```

To change: modify `_L1_CACHE_SIZE` in `/Users/yonatangross/coding/SkillForge/backend/app/core/cached_chat_model.py`.

## Cache Key Generation

Cache keys are deterministic SHA256 hashes of:

1. **Agent type** - for namespace isolation
2. **Message content** - serialized to JSON (sorted keys)

```python
# Example cache key generation
key = SHA256(
    agent_type + serialized_messages
)
# Result: "cached_model:tech_explainer:a1b2c3d4..."
```

**Note**: Temperature, max_tokens, and other model config are NOT included in the cache key. Only message content affects caching.

## L1 vs L2 Caching

### L1 Cache (This Module)
- **Storage**: In-memory dict per model instance
- **Hit latency**: < 1ms
- **Scope**: Single worker/process
- **Eviction**: LRU (oldest entries removed when full)
- **Size**: 100 entries (configurable)

### L2 Cache (LangChain Built-in)
- **Storage**: Redis with vector similarity
- **Hit latency**: < 10ms
- **Scope**: Shared across all workers
- **Eviction**: TTL-based (default 24 hours)
- **Size**: Unlimited (limited by Redis memory)

The wrapper adds L1 on top of LangChain's existing L2 cache for faster local hits.

## Error Handling

All cache operations are wrapped in try-except blocks. Cache failures:

- **Log warnings** with structured logging
- **Continue without cache** (graceful degradation)
- **Never block LLM calls**

```python
# Example: Cache error doesn't prevent LLM call
result = await cached_model.ainvoke([HumanMessage(content="Hello")])
# If cache check fails → logged as warning → LLM called normally
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ CachedChatModel                                         │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Check L1 (in-memory)                          │  │
│  │    ├─ Hit? Return cached response (< 1ms)        │  │
│  │    └─ Miss? Continue to step 2                   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 2. Call wrapped model                            │  │
│  │    (LangChain L2 cache checks here automatically)│  │
│  │    └─ L2 Hit? Fast return (< 10ms)               │  │
│  │    └─ L2 Miss? Full LLM call (2-10 sec)          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 3. Store result in L1 cache                      │  │
│  │    (for next local call)                         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Testing

Run the comprehensive test suite:

```bash
poetry run pytest tests/unit/core/test_cached_chat_model.py -v
```

Test coverage:

- ✅ L1 cache hits and misses
- ✅ Cache key generation (deterministic)
- ✅ LRU eviction when full
- ✅ Graceful error handling
- ✅ LangChain compatibility (structured output, fallbacks, batching)
- ✅ Cache bypass mode
- ✅ Sync and async methods

## Integration with Existing Code

The wrapper is designed to be a drop-in replacement. To add caching to existing code:

```python
# Before
model = get_chat_model()
response = await model.ainvoke(messages)

# After (with caching)
from app.core.cached_chat_model import CachedChatModel

model = CachedChatModel(
    model=get_chat_model(),
    agent_type="my_agent",
)
response = await model.ainvoke(messages)  # Identical API
```

## Files

| File | Purpose |
|------|---------|
| `/Users/yonatangross/coding/SkillForge/backend/app/core/cached_chat_model.py` | Implementation |
| `/Users/yonatangross/coding/SkillForge/backend/tests/unit/core/test_cached_chat_model.py` | Tests (21 tests) |
| `/Users/yonatangross/coding/SkillForge/backend/app/core/CACHED_CHAT_MODEL.md` | This documentation |

## Future Enhancements

Potential improvements (not yet implemented):

1. **Custom L2 cache**: Direct Redis access instead of relying on LangChain's cache
2. **Cache statistics API**: Expose hit/miss rates, latency metrics
3. **Configurable cache size**: Runtime configuration via settings
4. **Cache warming**: Pre-populate cache with common queries
5. **Multi-level eviction**: Smarter eviction based on access frequency + recency

## License

Part of SkillForge project - see project LICENSE.

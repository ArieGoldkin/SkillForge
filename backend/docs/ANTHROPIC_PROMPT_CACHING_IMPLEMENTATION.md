# Anthropic Prompt Caching Implementation

## Overview

This document describes the implementation of Anthropic prompt caching in the SkillForge backend, which enables significant cost savings (up to 90% for cached content) and reduced latency for repeated system prompts.

## Implementation Details

### 1. Configuration (app/core/config.py)

Added `ANTHROPIC_PROMPT_CACHE_TTL` setting to control cache duration:

```python
ANTHROPIC_PROMPT_CACHE_TTL: str = Field(
    default="1h",
    description="TTL for Anthropic prompt caching: '5m' (default) or '1h' (extended)",
)
```

**Options:**
- `"5m"` - Default Anthropic ephemeral caching (5 minutes)
- `"1h"` - Extended caching with 1-hour TTL (requires beta header)

### 2. Model Factory (app/core/model_factory.py)

Modified `get_chat_model()` to use `ChatAnthropic` directly when provider is "anthropic":

**Key Changes:**
- Import `ChatAnthropic` from `langchain_anthropic`
- When provider is "anthropic", create `ChatAnthropic` instance directly instead of using `init_chat_model()`
- Add `betas=["extended-cache-ttl-2025-04-11"]` parameter when TTL is "1h"
- Log prompt cache status (enabled, TTL) for observability

**Code Structure:**
```python
if provider == "anthropic":
    # Determine cache configuration
    betas_list: list[str] | None = None
    if settings.ANTHROPIC_PROMPT_CACHE_TTL == "1h":
        betas_list = ["extended-cache-ttl-2025-04-11"]

    # Create ChatAnthropic with betas parameter
    anthropic_kwargs = {
        "model": model_identifier_to_use,
        "api_key": settings.ANTHROPIC_API_KEY,
        # ... other parameters
    }
    if betas_list:
        anthropic_kwargs["betas"] = betas_list

    return ChatAnthropic(**anthropic_kwargs)
```

### 3. Agent Base (app/domains/analysis/workflows/agents/base.py)

Modified agent creation to add `cache_control` to system prompts:

**Key Changes:**
- Import `SystemMessage` from `langchain_core.messages`
- Import `settings` to check provider and TTL
- Added `_create_system_message_with_cache_control()` helper function
- Updated `create_structured_agent()` to use the helper
- Updated `create_tool_enabled_agent()` to use the helper

**Helper Function:**
```python
def _create_system_message_with_cache_control(system_prompt: str) -> SystemMessage:
    """Create a SystemMessage with Anthropic prompt caching support."""
    provider = settings.resolved_llm_provider()
    if provider != "anthropic":
        return SystemMessage(content=system_prompt)

    # Determine cache_control based on TTL
    cache_control: dict[str, str] = {"type": "ephemeral"}
    if settings.ANTHROPIC_PROMPT_CACHE_TTL == "1h":
        cache_control["ttl"] = "1h"

    # Create message with cache_control in content block
    return SystemMessage(
        content=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": cache_control,
            }
        ]
    )
```

## How Anthropic Prompt Caching Works

### Cache Control Structure

For Anthropic models, the cache_control marker goes on content blocks:

```python
{
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": "You are an expert analyst...",
            "cache_control": {"type": "ephemeral"}  # or {"type": "ephemeral", "ttl": "1h"}
        }
    ]
}
```

### Pricing Impact

**Without Caching:**
- Input tokens: $0.003/1K tokens (Sonnet 3.5)
- Output tokens: $0.015/1K tokens

**With Caching:**
- Cache writes: $0.00375/1K tokens (25% markup)
- Cache reads: $0.0003/1K tokens (90% discount!)
- Output tokens: $0.015/1K tokens (unchanged)

**Example Savings:**
For a 2000-token system prompt called 10 times:
- Without cache: 10 × 2000 × $0.003 = $0.060
- With cache: (1 × 2000 × $0.00375) + (9 × 2000 × $0.0003) = $0.0129
- **Savings: 78.5%**

### Cache Behavior

- **5-minute TTL:** Default Anthropic caching, no beta header needed
- **1-hour TTL:** Extended caching, requires beta header `extended-cache-ttl-2025-04-11`
- Cache key includes: model, exact prompt text, temperature, and other parameters
- Cache invalidates automatically after TTL expires
- Separate caches for different models (e.g., Sonnet vs Haiku)

## Usage

### Environment Configuration

Add to `.env` or `.env.test`:

```bash
# Use 1-hour cache (recommended for production)
ANTHROPIC_PROMPT_CACHE_TTL="1h"

# Or use 5-minute cache (default)
ANTHROPIC_PROMPT_CACHE_TTL="5m"
```

### Logging

When prompt caching is enabled, you'll see logs like:

```
chat_model_initializing provider=anthropic prompt_cache_enabled=True prompt_cache_ttl=1h
system_prompt_cache_control_enabled cache_type=ephemeral ttl=1h
```

## Non-Anthropic Providers

For non-Anthropic providers (OpenAI, Google, etc.):
- No cache_control is added to system messages
- Standard LangChain message format is used
- No beta headers are sent
- Behavior is unchanged from previous implementation

## Testing

The implementation includes:
- Type checking with mypy/ty
- Linting with ruff
- Provider detection handles all edge cases
- Graceful fallback for non-Anthropic models

## References

- [Anthropic Prompt Caching Documentation](https://docs.anthropic.com/en/docs/prompt-caching)
- [LangChain ChatAnthropic](https://python.langchain.com/docs/integrations/chat/anthropic/)
- [LangChain Messages API](https://python.langchain.com/docs/modules/model_io/chat/message_types/)

## Future Enhancements

Potential improvements:
1. Add metrics tracking for cache hit rates
2. Add cache warming strategy for common prompts
3. Support for caching tool definitions (future Anthropic feature)
4. Add budget monitoring for cache writes
5. Support for fine-grained cache control per agent type

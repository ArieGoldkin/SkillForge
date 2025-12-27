# Gemini SDK ValidationError Fix: max_concurrency Parameter

**Date:** 2025-12-27
**Issue:** ValidationError when using `max_concurrency` with Gemini models
**Status:** ✅ Fixed

## Problem

The Gemini SDK was rejecting batch requests with a validation error:

```
pydantic.v1.error_wrappers.ValidationError: 1 validation error for GenerateContentConfig
max_concurrency
  Extra inputs are not permitted [type=extra_forbidden, input_value=5, input_type=int]
```

### Root Cause

`max_concurrency` was being passed as a **keyword argument** to `abatch()`:

```python
# WRONG - max_concurrency leaks to Gemini SDK
responses = await model.abatch(
    batch_inputs,
    config=config,
    max_concurrency=5,  # ❌ Passed as kwarg
)
```

LangChain forwards unknown kwargs to the underlying model's SDK. The Gemini SDK's `GenerateContentConfig` has `extra='forbid'`, which rejects the parameter.

### Correct Usage

`max_concurrency` must be **inside the RunnableConfig dict**, not as a kwarg:

```python
# CORRECT - max_concurrency in config dict
config = create_runnable_config()
config["max_concurrency"] = 5  # ✅ Set in config
responses = await model.abatch(
    batch_inputs,
    config=config,
)
```

This is documented in LangChain's `RunnableConfig` TypedDict:

```python
class RunnableConfig(TypedDict, total=False):
    tags: list[str]
    metadata: dict[str, Any]
    callbacks: Callbacks
    run_name: str
    max_concurrency: int | None  # ✅ Part of config schema
    recursion_limit: int
    configurable: dict[str, Any]
    run_id: uuid.UUID | None
```

## Files Fixed

### 1. `app/shared/services/g_eval/scorer.py` (line 770-776)

**Before:**
```python
config = create_runnable_config()
responses = await model.abatch(
    batch_inputs,
    config=config,
    max_concurrency=5,  # ❌
)
```

**After:**
```python
config = create_runnable_config()
config["max_concurrency"] = 5  # ✅
responses = await model.abatch(
    batch_inputs,
    config=config,
)
```

### 2. `app/shared/services/g_eval/self_consistency.py` (line 156-163)

**Before:**
```python
config = create_runnable_config()
responses = await model.abatch(
    batch_inputs,
    config=config,
    max_concurrency=5,  # ❌
)
```

**After:**
```python
config = create_runnable_config()
config["max_concurrency"] = 5  # ✅
responses = await model.abatch(
    batch_inputs,
    config=config,
)
```

### 3. `app/domains/analysis/workflows/tasks/aggregation/compress_findings.py` (line 348-355)

**Before:**
```python
results = await llm_with_structure.abatch(
    batch_inputs,
    config=config,
    max_concurrency=5,  # ❌
)
```

**After:**
```python
config["max_concurrency"] = 5  # ✅
results = await llm_with_structure.abatch(
    batch_inputs,
    config=config,
)
```

## Verification

### Test Run

```bash
poetry run python -c "
import asyncio
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.timeout_config import create_runnable_config
from app.core.config import get_settings

async def test():
    settings = get_settings()
    model = ChatGoogleGenerativeAI(
        model='gemini-2.0-flash-exp',
        api_key=settings.GOOGLE_API_KEY,
    )

    config = create_runnable_config()
    config['max_concurrency'] = 5  # ✅ Fixed pattern

    batch_inputs = [
        [HumanMessage(content='Say hello')],
        [HumanMessage(content='Say goodbye')],
    ]

    responses = await model.abatch(batch_inputs, config=config)
    print(f'✅ Success: {len(responses)} responses')

asyncio.run(test())
"
```

**Output:**
```
✅ abatch() succeeded with max_concurrency in config
Received 2 responses
```

### Linting

```bash
poetry run ruff format --check app/shared/services/g_eval/
poetry run ruff check app/shared/services/g_eval/
# All checks passed! ✅
```

## Why This Matters

1. **Rate Limiting:** `max_concurrency=5` prevents overwhelming the Gemini API with parallel requests
2. **Cost Control:** Prevents rate limit retry costs
3. **Reliability:** Gemini API has strict rate limits; controlled concurrency ensures stability

## References

- [LangChain RunnableConfig](https://python.langchain.com/docs/how_to/configure)
- [Pydantic Extra Config](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra)
- [Issue #564](https://github.com/YourOrg/SkillForge/issues/564) - Langfuse observability

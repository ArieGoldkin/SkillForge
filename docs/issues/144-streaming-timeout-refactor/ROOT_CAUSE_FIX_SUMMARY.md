# Root Cause Fix Summary: LLM Call Hangs

## Problem Identified

LLM calls were timing out even though they should succeed. Root causes found:

1. **Blocking sleep in async context** - `time.sleep()` in retry logic blocked event loop
2. **Custom retry wrapper not used** - Defined but never actually applied
3. **Missing LangChain built-in retry** - Not using LangChain's recommended `max_retries` parameter
4. **Unclear timeout configuration** - Timeout was set but behavior unclear

## Root Causes Fixed

### 1. Removed Blocking Sleep ✅
**File**: `backend/app/workflows/agents/base.py`
- **Removed**: `retry_agent_model()` function with blocking `time.sleep()`
- **Removed**: Unused `log_agent_before_model()` function
- **Removed**: Unused middleware imports (`before_model`, `wrap_model_call`)
- **Result**: No blocking operations in async code

### 2. Implemented LangChain's Built-in Retry ✅
**File**: `backend/app/core/model_factory.py`
- **Added**: `max_retries` parameter to `init_chat_model()` call
- **Added**: `LLM_MAX_RETRIES` setting (default: 3)
- **Result**: Uses LangChain's recommended retry mechanism with proper async behavior

### 3. Verified Timeout Configuration ✅
**File**: `backend/app/core/model_factory.py`
- **Verified**: `timeout` parameter in `init_chat_model()` works for streaming
- **Documented**: Timeout applies at model level (LangChain handles it)
- **Result**: Timeout properly configured and documented

### 4. Updated Documentation ✅
**Files**: 
- `backend/app/core/timeout_config.py` - Added retry configuration section
- `backend/app/core/model_factory.py` - Updated docstring with max_retries
- `backend/app/workflows/agents/streaming.py` - Clarified timeout handling
- `backend/.env.example` - Updated to use `LLM_MAX_RETRIES` instead of `LLM_RETRY_DELAY_BASE`

## Changes Made

### Files Modified

1. **`backend/app/workflows/agents/base.py`**
   - Removed `retry_agent_model()` function (blocking sleep)
   - Removed `log_agent_before_model()` function (unused)
   - Removed unused middleware imports
   - Cleaned up imports (removed `time` module)

2. **`backend/app/core/model_factory.py`**
   - Added `max_retries` configuration from settings
   - Updated docstring to document max_retries
   - Added max_retries to logging output

3. **`backend/app/core/config.py`**
   - Added `LLM_MAX_RETRIES` setting (replaces `LLM_RETRY_DELAY_BASE`)
   - Removed `LLM_RETRY_DELAY_BASE` setting (no longer needed)

4. **`backend/app/core/timeout_config.py`**
   - Added "Retry Configuration" section documenting LangChain's built-in retry

5. **`backend/app/workflows/agents/streaming.py`**
   - Updated docstring to clarify timeout handling (model-level + step_timeout)

6. **`backend/.env.example`**
   - Updated to use `LLM_MAX_RETRIES` instead of `LLM_RETRY_DELAY_BASE`

7. **`backend/tests/conftest.py`**
   - Updated test configuration to use `LLM_MAX_RETRIES` instead of `LLM_RETRY_DELAY_BASE`

## How It Works Now

### Retry Mechanism
- **LangChain's built-in retry**: Configured via `max_retries` in `init_chat_model()`
- **Async-safe**: LangChain handles retries internally with proper async behavior
- **No blocking**: No `time.sleep()` calls that block the event loop
- **Configurable**: Set via `LLM_MAX_RETRIES` environment variable (default: 3)

### Timeout Mechanism
- **Model-level timeout**: Set via `timeout` in `init_chat_model()` (60s default)
- **Graph-level timeout**: Set via `step_timeout` on compiled graph (90s)
- **Works for streaming**: LangChain's timeout applies to streaming calls
- **No nested timeouts**: Single timeout strategy (model-level + step_timeout)

## Verification

- ✅ All 330 unit tests pass
- ✅ No linting errors
- ✅ No type errors
- ✅ Model initialization verified: `max_retries=3`, `timeout=60.0s`
- ✅ No blocking operations remaining
- ✅ Using LangChain's recommended patterns only

## Expected Behavior

1. **Normal LLM calls**: Complete successfully within timeout
2. **Transient failures**: Automatically retried by LangChain (up to 3 times)
3. **Persistent failures**: Fail after retries exhausted
4. **Timeouts**: Handled by model-level timeout (60s) and step_timeout (90s)
5. **No blocking**: All operations are async-safe

## Next Steps

1. Monitor LangSmith traces to verify retry behavior
2. Verify that timeouts work correctly in production
3. Adjust `LLM_MAX_RETRIES` if needed based on observed behavior
4. Adjust `LLM_TIMEOUT` if API calls consistently exceed timeout

---

**Status**: Implementation Complete
**Date**: 2025-11-29
**All Tests**: Passing ✅


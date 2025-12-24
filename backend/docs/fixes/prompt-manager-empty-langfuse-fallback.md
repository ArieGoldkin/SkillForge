# Fix: Prompt Manager Empty Langfuse Fallback

**Date**: 2024-12-24
**Issue**: Integration test `test_full_cache_flow` failing due to empty Langfuse prompts
**Status**: ✅ Fixed

## Problem

The `test_full_cache_flow` integration test was failing with:
```
AssertionError: assert 0 > 0
  where 0 = len('')
```

### Root Cause

The PromptManager had a logic bug in the Langfuse fetching flow:

```python
# BEFORE (buggy code)
prompt_obj = await self._fetch_from_langfuse(name, label)
if prompt_obj:
    prompt_content = prompt_obj["prompt"]
    # Cache and return even if prompt_content is empty!
    await self._cache_prompt(name, label, prompt_content)
    return self._compile_prompt(prompt_content, variables)
```

**The issue**: Even when Langfuse returned an empty string `""`, the code treated it as valid and:
1. Cached the empty string
2. Attempted to compile it with variables
3. Never fell back to hardcoded prompts

This meant the system would return empty prompts instead of using the hardcoded fallbacks.

## Solution

### 1. Fix PromptManager Logic

Added validation to check if Langfuse prompt has actual content before using it:

```python
# AFTER (fixed code)
prompt_obj = await self._fetch_from_langfuse(name, label)
if prompt_obj:
    prompt_content = prompt_obj["prompt"]
    # Only use Langfuse prompt if it has content
    if prompt_content and prompt_content.strip():
        # Cache in both L1 and L2
        await self._cache_prompt(name, label, prompt_content)
        return self._compile_prompt(prompt_content, variables)

    logger.warning(
        "prompt_langfuse_empty",
        name=name,
        label=label,
        message="Langfuse prompt is empty, falling back to hardcoded",
    )

# Fallback: Hardcoded prompts (now properly reached when Langfuse is empty)
hardcoded_prompt = self._get_hardcoded_prompt(name)
if hardcoded_prompt:
    return self._compile_prompt(hardcoded_prompt, variables)
```

**Changes**:
- Check `if prompt_content and prompt_content.strip():` before using Langfuse prompt
- Log warning when Langfuse prompt is empty
- Fall through to hardcoded fallback when Langfuse is empty

**File**: `/Users/yonatangross/coding/SkillForge/backend/app/shared/services/prompts/prompt_manager.py:1390-1405`

### 2. Fix Integration Test

Updated the test to be more defensive and verify the cache flow regardless of Langfuse content:

```python
# BEFORE (failing test)
result1 = await manager.get_prompt(
    name=prompt_name,
    variables={},  # Empty variables caused KeyError on hardcoded fallback
    label="production",
)

# AFTER (robust test)
test_variables = {"agent_list": "- test_agent_1\n- test_agent_2"}
result1 = await manager.get_prompt(
    name=prompt_name,
    variables=test_variables,  # Provide required variables
    label="production",
)
```

**Changes**:
- Provide required variables (`agent_list` for routing prompt)
- Added comprehensive docstring explaining test behavior
- Verify cache consistency across L1, L2, and hardcoded sources
- Check that `prompt_source` is either `"langfuse"` or `"hardcoded"`

**File**: `/Users/yonatangross/coding/SkillForge/backend/tests/unit/shared/services/prompts/test_prompt_manager.py:406-506`

## Test Results

### Before Fix
```
FAILED tests/unit/shared/services/prompts/test_prompt_manager.py::TestPromptManagerIntegration::test_full_cache_flow
AssertionError: assert 0 > 0
  where 0 = len('')
```

### After Fix
```
PASSED tests/unit/shared/services/prompts/test_prompt_manager.py::TestPromptManagerIntegration::test_full_cache_flow
24 passed in 4.96s
```

All 24 tests in the test suite pass, including:
- L1/L2 cache hit/miss scenarios
- Langfuse fetch success/failure
- Hardcoded fallback
- Variable compilation
- Integration tests with live Redis/Langfuse

## Cache Flow Verification

The test now properly verifies the multi-level caching strategy:

1. **First call** (L1 miss, L2 miss):
   - Fetches from Langfuse
   - If Langfuse is empty → falls back to hardcoded
   - Returns non-empty prompt

2. **Second call** (L1 hit):
   - Returns cached result from L1
   - Same result as first call

3. **Third call** (L1 cleared, L2 hit):
   - If Langfuse had content → L2 Redis cache hit
   - If Langfuse was empty → hardcoded (not cached)
   - Result consistent with first call

## Benefits

1. **Robustness**: System no longer breaks when Langfuse prompts are empty
2. **Graceful degradation**: Automatically falls back to hardcoded prompts
3. **Observability**: Logs warning when Langfuse is empty
4. **Test coverage**: Integration test verifies cache flow works in both scenarios

## Impact

- **Production**: No breaking changes, only improves robustness
- **Development**: Developers can now work with empty Langfuse instances
- **Testing**: Integration tests pass regardless of Langfuse state
- **Observability**: Clear warning logs when Langfuse prompts are empty

## Related Files

- `app/shared/services/prompts/prompt_manager.py` - Core logic fix
- `tests/unit/shared/services/prompts/test_prompt_manager.py` - Test improvements

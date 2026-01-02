# Brainstorm: Multiple Critical Issues

**Date**: 2025-01-01  
**Priority**: CRITICAL - Multiple blocking issues affecting user experience

## Issues Summary

1. **ZERO PROGRESS BUG** - Library shows 0% progress for all analyses
2. **CODE BUG** - Missing `session` variable causing test failures
3. **HIGH FAILURE RATE** - Many analyses failing
4. **STUCK ANALYSES** - Many analyses stuck in "pending" with null titles
5. **TEST FAILURES** - Tests failing due to actual code bugs

---

## Issue 1: Zero Progress Bug (CRITICAL)

### Problem
Library page shows 0% progress for all analyses, even when they're running or completed.

### Root Cause
**File**: `frontend/src/features/library/hooks/useLibrarySkills.ts:72`

```typescript
progress: isFailed ? undefined : 0,  // ❌ HARDCODED TO 0!
```

This hardcodes progress to 0 for all non-failed analyses. The progress should be calculated based on:
- Analysis status (complete = 100%, running = calculate from stages)
- Stage completion counts
- SSE progress data

### Impact
- **User Experience**: Users see no progress indication
- **Trust**: Appears broken/incomplete
- **Functionality**: Can't track analysis progress from library

### Solution
Calculate progress from:
1. `analysis.status === 'complete'` → 100%
2. `analysis.status === 'analyzing'` → Calculate from stage data or use estimated progress
3. Check if API provides progress data
4. Fallback to estimated progress based on status

**Reference**: `frontend/src/features/library/hooks/useSkillsData.ts` has better logic:
```typescript
progress: analysis.status === 'complete' ? 100 : 65,
```

### Files to Fix
- `frontend/src/features/library/hooks/useLibrarySkills.ts` - Fix progress calculation
- `backend/app/api/v1/analysis/library.py` - Potentially add progress data to API response

---

## Issue 2: Missing Session Variable (CODE BUG)

### Problem
Test failure: `NameError: name 'session' is not defined`

**Location**: `backend/app/api/v1/analysis/library.py:158`

```python
search_service = SearchService(session, embedding_service)  # ❌ 'session' not defined
```

### Root Cause
The function uses `db: Annotated[AsyncSession, Depends(get_db)]` at line 391, but the variable name is `db`, not `session`. The code at line 158 tries to use `session` which doesn't exist in scope.

### Impact
- **Test Failures**: Tests fail with NameError
- **Production**: Hybrid/semantic search will fail if this code path executes
- **Search Functionality**: Broken for semantic/hybrid modes

### Solution
Change line 158 from:
```python
search_service = SearchService(session, embedding_service)
```

To:
```python
search_service = SearchService(db, embedding_service)
```

### Files to Fix
- `backend/app/api/v1/analysis/library.py:158` - Use `db` instead of `session`

---

## Issue 3: High Failure Rate

### Problem
Many analyses are failing. From the UI screenshot:
- 9 failed stages out of 30 total
- Multiple agent groups showing failures
- Circuit breaker opened causing cascading failures

### Root Causes

1. **Circuit Breaker Opens**:
   - After 5+ agent failures, circuit breaker opens
   - All subsequent LLM calls fail immediately
   - Cascades to more failures

2. **Agent Failures**:
   - Multiple agents failing (Tech Comparison, Trends Analysis, Key Insights, etc.)
   - Failure reasons need investigation:
     - LLM API errors?
     - Timeout issues?
     - Content extraction problems?
     - Validation failures?

3. **No Graceful Degradation**:
   - When circuit breaker opens, agents don't handle it gracefully
   - Should use fallbacks or skip non-critical agents

### Impact
- **User Experience**: Users see many failed analyses
- **Success Rate**: Low analysis completion rate
- **Trust**: Appears unreliable

### Investigation Needed
1. Check logs for actual failure reasons
2. Verify circuit breaker recovery time
3. Check if agents handle circuit breaker errors
4. Verify our recent circuit breaker fix in aggregation is working

### Solutions

**Short Term**:
- Verify circuit breaker fix is deployed
- Check agent error handling
- Add better error messages

**Long Term**:
- Improve agent resilience (retries, fallbacks)
- Better circuit breaker recovery
- Graceful degradation (skip non-critical agents)
- Better error reporting to users

---

## Issue 4: Stuck Analyses (Pending Status)

### Problem
Many analyses stuck in "pending" status with null titles:
- `status: "pending"`
- `title: null`

### Root Causes

1. **Workflow Not Starting**:
   - Background task not starting
   - Workflow initialization failing
   - Error handling swallowing errors

2. **Title Not Persisted**:
   - We tried to fix this before
   - Title from extraction_metadata not saving to analysis.title
   - Frontend fallback might not be working

### Impact
- **Library Display**: Shows "Untitled" analyses
- **User Confusion**: Can't identify analyses
- **Data Quality**: Poor user experience

### Investigation Needed
1. Check if workflow tasks are starting
2. Check error logs for workflow startup failures
3. Verify title persistence fix is working
4. Check frontend fallback logic

### Solutions
1. Verify workflow startup error handling
2. Ensure title persistence works
3. Add better frontend fallback for missing titles
4. Clean up stuck pending analyses

---

## Issue 5: Test Failures

### Problem
Tests are failing due to actual code bugs (not test issues).

### Failures
1. `test_hybrid_search_success` - NameError: name 'session' is not defined
2. Potentially more tests failing due to code bugs

### Impact
- **Development Velocity**: Blocked on fixing bugs
- **CI/CD**: Tests don't pass
- **Code Quality**: Bugs in production code

### Solution
1. Fix code bugs (Issue 2)
2. Re-run tests
3. Fix any additional bugs found

---

## Priority Fix Order

1. **IMMEDIATE** (Blocking):
   - Fix `session` → `db` bug (Issue 2)
   - Fix zero progress bug (Issue 1)

2. **HIGH** (User Impact):
   - Investigate high failure rate (Issue 3)
   - Fix stuck pending analyses (Issue 4)

3. **MEDIUM** (Quality):
   - Fix test failures (Issue 5)
   - Improve error handling

---

## Next Steps

1. Fix the two code bugs immediately
2. Run full test suite with logs
3. Investigate failure patterns
4. Implement fixes for progress and pending analyses
5. Verify circuit breaker fixes are working

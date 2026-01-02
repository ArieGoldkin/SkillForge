# Brainstorm: Multiple Critical Issues - Root Cause Analysis

**Date:** January 1, 2026  
**Status:** 🔴 CRITICAL - Multiple system failures affecting user experience

---

## 📋 Executive Summary

Three critical issues identified:
1. **Zero Progress in Library** - Frontend hardcodes progress to 0
2. **Many Agent Failures** - Circuit breaker opens causing 9/30 agents to fail
3. **103 Tests Failing** - 44 failures + 59 errors, blocking development

---

## 🔍 Root Cause Analysis

### Issue 1: Zero Progress in Library (FRONTEND BUG)

**Symptoms:**
- Library page shows "0%" progress for all in-progress analyses
- No visual indication of actual analysis progress
- Users can't see which analyses are actually progressing

**Root Cause:**
```typescript
// frontend/src/features/library/hooks/useLibrarySkills.ts:72
progress: isFailed ? undefined : 0,  // ❌ HARDCODED TO 0!
```

**Why This Happened:**
- Progress calculation never implemented for library view
- Backend library endpoint doesn't return progress data
- Frontend defaults to 0 instead of calculating from analysis status

**Impact:**
- Poor UX - users think analyses are stuck
- Can't distinguish between pending and actively running analyses
- Library page shows no useful progress information

**Solution:**
1. Calculate progress from analysis status and stage information
2. Option A: Query progress from SSE events/analysis status API
3. Option B: Add progress calculation to library endpoint
4. Update frontend to use calculated progress

---

### Issue 2: Library Hybrid Search Bug (BACKEND BUG)

**Symptoms:**
- Test failure: `test_hybrid_search_success` fails
- Error: `name 'session' is not defined`
- Hybrid search falls back to fulltext search

**Root Cause:**
```python
# backend/app/api/v1/analysis/library.py:158
search_service = SearchService(session, embedding_service)  # ❌ 'session' not defined!
```

**Why This Happened:**
- Function parameter doesn't include `session: AsyncSession`
- `SearchService` requires a session but it's not injected
- Code tries to use `session` variable that doesn't exist

**Impact:**
- Hybrid search doesn't work (falls back to fulltext)
- Tests fail
- Reduced search quality (no vector search)

**Solution:**
1. Add `session: Annotated[AsyncSession, Depends(get_db)]` parameter
2. Pass session to `SearchService` constructor
3. Fix test mocks to provide session

---

### Issue 3: Many Agent Failures (CIRCUIT BREAKER)

**Symptoms:**
- 9 out of 30 agents failing in analysis
- Circuit breaker "llm_api" is OPEN
- Error: "Circuit breaker 'llm_api' is OPEN. Retry after 60.0s"

**Root Cause:**
1. **Initial Failure Cascade:**
   - Multiple agents fail (likely due to LLM API issues)
   - After 5 failures, circuit breaker opens
   - All subsequent LLM calls fail fast

2. **Circuit Breaker State:**
   - Stays OPEN for 60 seconds (timeout)
   - Auto-recovery attempts to HALF_OPEN after timeout
   - If failures continue, stays OPEN

3. **We Fixed Aggregation:**
   - Aggregation now checks circuit breaker before synthesis
   - But agents still fail because they don't check circuit breaker

**Impact:**
- 30% failure rate (9/30 agents)
- Analysis marked "Complete with Errors"
- Poor quality artifacts (missing agent insights)

**Solution:**
1. **Immediate:** Check circuit breaker state before agent execution
2. **Short-term:** Add graceful degradation when circuit breaker open
3. **Long-term:** Investigate why so many initial failures (LLM API issues?)

---

### Issue 4: 103 Tests Failing (TEST INFRASTRUCTURE)

**Breakdown:**
- **44 FAILED** - Assertions fail or exceptions raised
- **59 ERRORS** - Setup/teardown failures, missing dependencies

**Categories:**

1. **Library Tests (10 failures):**
   - `test_hybrid_search_*` - All failing due to 'session' bug
   - `test_semantic_search_*` - Similar issues
   - `test_default_search_mode` - Assertion failures

2. **Integration Tests (15 failures):**
   - `test_workflow_status_updates_to_complete` - Status tracking issues
   - `test_full_workflow_e2e` - End-to-end workflow failures
   - `test_ollama_integration` - Ollama provider issues

3. **Component Tests (3 failures):**
   - `test_context_engineering_*` - Memory/context issues

4. **Smoke Tests (40+ errors):**
   - Retrieval/search tests - All ERROR state (not failed)
   - Likely database/environment setup issues

5. **Performance Tests (8 failures):**
   - Concurrent execution failures
   - Timeout issues

**Root Causes:**
1. **Library 'session' bug** - Causes all library search tests to fail
2. **Database state** - Tests not properly isolated
3. **Circuit breaker state** - Tests affected by OPEN circuit breaker
4. **Ollama configuration** - Integration tests assume Ollama running
5. **Test data pollution** - Previous test runs affecting current tests

**Impact:**
- Development velocity blocked
- Can't confidently refactor
- CI/CD pipeline likely failing

**Solution:**
1. Fix library 'session' bug (fixes 10+ tests immediately)
2. Reset circuit breaker in test fixtures
3. Add proper test isolation
4. Fix Ollama integration test setup
5. Investigate smoke test errors (environment issues?)

---

## 🎯 Priority Ranking

### P0 - Critical (Fix Now)
1. **Library 'session' bug** - Blocks 10+ tests, breaks hybrid search
2. **Zero progress display** - Poor UX, users confused

### P1 - High (Fix Today)
3. **Circuit breaker causing agent failures** - 30% failure rate
4. **Test infrastructure** - Fix library tests, then systematic review

### P2 - Medium (Fix This Week)
5. **Remaining test failures** - Systematic fix after P0/P1 resolved
6. **Progress calculation** - Better UX enhancement

---

## 📝 Implementation Plan

### Phase 1: Quick Wins (1-2 hours)

#### Fix 1: Library 'session' Bug
```python
# backend/app/api/v1/analysis/library.py
async def get_library(
    repo: Annotated[ILibraryRepository, Depends(get_library_repository)],
    db: Annotated[AsyncSession, Depends(get_db)],  # ✅ ADD THIS
    # ... rest of parameters
):
    # ... in hybrid search block:
    search_service = SearchService(db, embedding_service)  # ✅ Use 'db' not 'session'
```

#### Fix 2: Zero Progress - Quick Calculation
```typescript
// frontend/src/features/library/hooks/useLibrarySkills.ts
function calculateProgress(status: AnalysisStatus): number | undefined {
  switch (status) {
    case 'pending': return 0
    case 'running': return 50  // Estimate - could be improved
    case 'complete': return 100
    case 'failed': return undefined
    default: return 0
  }
}

// In transformItemToSkill:
progress: isFailed ? undefined : calculateProgress(item.status),
```

**Result:** 
- Hybrid search works
- 10+ tests pass
- Progress shows (even if estimated)

---

### Phase 2: Circuit Breaker Resilience (2-3 hours)

#### Fix 3: Check Circuit Breaker Before Agent Execution
```python
# backend/app/domains/analysis/workflows/agents/execution.py
async def _execute_agent_retry_loop(...):
    # Check circuit breaker BEFORE attempting LLM call
    from app.core.resilience import get_resilience_manager
    resilience_manager = get_resilience_manager()
    circuit_breaker = resilience_manager.get_circuit_breaker("llm_api")
    
    if circuit_breaker.is_open:
        logger.warning(
            "agent_skipped_circuit_breaker_open",
            agent_type=params.agent_type,
            analysis_id=str(params.analysis_id),
        )
        return AgentExecutionResult(
            agent_type=params.agent_type,
            status=AgentStatus.SKIPPED,
            findings={},
            error="Circuit breaker OPEN - agent skipped",
        )
    
    # Proceed with normal execution...
```

**Result:**
- Agents skip gracefully when circuit breaker open
- No wasted LLM calls
- Better error messages

---

### Phase 3: Proper Progress Calculation (4-6 hours)

#### Option A: Query Analysis Status for Progress
```typescript
// Frontend: Query analysis status API for running analyses
const { data: status } = useQuery({
  queryKey: ['analysis-status', analysisId],
  queryFn: () => analyzeAPI.getAnalysisStatus(analysisId),
  enabled: status === 'running',
  refetchInterval: 5000, // Poll every 5 seconds
})

// Calculate progress from status/stage information
const progress = calculateProgressFromStatus(status)
```

#### Option B: Add Progress to Library Endpoint
```python
# Backend: Calculate progress when listing analyses
progress_percent = calculate_progress_from_agent_findings(analysis_id)
# Add to LibrarySearchResult schema
```

**Recommendation:** Option A (frontend polling) - simpler, doesn't require backend changes

---

### Phase 4: Test Infrastructure (1-2 days)

#### Systematic Test Fixes:

1. **Library Tests** (10 tests):
   - Fix 'session' bug → all pass

2. **Circuit Breaker Tests**:
   - Add circuit breaker reset in test fixtures
   - Ensure tests don't affect each other

3. **Ollama Integration Tests**:
   - Check if Ollama is running before tests
   - Skip tests if Ollama not available

4. **Smoke Tests** (40+ errors):
   - Investigate environment setup
   - Check database connectivity
   - Verify embeddings service

5. **Integration Tests**:
   - Add proper test isolation
   - Reset database state between tests
   - Fix workflow status tracking tests

---

## 🚨 Critical Questions

1. **Why are agents failing initially?**
   - LLM API issues?
   - Network problems?
   - Rate limiting?
   - Timeout issues?

2. **Why doesn't circuit breaker recover?**
   - Continuous failures preventing recovery?
   - Timeout too long (60s)?
   - Need manual reset?

3. **Should we have progress in library?**
   - Real-time updates (polling)?
   - Snapshot from last SSE event?
   - Estimated based on status?

4. **Test failure threshold?**
   - What's acceptable failure rate?
   - Which tests are critical vs nice-to-have?
   - Should smoke tests run in CI?

---

## ✅ Success Criteria

### Immediate (Today):
- [ ] Library 'session' bug fixed
- [ ] Zero progress shows estimated progress
- [ ] 10+ library tests passing

### Short-term (This Week):
- [ ] Circuit breaker checked before agents
- [ ] Agent failure rate < 10%
- [ ] All critical tests passing (< 20 failures)

### Long-term (This Sprint):
- [ ] Real progress calculation in library
- [ ] Test suite 95%+ passing
- [ ] Circuit breaker auto-recovery working

---

## 📊 Metrics to Track

1. **Agent Failure Rate:**
   - Target: < 5%
   - Current: 30% (9/30)

2. **Test Pass Rate:**
   - Target: > 95%
   - Current: ~95.5% (4967/5106, but 59 errors)

3. **Library Progress Accuracy:**
   - Target: Real progress for running analyses
   - Current: Always 0%

4. **Circuit Breaker Recovery:**
   - Target: Auto-recovery within 60s
   - Current: Unknown (needs monitoring)

---

## 🔗 Related Issues

- Issue #441: Error tracking for failed analyses (✅ partially implemented)
- Issue #489: SSE error reconciliation (✅ implemented)
- Issue #533: Circuit breaker for LLM API resilience (⚠️ needs improvement)
- Issue #606: Ollama integration (⚠️ tests failing)

---

**Next Steps:**
1. Implement Phase 1 fixes (quick wins)
2. Test circuit breaker behavior
3. Systematic test fixes
4. Monitor metrics after fixes

# Error Handling Standardization - Quick Reference

**Last Updated**: December 2025  
**Status**: Planning Phase

---

## 🎯 Core Principles

1. **All failures emit `type="error"` events** - Never use `type="progress"` with `status="failed"`
2. **All nodes check `should_abort` before executing** - Use `check_should_abort()` helper
3. **Status updates are atomic** - Use locking to prevent race conditions
4. **Frontend detects failures from both event types** - For backward compatibility during migration

---

## 📋 Quick Task Checklist

### Phase 1: Foundation (Week 1) - 10 tasks
- [ ] 1.1: Create error event standard document
- [ ] 1.2: Create `emit_error_event()` helper function
- [ ] 1.3: Fix quality gate error event
- [ ] 1.4: Create `check_should_abort()` helper
- [ ] 1.5: Add abort check to supervisor
- [ ] 1.6: Add abort check to quality gate
- [ ] 1.7: Add abort check to aggregate findings
- [ ] 1.8: Add abort checks to all 8 agent nodes
- [ ] 1.9: Add abort check to artifact generation
- [ ] 1.10: Integration test for abort signal

### Phase 2: Migration (Week 2) - 8 tasks
- [ ] 2.1: Migrate extract_content to error helper
- [ ] 2.2: Migrate generate_embedding to error helper
- [ ] 2.3: Migrate supervisor to error helper
- [ ] 2.4: Migrate aggregate_findings to error helper
- [ ] 2.5: Migrate artifact generation to error helper
- [ ] 2.6: Create status update locking mechanism
- [ ] 2.7: Unify GeneratorExit handling
- [ ] 2.8: Verify error event persistence

### Phase 3: Frontend & Testing (Week 3) - 7 tasks
- [ ] 3.1: Update frontend error detection
- [ ] 3.2: Fix progress calculation
- [ ] 3.3: Add error code display to UI
- [ ] 3.4: Add SSE reconnection logic
- [ ] 3.5: Add comprehensive E2E tests
- [ ] 3.6: Add backend integration tests
- [ ] 3.7: Update documentation

---

## 🔧 Code Patterns

### Emitting Error Events (Backend)

**✅ CORRECT:**
```python
from app.shared.services.messaging.sse_helpers import emit_error_event

try:
    # ... do work ...
except Exception as e:
    await emit_error_event(
        analysis_id=analysis_id,
        stage="extraction",
        error=str(e),
        error_code="EXTRACTION_FAILED",
    )
    raise
```

**❌ WRONG:**
```python
await emit_streaming_event(
    "progress",  # WRONG - should be "error"
    stage="extraction",
    status="failed",
    error=str(e),
)
```

### Checking Abort Signal (Backend)

**✅ CORRECT:**
```python
from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

async def my_node(state: AnalysisState) -> dict:
    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}  # Skip execution
    
    # ... continue with work ...
```

**❌ WRONG:**
```python
async def my_node(state: AnalysisState) -> dict:
    # Missing abort check - node will execute even if workflow should abort
    # ... do work ...
```

### Detecting Failed Stages (Frontend)

**✅ CORRECT:**
```typescript
import { isFailedStage } from '@app-types/sse'

const failedCount = events.filter(isFailedStage).length
```

**❌ WRONG:**
```typescript
// Only checks error events, misses failed progress events
const failedCount = events.filter(isErrorEvent).length
```

---

## 🐛 Common Mistakes to Avoid

1. **Don't use `type="progress"` with `status="failed"`** - Always use `type="error"`
2. **Don't skip abort checks** - All nodes must check `should_abort`
3. **Don't update status without locking** - Use status updater with locking
4. **Don't log GeneratorExit as error during cleanup** - Use unified detection function
5. **Don't count failed stages in progress** - Exclude from completion percentage

---

## 📊 Progress Tracking

**Total Tasks**: 25  
**Completed**: 0  
**In Progress**: 0  
**Blocked**: 0  

**Phase 1**: 0/10 (0%)  
**Phase 2**: 0/8 (0%)  
**Phase 3**: 0/7 (0%)

---

## 🔗 Related Files

- **Full Plan**: `docs/ERROR_HANDLING_STANDARDIZATION_PLAN.md`
- **Bug Report**: `docs/ANALYSIS_BUG_REPORT.md`
- **SSE Schema**: `docs/SSE_SCHEMA.md` (to be updated)

---

## 🚨 Critical Path

**Must complete in order:**
1. Task 1.1: Error standard (foundation)
2. Task 1.2: Error helper (foundation)
3. Task 1.4: Abort helper (foundation)
4. Then: All other tasks can proceed in parallel

---

**Quick Start**: Begin with Task 1.1 to establish the standard, then proceed systematically through Phase 1.



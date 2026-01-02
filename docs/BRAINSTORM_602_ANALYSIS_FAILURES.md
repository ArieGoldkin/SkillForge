# Brainstorm: Issue #602 - Analysis Pipeline Failures

**Date**: 2026-01-02
**Branch**: `issue/602-hyde-embeddings`
**Priority**: CRITICAL - Core feature completely broken

---

## Executive Summary

During validation of the HyDE implementation (Issue #602), we discovered that the **entire analysis pipeline is broken**. All 9 agents produce empty/placeholder findings, resulting in 100% analysis failure rate.

**HyDE implementation is complete and working**, but it's irrelevant if no analyses succeed.

---

## Root Cause Analysis

### Root Cause #1: Content Cleaner Truncating 82%+ of Content (UPSTREAM)

**Location**: `/backend/app/shared/services/extraction/content_cleaner.py` (line 58)

**The Bug**:
```python
END_CONTENT_INDICATORS = [
    r"^#{1,3}\s*(?:related|more|recommended|popular|trending)",
    r"^#{1,3}\s*(?:comments?|discussion|replies)",
    r"^#{1,3}\s*(?:about the author|author bio|written by)",
    r"^#{1,3}\s*(?:share this|spread the word)",
    r"^#{1,3}\s*(?:newsletter|subscribe|sign up)",
    r"^#{1,3}\s*(?:footer|sidebar|widget)",  # ← THIS PATTERN IS THE PROBLEM
]
```

**What Happens**:
1. Jina API extracts full article content (65,405 bytes, 8,048 words)
2. Content cleaner scans for "end of content" indicators
3. Pattern `sidebar` matches legitimate `### Sidebars` ToC header in Martin Fowler article
4. Cleaner truncates at line 109 of 627 lines (82.6% of content DISCARDED)
5. Only 7,304 bytes (423 words) stored in database
6. Agents receive drastically incomplete content

**Evidence**:
```
content_cleaned: original_length=65272 cleaned_length=7304 reduction_percent=88.8
```

**Fix Required**:
```python
# Option A: More specific pattern (word boundaries)
r"^#{1,3}\s+(?:footer|page\s+sidebar|widgets?)\s*$",

# Option B: Add quality gate for excessive truncation
if reduction_percent > 70:
    logger.warning("excessive_content_reduction", ...)
    # Flag for review or skip truncation
```

---

### Root Cause #2: Empty Content Passed to Agents (DOWNSTREAM)

**Location**: `/backend/app/domains/analysis/workflows/tasks/runners.py` (lines 183-208)

**The Bug**:
```python
async def _load_content_from_artifact(session, state, agent_type, fallback_content):
    try:
        store = ArtifactStore(session)
        loaded = await store.load(uri=uri, section=section, max_chars=max_chars)

        # BUG: Returns empty string without validation
        logger.info("artifact_content_loaded", content_length=len(loaded))
        return loaded  # ← Returns "" when content is empty/NULL

    except Exception as e:
        # Fallback ONLY on exception, not on empty success
        return fallback_content  # ← Never reached if load() "succeeds" with empty
```

**What Happens**:
1. Extraction phase stores content in `analysis.raw_content` via Session A
2. Agent execution phase loads via `ArtifactStore` using Session B
3. Session B returns empty string (isolation/race condition/NULL)
4. Empty string is returned as "successful" load
5. Agents receive `""` instead of article content
6. Agents produce placeholder/empty findings

**Fix Required**:
```python
loaded = await store.load(...)
if not loaded or len(loaded.strip()) == 0:
    logger.warning("artifact_load_empty", ...)
    return fallback_content  # Use state["raw_content"] instead
return loaded
```

---

## All Issues Identified

### Tier 1: CRITICAL (Blocks All Usage)

| ID | Issue | File | Impact |
|----|-------|------|--------|
| **C1** | Content cleaner truncating 82%+ of content | `content_cleaner.py:58` | 88.8% content loss |
| **C2** | Empty content passed to agents | `runners.py:183-208` | 100% agent failure |
| **C3** | Session isolation in artifact loading | `artifact_store.py` | Content not reaching agents |
| **C4** | Langfuse 401 Unauthorized | Credentials config | No observability |

### Tier 2: HIGH (Degrades Experience)

| ID | Issue | File | Impact |
|----|-------|------|--------|
| **H1** | TimeoutError not wrapped for SSE | `exception_handler.py` | User sees stale state |
| **H2** | Error details not persisted to DB | Workflow completion | `error_message` NULL |
| **H3** | Quality gate retry loop ineffective | `validation.py` | 3 retries all fail |

### Tier 3: MEDIUM (Bugs to Fix)

| ID | Issue | File | Impact |
|----|-------|------|--------|
| **M1** | OpenTelemetry span warnings | Middleware | Missing trace context |
| **M2** | Framer Motion color warnings | CSS/Theme | Console spam |
| **M3** | Content extraction word count mismatch | Extraction service | Logging confusion |

---

## Proposed Fix Strategy

### Phase 1: Emergency Fix (UPSTREAM - Content Extraction)

**Goal**: Ensure full article content is preserved

1. **Fix content cleaner overly aggressive pattern** (C1)
   - Remove or refine the `sidebar` pattern in `END_CONTENT_INDICATORS`
   - Option A: Change to `r"^#{1,3}\s+(?:footer|page\s+sidebar|widgets?)\s*$"` (word boundaries)
   - Option B: Remove `sidebar` from the pattern entirely
   - Add quality gate: warn if content reduction > 70%

2. **Add integration test with real-world articles**
   - Martin Fowler microservices article
   - CSS-Tricks articles
   - Verify full content extraction

### Phase 2: Emergency Fix (DOWNSTREAM - Agent Content Loading)

**Goal**: Ensure agents receive content even if artifact loading fails

3. **Fix `_load_content_from_artifact`** (C2)
   - Add empty content check before returning
   - Fall back to `fallback_content` (state["raw_content"]) when empty
   - Log warning for debugging

4. **Verify content flow** (C3)
   - Add logging at each handoff point
   - Confirm content exists in state["raw_content"]
   - Trace why ArtifactStore returns empty

### Phase 3: Robustness

**Goal**: Prevent silent failures

5. **Wrap TimeoutError for SSE** (H1)
   - Catch TimeoutError in workflow exception handler
   - Emit proper SSE error event to frontend
   - Include timeout context in error message

6. **Persist error details** (H2)
   - Update analysis record with:
     - `error_code`: Specific failure reason
     - `error_message`: Human-readable description
     - `failed_at_stage`: Which stage failed
   - Fix database update in workflow completion

### Phase 4: Observability

**Goal**: Enable debugging

7. **Fix Langfuse credentials** (C4)
   - Check `.env` for correct `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
   - Verify `LANGFUSE_HOST` matches running Langfuse instance
   - Test telemetry export

8. **Fix OpenTelemetry spans** (M1)
   - Ensure spans created with `start_as_current_span()`
   - Check middleware initialization order

---

## Verification Plan

After fixes, verify:

1. **Unit Tests**
   ```bash
   cd backend && poetry run pytest tests/unit/ -v --tb=short
   ```
   Expected: 4421 passed (current baseline)

2. **Integration Test**
   - Submit Martin Fowler article URL
   - Verify extraction produces content
   - Verify agents receive content
   - Verify agents produce findings
   - Verify quality gate passes
   - Verify artifact generated with real content

3. **E2E Test**
   - Open http://localhost:5173
   - Submit URL
   - Watch progress update in real-time
   - Verify completion with valid artifact
   - Download and inspect markdown

---

## Questions to Answer

1. **Why is ArtifactStore returning empty?**
   - Is `analysis.raw_content` NULL in database?
   - Is there a session commit timing issue?
   - Is the query filtering incorrectly?

2. **Why do agents not fail loudly on empty content?**
   - Should agents validate input content length?
   - Should there be a minimum content threshold?

3. **Why does Handle Pattern have this flaw?**
   - Was this a regression?
   - Did it ever work correctly?
   - Check git blame for `_load_content_from_artifact`

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `backend/app/shared/services/extraction/content_cleaner.py` | Fix overly aggressive sidebar pattern | P0 |
| `backend/app/domains/analysis/workflows/tasks/runners.py` | Add empty content fallback | P0 |
| `backend/app/domains/analysis/services/context/artifact_store.py` | Add debug logging | P1 |
| `backend/app/domains/analysis/services/workflow/exception_handler.py` | Wrap TimeoutError | P1 |
| `backend/.env` | Fix Langfuse credentials | P2 |

---

## Success Criteria

- [ ] Analysis completes successfully (not marked FAILED)
- [ ] All 9 agents produce non-empty findings
- [ ] Quality gate score > 0.7
- [ ] Artifact contains actual analysis, not placeholders
- [ ] Frontend shows 100% progress and completion
- [ ] Langfuse receives traces (no 401 errors)

---

## Related Issues

- **#602**: HyDE implementation (this branch) - HyDE is done, but blocked by analysis failures
- **#244**: Handle Pattern implementation - introduced the artifact loading bug
- **#489**: SSE error reconciliation - related to error handling

---

## Timeline

| Phase | Task | Estimate |
|-------|------|----------|
| Phase 1 | Emergency fix for content loading | 1-2 hours |
| Phase 2 | Robustness improvements | 2-4 hours |
| Phase 3 | Observability fixes | 1-2 hours |
| Verification | Full E2E testing | 1 hour |
| **Total** | | **5-9 hours** |

---

## Next Steps

1. [ ] Confirm root cause with database query
2. [ ] Implement Phase 1 fix
3. [ ] Run integration test
4. [ ] If passing, commit and push
5. [ ] Document on issue #602
6. [ ] Create sub-issues for Phase 2/3 work

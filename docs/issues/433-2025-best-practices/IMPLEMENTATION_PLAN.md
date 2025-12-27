# Issue #433: 2025 Best Practices Implementation Plan

**Created:** December 27, 2025
**Branch:** `issue/433-2025-best-practices`
**Status:** Planning Complete - Ready for Implementation

---

## Executive Summary

This document provides a comprehensive implementation plan for completing phases 3-7 of Issue #433 (2025 Best Practices). The research phase identified:

- **7 async generators** to cleanup (2 need fixes)
- **10 frontend components** to refactor with compound patterns
- **7 branded types** to implement
- **60+ tests** to convert to VCR recording
- **15+ tracing spans** to add

**Total Estimated Effort:** 45-55 hours across 5 phases

---

## Phase Summary

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ISSUE #433 - REMAINING PHASES (3-7)                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   PHASE 3: Async Generator Cleanup          PHASE 4: Compound Components    ║
║   ═══════════════════════════════          ══════════════════════════════   ║
║   Effort: 2-3 hours | Impact: HIGH          Effort: 6-8 hours | Impact: MED ║
║   Risk: LOW                                 Risk: MEDIUM                    ║
║   Files: 2 files needing fixes              Components: 10 to refactor      ║
║                                                                              ║
║   PHASE 5: Branded Types                    PHASE 6: VCR Testing            ║
║   ═════════════════════                     ═════════════════               ║
║   Effort: 3-4 hours | Impact: MED           Effort: 4-6 hours | Impact: MED ║
║   Risk: LOW                                 Risk: LOW                       ║
║   Types: 7 branded types                    Tests: 60+ to convert           ║
║                                                                              ║
║   PHASE 7: Tracing Enhancements                                             ║
║   ═════════════════════════════                                             ║
║   Effort: 3-4 hours | Impact: LOW                                           ║
║   Risk: LOW                                                                 ║
║   Spans: 15+ new trace spans                                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Phase 3: Async Generator Cleanup

### Summary
Replace direct async generator iteration with `aclosing()` context managers to prevent resource leaks.

### Files Requiring Changes

| File | Location | Issue | Priority |
|------|----------|-------|----------|
| `quality_gate_node.py` | Line 509-520 | Manual session cleanup | HIGH |
| `dependencies.py` | Line 20-43 | Nested generators | MEDIUM |

### Already Correct (No Changes Needed)
- `sse_handler.py:144` - Uses `async with aclosing(broadcaster.subscribe(channel))`
- `streaming.py:76` (tutor) - Uses `async with aclosing(broadcaster.subscribe(channel))`
- `streaming.py:117-123` (agents) - Uses `aclosing()` for agent.astream()
- `analysis_repository.py:355` - Uses SQLAlchemy `async with session.stream_scalars()`
- `broadcaster.py:116-181` - Proper finally block cleanup
- `redis_broadcaster.py:195-301` - Proper finally block cleanup

### Implementation Details

#### Fix 1: quality_gate_node.py
```python
# BEFORE (Line 509-520):
async for db_session in get_db():
    try:
        analysis_repo = AnalysisRepository(session=db_session)
        await analysis_repo.record_error(...)
    finally:
        await db_session.close()
    break

# AFTER:
from contextlib import aclosing

async with aclosing(get_db()) as session_gen:
    async for db_session in session_gen:
        analysis_repo = AnalysisRepository(session=db_session)
        await analysis_repo.record_error(...)
        break  # Only need one iteration
```

#### Fix 2: dependencies.py
```python
# BEFORE (Line 20-43):
async def get_database_session() -> AsyncGenerator[AsyncSession]:
    async for session in _get_db():
        yield session

# AFTER:
async def get_database_session() -> AsyncGenerator[AsyncSession]:
    """Database session dependency with proper async cleanup."""
    async with _get_db() as session:
        yield session
```

### Testing Requirements
- Run existing tests: `pytest backend/tests/unit/domains/analysis/workflows/nodes/`
- Verify SSE streaming still works with real database
- Check for resource leaks in long-running analysis

### Effort: 2-3 hours

---

## Phase 4: Compound Components

### Summary
Refactor frontend components with boolean prop combinations to use 2025 compound component patterns.

### Priority 1 Components (High Impact)

| Component | Location | Current Pattern | New Pattern |
|-----------|----------|-----------------|-------------|
| AnalysisProgressCard | `steps/AnalysisProgressCard.tsx` | 5+ boolean conditions | CVA variants |
| ProgressColumn | `progress/ProgressColumn.tsx` | 15+ props drilling | Context + composition |
| ArtifactPreviewModal | `artifact/` | Boolean state combinations | State machine |

### Priority 2 Components (Medium Impact)

| Component | Location | Current Pattern | New Pattern |
|-----------|----------|-----------------|-------------|
| AnalysisRenderRouter | `render-router/` | 7 route conditions | Extract route components |
| ConnectionStatus | `progress/` | Switch statement | Enum-driven rendering |
| LoadingStateDisplay | `progress/` | Switch statement | Enum-driven rendering |
| StageItem | `progress/StageItem.tsx` | Conditional sections | State-based slots |
| CommonAnalysisLayout | `render-router/` | Boolean slots | Compound layout |

### Priority 3 Components (Lower Impact)

| Component | Location | New Pattern |
|-----------|----------|-------------|
| TimeoutWarningBanner | `analysis/components/` | CVA variants |
| MobileBottomSheet | `accordion/` | Expose inner state |

### Implementation Pattern Examples

#### Pattern 1: CVA Variants (AnalysisProgressCard)
```tsx
// shared/components/ui/analysis-card.tsx
import { cva, type VariantProps } from 'class-variance-authority'

const analysisCardVariants = cva(
  "rounded-lg border p-4",
  {
    variants: {
      status: {
        analyzing: "border-blue-500 bg-blue-50",
        complete: "border-green-500 bg-green-50",
        "complete-with-errors": "border-red-500 bg-red-50",
      }
    }
  }
)

type AnalysisCardStatus = "analyzing" | "complete" | "complete-with-errors"

interface AnalysisProgressCardProps {
  status: AnalysisCardStatus  // Single prop instead of hasFailedStages + isComplete
  // ...
}
```

#### Pattern 2: Context + Composition (ProgressColumn)
```tsx
// Create context for stage status
const ProgressColumnContext = createContext<ProgressColumnState>(null)

export function ProgressColumnProvider({ stageStatuses, children }) {
  const { activeGroups, pendingGroups } = useMemo(() => {
    // Filtering logic here
  }, [stageStatuses])

  return (
    <ProgressColumnContext.Provider value={{ activeGroups, pendingGroups }}>
      {children}
    </ProgressColumnContext.Provider>
  )
}

// Usage:
<ProgressColumnProvider stageStatuses={...}>
  <ProgressColumn.Hero />
  <ProgressColumn.Groups />
  <ProgressColumn.SkippedList />
</ProgressColumnProvider>
```

#### Pattern 3: Enum-Driven Rendering (ConnectionStatus)
```tsx
const LOADING_STATE_CONFIG = {
  connecting: { icon: Loader2, text: 'Connecting...', className: 'text-blue-500' },
  connected: { icon: Wifi, text: 'Connected', className: 'text-green-500' },
  error: { icon: AlertCircle, text: 'Error', className: 'text-red-500' },
  // ... other states
} as const satisfies Record<LoadingStateType, LoadingStateUI>

function ConnectionStatus({ state }: { state: LoadingStateType }) {
  const config = LOADING_STATE_CONFIG[state]
  return (
    <Badge className={config.className}>
      <config.icon className="w-4 h-4" />
      {config.text}
    </Badge>
  )
}
```

### Testing Requirements
- Update component tests for new APIs
- Ensure Playwright E2E tests still pass
- Visual regression testing for UI changes

### Effort: 6-8 hours

---

## Phase 5: Branded Types

### Summary
Implement branded/opaque types to prevent accidental ID mixing at compile time.

### Types to Implement

| Type | Domain | Priority | Current | Files Affected |
|------|--------|----------|---------|----------------|
| AnalysisID | Core | P0 (Upgrade) | `str` alias | 100+ |
| ArtifactID | Core | P0 | `UUID` | 50+ |
| SessionID | Tutoring | P0 | `UUID` | 25+ |
| ChunkID | Search | P1 | `UUID` | 15+ |
| TraceID | Observability | P2 | `str` | 20+ |
| TopicID | Tutoring | P2 | `str` | 10+ |
| MessageID | Tutoring | P2 | `UUID` | 8+ |

### Backend Implementation (Python)

```python
# backend/app/core/branded_ids.py (NEW FILE)
"""Branded/opaque types for domain IDs using NewType pattern."""

from typing import NewType
from uuid import UUID

# Core domain IDs
AnalysisID = NewType('AnalysisID', UUID)
ArtifactID = NewType('ArtifactID', UUID)
SessionID = NewType('SessionID', UUID)
ChunkID = NewType('ChunkID', UUID)

# String-based IDs
TraceID = NewType('TraceID', str)
TopicID = NewType('TopicID', str)
MessageID = NewType('MessageID', UUID)

# Factory functions for runtime validation
def create_analysis_id(value: UUID | str) -> AnalysisID:
    """Create typed AnalysisID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return AnalysisID(value)

def create_artifact_id(value: UUID | str) -> ArtifactID:
    """Create typed ArtifactID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return ArtifactID(value)

# ... similar for other types
```

### Frontend Implementation (TypeScript)

```typescript
// frontend/src/types/branded-ids.ts (NEW FILE)
/**
 * Branded/opaque types for domain IDs.
 * Provides compile-time type safety without runtime overhead.
 */

// Core domain IDs
export type AnalysisID = string & { readonly __brand: 'AnalysisID' }
export type ArtifactID = string & { readonly __brand: 'ArtifactID' }
export type SessionID = string & { readonly __brand: 'SessionID' }
export type ChunkID = string & { readonly __brand: 'ChunkID' }

// Other IDs
export type TraceID = string & { readonly __brand: 'TraceID' }
export type TopicID = string & { readonly __brand: 'TopicID' }
export type MessageID = string & { readonly __brand: 'MessageID' }

// Factory functions
export const AnalysisID = (id: string): AnalysisID => {
  if (!isValidUUID(id)) throw new Error(`Invalid AnalysisID: ${id}`)
  return id as AnalysisID
}

export const ArtifactID = (id: string): ArtifactID => {
  if (!isValidUUID(id)) throw new Error(`Invalid ArtifactID: ${id}`)
  return id as ArtifactID
}

// ... similar for other types

function isValidUUID(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
}
```

### Migration Strategy

1. **Add branded type definitions** (both Python and TypeScript)
2. **Update API schemas** to use branded types
3. **Update state types** (AnalysisState, TutorState)
4. **Update repositories** function signatures
5. **Update route parameters** (FastAPI Path, TanStack Router)
6. **Run type checker** to find remaining plain string usages

### Testing Requirements
- Type checker passes with new branded types
- Existing tests continue to pass
- Add unit tests for factory functions

### Effort: 3-4 hours

---

## Phase 6: VCR Testing Integration

### Summary
Add VCR.py for HTTP recording/playback testing to improve test reliability and reduce flakiness.

### Services to Record

| Service | Test Count | Priority | Cassette Files |
|---------|------------|----------|----------------|
| Tavily Search | 35 | HIGH | 35 cassettes |
| Jina Reader | 10 | HIGH | 10 cassettes |
| GitHub Search | 15 | MEDIUM | 15 cassettes |
| OpenAI Batch | 20 | MEDIUM | 20 cassettes |

### Implementation Steps

#### Step 1: Add Dependencies
```toml
# pyproject.toml
[tool.poetry.dependencies]
pytest-vcr = "^1.0.2"
vcrpy = "^6.0.1"
```

#### Step 2: Create Cassette Directory
```
backend/tests/cassettes/
├── unit/
│   ├── tavily_search/
│   ├── jina_reader/
│   └── github_search/
└── integration/
    └── full_workflow/
```

#### Step 3: Add VCR Configuration
```python
# backend/tests/conftest.py
import vcr

@pytest.fixture(scope="session")
def vcr_config():
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "once",
        "match_on": ["method", "uri", "body"],
        "filter_headers": [
            ("authorization", "REDACTED"),
            ("x-api-key", "REDACTED"),
        ],
        "before_record_request": redact_api_keys,
    }
```

#### Step 4: Convert Test Example
```python
# BEFORE:
@pytest.mark.asyncio
async def test_search_success(tavily_search):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {...}
    tavily_search.client.post = AsyncMock(return_value=mock_response)
    result = await tavily_search.search("test query")

# AFTER:
@pytest.mark.asyncio
@pytest.mark.vcr("tavily_search/test_search_success.yaml")
async def test_search_success(tavily_search):
    # No mocking - VCR replays recorded response
    result = await tavily_search.search("test query")
    assert result["answer"] == "Test answer"
```

### Recording Process
1. Run tests with `VCR_RECORD_MODE=all` and real API keys
2. Commit cassettes (API responses) to git
3. CI uses cassettes - no real API calls needed

### Effort: 4-6 hours

---

## Phase 7: Tracing Enhancements

### Summary
Add granular trace spans for better observability in Langfuse.

### Gaps Identified

| Gap | Current State | Enhancement |
|-----|---------------|-------------|
| Function-level spans | Node-level only | Add 15+ function spans |
| Cost tracking | Manual calculation | Per-agent cost scores |
| User tracking | All "anonymous" | Real user ID extraction |
| Database spans | Not tracked | SQLAlchemy event listeners |
| SSE spans | Not tracked | Event delivery timing |

### Priority 1 Enhancements (Immediate)

#### Add Function Spans
```python
# Add @traced_tool to these functions:
# - extract_structured_response()
# - validate_findings_count()
# - process_agent_result()
# - run_self_correction_loop()

from app.core.tracing import traced_tool

@traced_tool("extract_structured_response", tags=["parsing", "validation"])
async def extract_structured_response(...):
    # Existing code - now traced automatically
    pass
```

#### Add Cost Tracking
```python
# In invoke_agent() after usage extraction:
cost_per_million = PRICING[model]
input_cost = (usage.input_tokens / 1_000_000) * cost_per_million["input"]
output_cost = (usage.output_tokens / 1_000_000) * cost_per_million["output"]

langfuse_service.submit_score(
    name="cost_usd",
    value=input_cost + output_cost,
    comment=f"{model}: {usage.input_tokens}in + {usage.output_tokens}out",
)
```

#### Extract User IDs
```python
# Instead of hardcoded "anonymous":
update_current_trace(
    user_id=get_user_id_from_context(),  # Extract from request
    metadata={"user_tier": get_user_tier(), "source": "api|ui|mcp"},
)
```

### Priority 2 Enhancements (Next Sprint)

#### Database Query Spans
```python
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, ...):
    start_span("db_query", metadata={"query": statement[:200]})

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, ...):
    end_span(metadata={"rows_affected": cursor.rowcount})
```

#### SSE Event Spans
```python
@traced_tool("broadcast_sse_event", tags=["messaging"])
async def publish_progress_event(event_type: str, data: dict, channel: str):
    update_current_observation(metadata={"event_size_bytes": len(json.dumps(data))})
    await broadcaster.publish(channel, json.dumps(data))
```

### Testing Requirements
- Verify Langfuse receives new spans
- Check latency impact (<5% overhead)
- Validate cost calculations accuracy

### Effort: 3-4 hours

---

## Implementation Order

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         RECOMMENDED IMPLEMENTATION ORDER                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   WEEK 1 (8-10 hours)                                                        ║
║   ═══════════════════                                                        ║
║   ✓ Phase 3: Async Generator Cleanup (2-3h)                                  ║
║     - Fix quality_gate_node.py and dependencies.py                           ║
║     - Run tests to verify no regressions                                     ║
║                                                                              ║
║   ✓ Phase 5: Branded Types (3-4h)                                            ║
║     - Create branded_ids.py (Python)                                         ║
║     - Create branded-ids.ts (TypeScript)                                     ║
║     - Update API schemas                                                     ║
║                                                                              ║
║   WEEK 2 (10-14 hours)                                                       ║
║   ════════════════════                                                       ║
║   ✓ Phase 4: Compound Components (6-8h)                                      ║
║     - Priority 1: AnalysisProgressCard, ProgressColumn                       ║
║     - Priority 2: ConnectionStatus, LoadingStateDisplay                      ║
║                                                                              ║
║   ✓ Phase 6: VCR Testing (4-6h)                                              ║
║     - Install pytest-vcr, configure cassettes                                ║
║     - Convert Tavily Search tests (highest ROI)                              ║
║                                                                              ║
║   WEEK 3 (3-4 hours)                                                         ║
║   ════════════════════                                                       ║
║   ✓ Phase 7: Tracing Enhancements (3-4h)                                     ║
║     - Add function spans                                                     ║
║     - Implement cost tracking                                                ║
║     - User ID extraction                                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Success Metrics

### Phase 3: Async Generators
- [ ] Zero async generators using direct iteration
- [ ] All generators use `aclosing()` or built-in context managers
- [ ] No resource leaks in long-running analyses

### Phase 4: Compound Components
- [ ] Components with 3+ boolean props reduced from 8 to 2
- [ ] Average lines per component reduced by 30-40%
- [ ] Props drilling depth reduced from 5 to 2 levels

### Phase 5: Branded Types
- [ ] 7 branded types implemented
- [ ] Type checker catches ID mixing errors
- [ ] No runtime behavior changes

### Phase 6: VCR Testing
- [ ] 60+ tests converted to VCR
- [ ] CI runs without API keys
- [ ] Test execution time reduced by 50%+

### Phase 7: Tracing
- [ ] 15+ new trace spans added
- [ ] Cost tracking visible in Langfuse
- [ ] User segmentation working

---

## Files to Create/Modify

### New Files
- `backend/app/core/branded_ids.py`
- `frontend/src/types/branded-ids.ts`
- `backend/tests/cassettes/` (directory structure)
- `frontend/src/shared/components/ui/analysis-card.tsx` (CVA variants)
- `frontend/src/features/analysis/contexts/ProgressColumnContext.tsx`

### Modified Files
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`
- `backend/app/api/dependencies.py`
- `frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx`
- `frontend/src/features/analysis/components/progress/ProgressColumn.tsx`
- `frontend/src/features/analysis/components/progress/ConnectionStatus.tsx`
- `backend/tests/conftest.py` (VCR config)
- `backend/app/domains/analysis/workflows/agents/invocation.py` (tracing)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Component refactor breaks UI | Run Playwright E2E tests before/after |
| Branded types cause cascading changes | Implement incrementally (P0 first) |
| VCR cassettes become stale | Add cassette refresh CI job |
| Tracing adds latency | Measure overhead, use sampling |
| Async cleanup breaks streaming | Test SSE with long analyses |

---

**Last Updated:** December 27, 2025
**Author:** Claude Code Research Analysis

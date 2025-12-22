# SSE Error Event Standard

**Version**: 1.0  
**Date**: December 2025  
**Status**: Active Standard

---

## Overview

This document defines the standard for error event emission across all workflow nodes in the SkillForge analysis system. All failures must emit consistent, structured error events that can be reliably detected by the frontend.

---

## Core Principle

**All failures MUST emit `type="error"` events. Never use `type="progress"` with `status="failed"`.**

---

## Event Type Decision Tree

### When to Use `type="error"`

Use `type="error"` when:
- A workflow stage fails and cannot continue
- An exception is caught and handled
- A validation check fails (e.g., quality gate)
- An agent fails to produce findings
- Any operation that prevents normal workflow progression

**Examples**:
- Extraction fails (invalid URL, timeout, network error)
- Embedding generation fails (API error, rate limit)
- Quality gate fails (scores below threshold)
- Agent execution fails (exception, timeout)
- Artifact generation fails (template error, validation failure)

### When to Use `type="progress"`

Use `type="progress"` when:
- A stage is running normally
- A stage completes successfully
- Progress updates during execution
- Non-fatal warnings or information

**Examples**:
- Stage started: `status="running"`
- Stage completed: `status="complete"`
- Progress update: `status="running"` with `progress_percent=50`
- Warning (non-fatal): `status="running"` with `quality_warning="Low confidence"`

### When to Use `type="complete"`

Use `type="complete"` when:
- The entire workflow completes successfully
- All stages finished and artifact is generated

**Examples**:
- Workflow complete: `type="complete"`, `stage="artifact_generation"`, `status="complete"`

---

## Error Event Structure

### Required Fields

```python
{
    "type": "error",  # MUST be "error"
    "analysis_id": "uuid-string",
    "stage": "stage_name",  # e.g., "extraction", "quality_validation"
    "status": "failed",  # MUST be "failed"
    "timestamp": "ISO-8601-timestamp",
    "error": "Human-readable error message",  # Required
}
```

### Optional Fields

```python
{
    "error_code": "ERROR_CODE",  # e.g., "EXTRACTION_FAILED", "QUALITY_GATE_FAILED"
    "details": {
        "error": "Detailed error message",
        "error_code": "ERROR_CODE",
        # Additional context-specific fields
    },
    # Stage-specific metadata
    "agent_type": "agent_name",  # For agent failures
    "quality_scores": {...},  # For quality gate failures
    "retry_count": 0,  # If retry attempted
}
```

---

## Implementation Pattern

### Standard Error Event Emission

**ALWAYS use the `emit_error_event()` helper function:**

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
        # Additional context
        url=url,
        retry_count=retry_count,
    )
    raise  # Re-raise to propagate
```

### Error Code Standards

Error codes follow the pattern: `{STAGE}_{FAILURE_TYPE}`

**Common Error Codes**:
- `EXTRACTION_FAILED` - Content extraction failed
- `EXTRACTION_TIMEOUT` - Extraction timed out
- `EXTRACTION_ERROR_PAGE` - Extracted content is an error page
- `EMBEDDING_FAILED` - Embedding generation failed
- `EMBEDDING_RATE_LIMIT` - Embedding API rate limited
- `SUPERVISOR_FAILED` - Supervisor routing failed
- `AGENT_FAILED` - Agent execution failed (use with `agent_type`)
- `QUALITY_GATE_FAILED` - Quality gate validation failed
- `ARTIFACT_GENERATION_FAILED` - Artifact generation failed
- `SYNTHESIS_FAILED` - Findings synthesis failed

---

## Migration Guide

### Before (Incorrect)

```python
# ❌ WRONG: Using progress event with failed status
await emit_streaming_event(
    "progress",  # Wrong type
    analysis_id=analysis_id,
    stage="quality_validation",
    status="failed",  # Wrong - should be error event
    error="Quality gate failed",
)
```

### After (Correct)

```python
# ✅ CORRECT: Using error event helper
await emit_error_event(
    analysis_id=analysis_id,
    stage="quality_validation",
    error="Quality gate failed - scores below threshold",
    error_code="QUALITY_GATE_FAILED",
    avg_score=avg_score,
    threshold=QUALITY_THRESHOLD,
    scores=quality_scores,
)
```

---

## Stage-Specific Examples

### Extraction Failure

```python
try:
    result = await extract_content(url, analysis_id)
except JinaReaderError as e:
    await emit_error_event(
        analysis_id=analysis_id,
        stage="extraction",
        error=str(e),
        error_code=e.error_code.value if e.error_code else "EXTRACTION_FAILED",
        url=url,
    )
    raise
```

### Quality Gate Failure

```python
if not gate_passed:
    await emit_error_event(
        analysis_id=analysis_id,
        stage="quality_validation",
        error="Quality gate failed - scores below threshold",
        error_code="QUALITY_GATE_FAILED",
        avg_score=avg_score,
        threshold=QUALITY_THRESHOLD,
        scores=quality_scores,
        gate_passed=False,
    )
```

### Agent Failure

```python
try:
    findings = await agent.analyze(content)
except Exception as e:
    await emit_error_event(
        analysis_id=analysis_id,
        stage=get_stage_name(agent_type),
        error=f"Agent {agent_type} failed: {str(e)}",
        error_code="AGENT_FAILED",
        agent_type=agent_type,
    )
    raise
```

### Supervisor Failure

```python
try:
    decision = await supervisor.select_agents(content)
except Exception as e:
    await emit_error_event(
        analysis_id=analysis_id,
        stage="supervisor_routing",
        error=f"Supervisor failed: {str(e)}",
        error_code="SUPERVISOR_FAILED",
    )
    raise
```

---

## Frontend Detection

The frontend detects failures using:

1. **Primary**: `type === "error"` events (standardized)
2. **Backward Compatibility**: `type === "progress"` with `status === "failed"` (during migration)

**Frontend Helper**:
```typescript
export function isFailedStage(event: unknown): boolean {
  if (isErrorEvent(event)) {
    return true
  }
  // Backward compatibility during migration
  if (isProgressEvent(event) && event.status === 'failed') {
    return true
  }
  return false
}
```

---

## Checklist for Node Migration

When migrating a node to use error events:

- [ ] Identify all failure points in the node
- [ ] Replace `emit_streaming_event("error", ...)` with `emit_error_event(...)`
- [ ] Replace `emit_streaming_event("progress", ..., status="failed")` with `emit_error_event(...)`
- [ ] Add appropriate `error_code` to all error events
- [ ] Include relevant context in error event (e.g., `agent_type`, `quality_scores`)
- [ ] Update unit tests to verify error event emission
- [ ] Verify error events are persisted to database
- [ ] Test frontend receives and displays error events correctly

---

## Testing Requirements

### Unit Tests

Each node must have tests that verify:
- Error events are emitted with correct structure
- Error codes are included
- Error messages are human-readable
- Context data is included

**Example Test**:
```python
async def test_extraction_failure_emits_error_event():
    with pytest.raises(JinaReaderError):
        await extract_content("invalid-url", analysis_id)
    
    # Verify error event was emitted
    events = await get_progress_events(analysis_id)
    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert error_events[0].stage == "extraction"
    assert error_events[0].error_code == "EXTRACTION_FAILED"
```

### Integration Tests

Integration tests verify:
- Error events are persisted to database
- Error events are retrievable via `/progress` endpoint
- Frontend can detect and display error events

---

## Backward Compatibility

During migration, the frontend will detect failures from both:
1. New `type="error"` events (standardized)
2. Old `type="progress"` events with `status="failed"` (legacy)

After all nodes are migrated, we can remove backward compatibility support.

---

## Related Documents

- `docs/ANALYSIS_BUG_REPORT.md` - Original bug analysis
- `docs/ERROR_HANDLING_STANDARDIZATION_PLAN.md` - Implementation plan
- `backend/app/shared/services/messaging/sse_helpers.py` - Error event helper implementation
- `frontend/src/schemas/sse.ts` - Frontend event schema

---

**Last Updated**: December 2025  
**Maintained By**: Backend Team

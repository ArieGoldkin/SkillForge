# SSE Event Schema

**Version:** 1.0  
**Last Updated:** January 2025  
**Issue:** #40 - SSE Endpoint Implementation

---

## Overview

This document defines the Server-Sent Events (SSE) schema for real-time analysis progress updates. All events follow a consistent structure with type-specific fields.

---

## Event Types

### 1. Progress Event

Emitted during workflow execution to indicate stage progress.

**Event Type:** `progress`

**Schema:**
```typescript
interface SSEProgressEvent {
  type: "progress"
  analysis_id: string  // UUID
  stage: StageName
  status: "pending" | "running" | "complete" | "failed"
  timestamp: string  // ISO 8601
  details?: {
    word_count?: number
    agent?: string
    progress_percent?: number
    [key: string]: unknown  // Stage-specific data
  }
}
```

**Stage Names:**

*Agent Stages:*
- `extraction` - Content extraction from URL
- `supervisor_routing` - Supervisor agent routing decision
- `tech_comparison` - Technology comparison analysis
- `security_audit` - Security audit analysis
- `implementation_planning` - Implementation planning
- `performance_audit` - Performance analysis
- `code_quality_audit` - Code quality analysis
- `trends_analysis` - Technology trends analysis
- `dependencies_analysis` - Dependencies analysis
- `aggregation` - Aggregating findings
- `artifact_generation` - Generating final artifact

*Workflow-level Stages:*
- `workflow` - Workflow-level events (errors, completion)
- `pattern_comparison` - A/B testing pattern comparison results
- `metrics` - Performance and quality metrics

**Example:**
```json
{
  "type": "progress",
  "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "extraction",
  "status": "running",
  "timestamp": "2025-01-01T10:30:05.123Z",
  "details": {
    "word_count": 5234
  }
}
```

---

### 2. Complete Event

Emitted when analysis workflow completes successfully.

**Event Type:** `complete`

**Schema:**
```typescript
interface SSECompleteEvent {
  type: "complete"
  analysis_id: string  // UUID
  stage: "artifact_generation"
  status: "complete"
  timestamp: string  // ISO 8601
  trace_id?: string  // Optional Langfuse trace ID for feedback submission
  details: {
    artifact_id: string  // UUID of generated artifact
  }
}
```

**Example:**
```json
{
  "type": "complete",
  "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "artifact_generation",
  "status": "complete",
  "timestamp": "2025-01-01T10:35:00.456Z",
  "trace_id": "trace-abc-123-def-456",
  "details": {
    "artifact_id": "789e0123-e45f-67g8-h901-234567890abc"
  }
}
```

**Note:** After receiving a `complete` event, the SSE connection is automatically closed by the server.

---

### 3. Error Event

Emitted when an error occurs during workflow execution.

**Event Type:** `error`

**Schema:**
```typescript
interface SSEErrorEvent {
  type: "error"
  analysis_id: string  // UUID
  stage: string  // Stage where error occurred
  status: "failed"
  timestamp: string  // ISO 8601
  details: {
    error: string  // Human-readable error message
    error_code?: string  // Optional error code
    [key: string]: unknown  // Additional error context
  }
}
```

**Example:**
```json
{
  "type": "error",
  "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "extraction",
  "status": "failed",
  "timestamp": "2025-01-01T10:30:10.789Z",
  "details": {
    "error": "URL not found (404)",
    "error_code": "EXTRACTION_FAILED"
  }
}
```

---

## Union Type

```typescript
type SSEEvent = SSEProgressEvent | SSECompleteEvent | SSEErrorEvent
```

---

## SSE Format

Events are sent in W3C SSE format:

```
event: progress
data: {"type": "progress", "analysis_id": "...", ...}

event: complete
data: {"type": "complete", "analysis_id": "...", ...}
```

**Fields:**
- `event:` - Event type (maps to `type` field in JSON)
- `data:` - JSON-encoded event object

---

## Frontend Integration

### TypeScript Types

```typescript
// frontend/src/types/sse.ts

export type StageName =
  // Agent stages
  | "extraction"
  | "supervisor_routing"
  | "tech_comparison"
  | "security_audit"
  | "implementation_planning"
  | "performance_audit"
  | "code_quality_audit"
  | "trends_analysis"
  | "dependencies_analysis"
  | "aggregation"
  | "artifact_generation"
  // Workflow-level stages
  | "workflow"
  | "pattern_comparison"
  | "metrics"

export type StageStatus = "pending" | "running" | "complete" | "failed"

export interface SSEProgressEvent {
  type: "progress"
  analysis_id: string
  stage: StageName
  status: StageStatus
  timestamp: string
  details?: {
    word_count?: number
    agent?: string
    progress_percent?: number
    [key: string]: unknown
  }
}

export interface SSECompleteEvent {
  type: "complete"
  analysis_id: string
  stage: "artifact_generation"
  status: "complete"
  timestamp: string
  trace_id?: string  // Optional Langfuse trace ID for feedback submission
  details: {
    artifact_id: string
  }
}

export interface SSEErrorEvent {
  type: "error"
  analysis_id: string
  stage: string
  status: "failed"
  timestamp: string
  details: {
    error: string
    error_code?: string
    [key: string]: unknown
  }
}

export type SSEEvent = SSEProgressEvent | SSECompleteEvent | SSEErrorEvent
```

### Usage Example

```typescript
import { SSEEvent } from "@/types/sse"

const eventSource = new EventSource(
  `/api/v1/analyze/${analysisId}/stream`
)

eventSource.addEventListener("progress", (event: MessageEvent) => {
  const data: SSEEvent = JSON.parse(event.data)
  
  if (data.type === "progress") {
    console.log(`Stage: ${data.stage}, Status: ${data.status}`)
    updateUI(data.stage, data.status, data.details)
  }
})

eventSource.addEventListener("complete", (event: MessageEvent) => {
  const data: SSEEvent = JSON.parse(event.data)
  
  if (data.type === "complete") {
    console.log("Analysis complete!", data.details.artifact_id)
    eventSource.close()
    navigateToArtifact(data.details.artifact_id)
  }
})

eventSource.addEventListener("error", (event: MessageEvent) => {
  const data: SSEEvent = JSON.parse(event.data)
  
  if (data.type === "error") {
    console.error("Analysis failed:", data.details.error)
    eventSource.close()
    showError(data.details.error)
  }
})

// Handle connection errors
eventSource.onerror = (error) => {
  console.error("SSE connection error:", error)
  eventSource.close()
  showError("Connection lost. Please refresh.")
}
```

---

## Backend Implementation

### Emitting Events

```python
from app.services.sse_helpers import emit_streaming_event

# Progress event
await emit_streaming_event(
    "progress",
    analysis_id=str(analysis_id),
    stage="extraction",
    status="running",
    word_count=5234
)

# Complete event
await emit_streaming_event(
    "complete",
    analysis_id=str(analysis_id),
    stage="artifact_generation",
    status="complete",
    artifact_id=str(artifact_id),
    trace_id=trace_id  # Optional Langfuse trace ID
)

# Error event
await emit_streaming_event(
    "error",
    analysis_id=str(analysis_id),
    stage="extraction",
    status="failed",
    error="URL not found (404)",
    error_code="EXTRACTION_FAILED"
)
```

---

## Event Flow

1. **Workflow starts** → Emit `progress` with `status: "pending"`
2. **Task begins** → Emit `progress` with `status: "running"`
3. **Task completes** → Emit `progress` with `status: "complete"`
4. **All tasks done** → Emit `complete` event
5. **Error occurs** → Emit `error` event

**Typical Sequence:**
```
progress (extraction, pending)
progress (extraction, running)
progress (extraction, complete)
progress (supervisor_routing, pending)
progress (supervisor_routing, running)
progress (tech_comparison, running)
progress (tech_comparison, complete)
...
progress (artifact_generation, running)
progress (artifact_generation, complete)
complete (artifact_id: ...)
```

---

## Validation

**Backend:**
- All events must include: `type`, `analysis_id`, `stage`, `status`, `timestamp`
- `analysis_id` must be valid UUID
- `stage` must be one of defined stage names
- `status` must be one of: `pending`, `running`, `complete`, `failed`
- `timestamp` must be ISO 8601 format

**Frontend:**
- Validate event structure before processing
- Handle missing or malformed events gracefully
- Log validation errors for debugging

---

## Versioning

**Current Version:** 1.0

**Breaking Changes:**
- None (initial version)

**Future Additions:**
- Additional stage names (non-breaking)
- Additional `details` fields (non-breaking)
- New event types (may require frontend updates)

---

**Last Updated:** January 2025  
**Maintained By:** Backend Team (Yonatan)

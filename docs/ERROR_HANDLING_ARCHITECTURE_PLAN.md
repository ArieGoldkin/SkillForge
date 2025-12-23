# Error Handling Architecture Plan - Production-Grade Failure Management

**Date**: December 22, 2025  
**Status**: Research & Planning  
**Goal**: Implement production-grade error handling with retry strategies, proper propagation, and observability

---

## 🎯 Core Principles

### 1. Error Classification (Transient vs Permanent)

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR CLASSIFICATION MATRIX                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TRANSIENT ERRORS (Retryable)                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Network timeouts (HTTP 408, 503, 504)                  │   │
│  │ • Rate limiting (HTTP 429)                                │   │
│  │ • Service unavailable (HTTP 503)                          │   │
│  │ • Database connection pool exhaustion                     │   │
│  │ • LLM API rate limits / throttling                        │   │
│  │ • Temporary embedding service unavailability              │   │
│  │                                                           │   │
│  │ Retry Strategy: Exponential backoff with jitter         │   │
│  │ Max Retries: 3-5 attempts                                 │   │
│  │ Backoff: 1s, 2s, 4s, 8s, 16s                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  PERMANENT ERRORS (Fail Fast)                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Invalid URL (HTTP 404, 400)                            │   │
│  │ • Authentication failures (HTTP 401, 403)                 │   │
│  │ • Malformed content (parsing errors)                      │   │
│  │ • Validation errors (schema mismatches)                   │   │
│  │ • Quality gate failures (after max retries)               │   │
│  │ • Configuration errors                                    │   │
│  │                                                           │   │
│  │ Retry Strategy: No retry (fail immediately)               │   │
│  │ Action: Emit error event, update status, propagate to UI │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  PARTIAL FAILURES (Graceful Degradation)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Agent failures (some agents succeed, others fail)       │   │
│  │ • Quality gate warnings (low quality but acceptable)      │   │
│  │ • Missing optional data                                  │   │
│  │                                                           │   │
│  │ Retry Strategy: Continue with available data              │   │
│  │ Action: Emit warning, log, continue workflow             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Error Propagation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR PROPAGATION ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Error Occurs in Workflow Node                         │   │
│  │    │                                                      │   │
│  │    ├─ Classify error (transient/permanent/partial)       │   │
│  │    ├─ Extract error_code from exception                 │   │
│  │    ├─ Determine retry eligibility                        │   │
│  │    └─ Emit error event with metadata                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. Error Event Emission                                  │   │
│  │    │                                                      │   │
│  │    ├─ SSE Event (real-time to frontend)                  │   │
│  │    │   └─ {type: "error", stage, error_code, message}    │   │
│  │    │                                                      │   │
│  │    ├─ Database Persistence (historical tracking)         │   │
│  │    │   └─ analysis_progress table                         │   │
│  │    │                                                      │   │
│  │    ├─ Structured Logging (observability)                 │   │
│  │    │   └─ structlog with error_code, stage, context      │   │
│  │    │                                                      │   │
│  │    └─ Langfuse Trace (LLM observability)                 │   │
│  │        └─ Error metadata, scores, retry_count             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│        ┌──────────────────┼──────────────────┐                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Frontend │      │ Langfuse │      │  Logs   │              │
│  │   UI     │      │  Trace   │      │          │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│        │                  │                  │                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Display  │      │ Track    │      │ Monitor  │              │
│  │ Error    │      │ LLM      │      │ & Alert  │              │
│  │ Code     │      │ Errors   │      │          │              │
│  │          │      │          │      │          │              │
│  │ Show     │      │ Score    │      │ Metrics  │              │
│  │ User-    │      │ Quality  │      │          │              │
│  │ Friendly │      │          │      │          │              │
│  │ Message  │      │          │      │          │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture Components

### Component 1: Error Classifier

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR CLASSIFIER SERVICE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Purpose: Classify errors and determine retry strategy          │
│                                                                  │
│  Input: Exception + Context                                     │
│  Output: ErrorClassification                                    │
│                                                                  │
│  ErrorClassification:                                          │
│  {                                                              │
│    "type": "transient" | "permanent" | "partial",             │
│    "error_code": "EXTRACTION_TIMEOUT",                         │
│    "retryable": true,                                           │
│    "max_retries": 3,                                           │
│    "backoff_strategy": "exponential",                          │
│    "user_message": "Network timeout. Retrying...",             │
│    "langfuse_tags": ["error", "retryable", "extraction"],      │
│  }                                                              │
│                                                                  │
│  Classification Rules:                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • HTTP 408, 429, 503, 504 → transient                   │   │
│  │ • HTTP 404, 400, 401, 403 → permanent                    │   │
│  │ • TimeoutError → transient                                │   │
│  │ • ValueError, TypeError → permanent                      │   │
│  │ • EmbeddingError (rate limit) → transient                │   │
│  │ • EmbeddingError (auth) → permanent                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 2: Retry Strategy Manager

```
┌─────────────────────────────────────────────────────────────────┐
│              RETRY STRATEGY MANAGER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Purpose: Execute retries with appropriate backoff              │
│                                                                  │
│  Strategies:                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Exponential Backoff (default for transient)            │   │
│  │    • Base delay: 1s                                        │   │
│  │    • Multiplier: 2x                                        │   │
│  │    • Max delay: 30s                                        │   │
│  │    • Jitter: ±20%                                          │   │
│  │    • Formula: delay = min(base * (2^attempt) + jitter,   │   │
│  │                        max_delay)                          │   │
│  │                                                           │   │
│  │ 2. Linear Backoff (for rate limits)                       │   │
│  │    • Base delay: 5s                                       │   │
│  │    • Increment: 5s per attempt                             │   │
│  │    • Max delay: 60s                                        │   │
│  │                                                           │   │
│  │ 3. Fixed Delay (for specific services)                     │   │
│  │    • Delay: 2s (constant)                                  │   │
│  │                                                           │   │
│  │ 4. No Retry (for permanent errors)                        │   │
│  │    • Fail immediately                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Retry Flow:                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ attempt = 0                                               │   │
│  │ while attempt < max_retries:                              │   │
│  │   try:                                                    │   │
│  │     result = await operation()                            │   │
│  │     return result                                         │   │
│  │   except TransientError as e:                              │   │
│  │     attempt += 1                                          │   │
│  │     delay = calculate_backoff(attempt)                   │   │
│  │     await emit_retry_event(attempt, delay)                 │   │
│  │     await asyncio.sleep(delay)                            │   │
│  │   except PermanentError as e:                             │   │
│  │     raise  # Fail immediately                             │   │
│  │ raise MaxRetriesExceeded()                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component 3: Enhanced Error Event

```
┌─────────────────────────────────────────────────────────────────┐
│              ENHANCED ERROR EVENT STRUCTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current (Basic):                                               │
│  {                                                              │
│    "type": "error",                                            │
│    "stage": "extraction",                                       │
│    "error": "Extraction failed",                               │
│    "error_code": "EXTRACTION_FAILED"                          │
│  }                                                              │
│                                                                  │
│  Enhanced (Production-Grade):                                   │
│  {                                                              │
│    "type": "error",                                            │
│    "analysis_id": "uuid",                                      │
│    "stage": "extraction",                                       │
│    "status": "failed",                                         │
│    "timestamp": "2025-12-22T13:00:00Z",                        │
│                                                                  │
│    // Error Details                                            │
│    "error": "Network timeout after 30s",                       │
│    "error_code": "EXTRACTION_TIMEOUT",                         │
│    "error_type": "transient",                                  │
│    "error_category": "network",                                │
│                                                                  │
│    // Retry Information                                        │
│    "retryable": true,                                          │
│    "retry_count": 2,                                           │
│    "max_retries": 3,                                           │
│    "next_retry_in": 4,  // seconds                             │
│    "retry_strategy": "exponential_backoff",                    │
│                                                                  │
│    // User-Facing Information                                  │
│    "user_message": "Network timeout. Retrying in 4 seconds...",│
│    "user_action": "retry" | "contact_support" | "none",        │
│    "support_url": "https://docs.skillforge.dev/errors/...",   │
│                                                                  │
│    // Observability                                            │
│    "langfuse_trace_id": "trace-123",                           │
│    "langfuse_tags": ["error", "retryable", "extraction"],     │
│    "metrics": {                                                │
│      "duration_ms": 30000,                                    │
│      "attempts": 2,                                           │
│      "backoff_delay_ms": 4000                                 │
│    },                                                          │
│                                                                  │
│    // Context                                                  │
│    "context": {                                                │
│      "url": "https://example.com/article",                    │
│      "content_type": "article",                               │
│      "stage_duration_ms": 30000                                │
│    }                                                           │
│  }                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Orchestrator Fix (No Backward Compatibility)

### Current Problem

```
┌─────────────────────────────────────────────────────────────────┐
│              CURRENT ORCHESTRATOR FLOW (BROKEN)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Workflow executes                                           │
│     │                                                            │
│     ├─ Node fails (e.g., embedding)                             │
│     ├─ Sets should_abort=True                                   │
│     ├─ Routes to workflow_failed node                          │
│     └─ Returns: {workflow_status: "failed", final_error: "..."} │
│                                                                  │
│  2. Orchestrator receives result                               │
│     │                                                            │
│     ├─ ❌ PROBLEM: Always validates result                      │
│     ├─ ❌ PROBLEM: Missing fields → tries to update status     │
│     ├─ ❌ PROBLEM: Status already "failed" → conflict         │
│     └─ ❌ ERROR: Invalid transition                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Fixed Orchestrator Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              FIXED ORCHESTRATOR FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Execute Workflow                                            │
│     result = await analysis_workflow.ainvoke(...)               │
│                                                                  │
│  2. Check Workflow Status (MANDATORY)                           │
│     workflow_status = result.get("workflow_status")            │
│                                                                  │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ IF workflow_status == "failed":                       │   │
│     │                                                       │   │
│     │   ✅ Workflow already handled failure                 │   │
│     │   ✅ Status already set by workflow_failed node      │   │
│     │   ✅ Error events already emitted                     │   │
│     │   ✅ Langfuse trace already updated                   │   │
│     │                                                       │   │
│     │   → Extract error details from result                 │   │
│     │   → Log orchestrator completion                      │   │
│     │   → Return early (no validation/persistence)          │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ ELIF workflow_status == "completed":                 │   │
│     │                                                       │   │
│     │   ✅ Validate result (expect complete data)          │   │
│     │   ✅ Persist data                                    │   │
│     │   ✅ Validate artifact                               │   │
│     │   ✅ Update status to "complete"                     │   │
│     │   ✅ Emit completion event                           │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ ELSE (workflow_status missing):                      │   │
│     │                                                       │   │
│     │   ❌ ERROR: Invalid workflow state                   │   │
│     │   → Log error with full context                     │   │
│     │   → Update status to "failed"                        │   │
│     │   → Emit error event                                │   │
│     │   → Raise WorkflowError                             │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔁 Retry Implementation Strategy

### Strategy 1: Node-Level Retries (Embedding, Extraction)

```
┌─────────────────────────────────────────────────────────────────┐
│              NODE-LEVEL RETRY PATTERN                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Example: generate_embedding_node                               │
│                                                                  │
│  async def generate_embedding_node(state):                      │
│      analysis_id = state["analysis_id"]                         │
│      content = state["raw_content"]                             │
│                                                                  │
│      # Classify error and get retry strategy                    │
│      error_classifier = ErrorClassifier()                       │
│      retry_manager = RetryStrategyManager()                     │
│                                                                  │
│      async def attempt_embedding():                             │
│          try:                                                    │
│              embedding = await embedding_service.generate(...)   │
│              return embedding                                  │
│          except EmbeddingError as e:                             │
│              classification = error_classifier.classify(e)     │
│                                                                  │
│              if not classification.retryable:                   │
│                  # Permanent error - fail immediately            │
│                  await emit_error_event(                        │
│                      analysis_id,                               │
│                      stage="embedding",                         │
│                      error=e,                                   │
│                      error_code=classification.error_code,     │
│                      retryable=False,                           │
│                  )                                              │
│                  raise                                          │
│                                                                  │
│              # Transient error - will retry                      │
│              raise  # Let retry_manager handle it               │
│                                                                  │
│      # Execute with retry strategy                              │
│      try:                                                        │
│          embedding = await retry_manager.execute(              │
│              attempt_embedding,                                 │
│              max_retries=3,                                     │
│              backoff_strategy="exponential",                    │
│              on_retry=lambda attempt, delay: emit_retry_event(   │
│                  analysis_id, "embedding", attempt, delay        │
│              ),                                                 │
│          )                                                       │
│          return {"content_embedding": embedding}                │
│      except MaxRetriesExceeded:                                 │
│          # All retries exhausted                                │
│          await emit_error_event(                                │
│              analysis_id,                                       │
│              stage="embedding",                                 │
│              error="Max retries exceeded",                     │
│              error_code="EMBEDDING_MAX_RETRIES_EXCEEDED",       │
│              retry_count=3,                                    │
│          )                                                      │
│          # Set abort signal                                     │
│          return {                                               │
│              "should_abort": True,                              │
│              "abort_reason": "Embedding generation failed after 3 retries",│
│          }                                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Strategy 2: Workflow-Level Retries (Quality Gate)

```
┌─────────────────────────────────────────────────────────────────┐
│              WORKFLOW-LEVEL RETRY PATTERN                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current: Quality gate retries synthesis (already implemented)  │
│                                                                  │
│  Enhanced: Add retry for other critical stages                  │
│                                                                  │
│  Example: Supervisor selection retry                           │
│                                                                  │
│  async def supervisor_node(state):                              │
│      retry_count = state.get("supervisor_retry_count", 0)       │
│      max_retries = 2                                            │
│                                                                  │
│      try:                                                        │
│          decision = await supervisor_route(...)                 │
│          return {"supervisor_decision": decision}                │
│      except SupervisorError as e:                               │
│          classification = error_classifier.classify(e)         │
│                                                                  │
│          if classification.retryable and retry_count < max_retries:│
│              # Retry supervisor selection                      │
│              await emit_retry_event(                           │
│                  analysis_id,                                  │
│                  stage="supervisor",                            │
│                  attempt=retry_count + 1,                       │
│                  delay=calculate_backoff(retry_count),         │
│              )                                                 │
│              return {                                           │
│                  "supervisor_retry_count": retry_count + 1,     │
│                  "should_retry_supervisor": True,               │
│              }                                                 │
│          else:                                                  │
│              # Fail permanently                                │
│              await emit_error_event(...)                        │
│              return {"should_abort": True, ...}                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Observability Integration

### Langfuse Error Tracking

```
┌─────────────────────────────────────────────────────────────────┐
│              LANGFUSE ERROR TRACKING                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Enhanced Trace Metadata:                                       │
│  {                                                              │
│    "error_code": "EXTRACTION_TIMEOUT",                         │
│    "error_type": "transient",                                  │
│    "retryable": true,                                          │
│    "retry_count": 2,                                           │
│    "max_retries": 3,                                           │
│    "stage": "extraction",                                      │
│    "tags": ["error", "retryable", "extraction", "timeout"],   │
│    "metadata": {                                               │
│      "url": "https://example.com/article",                    │
│      "duration_ms": 30000,                                     │
│      "backoff_delay_ms": 4000                                  │
│    }                                                           │
│  }                                                             │
│                                                                  │
│  Error Scoring:                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ • Track error frequency per error_code                    │   │
│  │ • Track retry success rate                                │   │
│  │ • Track error recovery time                               │   │
│  │ • Alert on error rate spikes                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend Error Display

```
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND ERROR DISPLAY ENHANCEMENT                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Current: Basic error code display                              │
│                                                                  │
│  Enhanced: Rich error information                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [Stage: Extraction]                                       │   │
│  │ ❌ Network timeout                                        │   │
│  │                                                           │   │
│  │ Retrying in 4 seconds... (Attempt 2 of 3)                │   │
│  │                                                           │   │
│  │ Error Code: EXTRACTION_TIMEOUT                            │   │
│  │ [Learn More] [Contact Support]                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Error Code Mapping:                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ EXTRACTION_TIMEOUT → "Network timeout. Retrying..."      │   │
│  │ EXTRACTION_404 → "URL not found. Please check the URL."  │   │
│  │ EMBEDDING_RATE_LIMIT → "Rate limited. Retrying..."       │   │
│  │ QUALITY_GATE_FAILED → "Quality below threshold..."      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Plan

### Phase 1: Error Classification (Foundation)

**Files to Create/Modify:**
- `backend/app/core/error_classifier.py` (NEW)
- `backend/app/core/exceptions.py` (ENHANCE - add error types)

**Tasks:**
1. Create `ErrorClassifier` service
2. Add error type classification (transient/permanent/partial)
3. Add error code mapping
4. Add user message generation
5. Add retry strategy determination

**Acceptance Criteria:**
- ✅ Classifies HTTP errors correctly
- ✅ Classifies timeout errors as transient
- ✅ Classifies validation errors as permanent
- ✅ Returns structured `ErrorClassification` object

---

### Phase 2: Retry Strategy Manager

**Files to Create/Modify:**
- `backend/app/core/retry_manager.py` (NEW)
- `backend/app/core/config.py` (ADD retry config)

**Tasks:**
1. Create `RetryStrategyManager` service
2. Implement exponential backoff
3. Implement linear backoff
4. Implement fixed delay
5. Add retry event emission hooks
6. Add max retries configuration

**Acceptance Criteria:**
- ✅ Executes retries with correct backoff
- ✅ Emits retry events to SSE
- ✅ Handles max retries exceeded
- ✅ Supports different backoff strategies

---

### Phase 3: Enhanced Error Events

**Files to Create/Modify:**
- `backend/app/shared/services/messaging/sse_helpers.py` (ENHANCE)
- `frontend/src/schemas/sse.ts` (ENHANCE)

**Tasks:**
1. Enhance `emit_error_event` with retry info
2. Add `emit_retry_event` function
3. Update SSE schema with new fields
4. Update frontend type definitions
5. Add user message generation

**Acceptance Criteria:**
- ✅ Error events include retry information
- ✅ Retry events are emitted during retries
- ✅ Frontend receives enhanced error data
- ✅ User-friendly messages displayed

---

### Phase 4: Orchestrator Fix (No Backward Compat)

**Files to Modify:**
- `backend/app/domains/analysis/services/workflow/orchestrator.py`

**Tasks:**
1. Check `workflow_status` before validation
2. Skip validation for `workflow_status="failed"`
3. Extract error details from failed workflow result
4. Log orchestrator completion
5. Remove legacy handling (no backward compat)

**Acceptance Criteria:**
- ✅ No validation for failed workflows
- ✅ No status transition conflicts
- ✅ Proper error extraction and logging
- ✅ Clean early return for failures

---

### Phase 5: Node-Level Retries

**Files to Modify:**
- `backend/app/domains/analysis/workflows/tasks/generate_embedding.py`
- `backend/app/domains/analysis/workflows/tasks/extract_content.py`
- `backend/app/domains/analysis/workflows/nodes/supervisor.py`

**Tasks:**
1. Add retry logic to embedding generation
2. Add retry logic to content extraction
3. Add retry logic to supervisor selection
4. Integrate error classifier
5. Integrate retry manager

**Acceptance Criteria:**
- ✅ Transient errors are retried
- ✅ Permanent errors fail immediately
- ✅ Retry events are emitted
- ✅ Max retries respected

---

### Phase 6: Status Transition Fix

**Files to Modify:**
- `backend/app/domains/analysis/services/persistence/status_updater.py`

**Tasks:**
1. Allow refinement transitions (failed → specific)
2. Add refinement detection logic
3. Update transition rules
4. Add logging for refinements

**Acceptance Criteria:**
- ✅ Generic "failed" can be refined to specific type
- ✅ Invalid transitions still rejected
- ✅ Refinement transitions logged

---

### Phase 7: Langfuse Integration

**Files to Modify:**
- `backend/app/core/tracing.py`
- `backend/app/core/langfuse_service.py`

**Tasks:**
1. Add error metadata to traces
2. Add retry information to traces
3. Add error tags
4. Track error metrics

**Acceptance Criteria:**
- ✅ Errors visible in Langfuse
- ✅ Retry attempts tracked
- ✅ Error codes in metadata
- ✅ Tags for filtering

---

### Phase 8: Frontend Enhancement

**Files to Modify:**
- `frontend/src/features/analysis/components/progress/StageItem.tsx`
- `frontend/src/features/analysis/utils/errorCodeFormatter.ts`
- `frontend/src/features/analysis/hooks/useAnalysisProgress.ts`

**Tasks:**
1. Display retry information
2. Show user-friendly messages
3. Add error code help links
4. Display retry countdown

**Acceptance Criteria:**
- ✅ Retry information displayed
- ✅ User-friendly error messages
- ✅ Error code help links work
- ✅ Retry countdown visible

---

## 📐 Architecture Validation

### Best Practices Compliance

```
┌─────────────────────────────────────────────────────────────────┐
│              BEST PRACTICES CHECKLIST                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ Error Classification                                        │
│     ├─ Transient vs permanent distinction                       │
│     ├─ Appropriate retry strategies                             │
│     └─ User-friendly error messages                            │
│                                                                  │
│  ✅ Retry Strategies                                            │
│     ├─ Exponential backoff with jitter                         │
│     ├─ Max retries respected                                   │
│     ├─ Retry events emitted                                    │
│     └─ Graceful failure after max retries                      │
│                                                                  │
│  ✅ Error Propagation                                           │
│     ├─ SSE events (real-time)                                  │
│     ├─ Database persistence (historical)                      │
│     ├─ Structured logging (observability)                      │
│     └─ Langfuse traces (LLM observability)                     │
│                                                                  │
│  ✅ Observability                                               │
│     ├─ Error codes tracked                                     │
│     ├─ Retry metrics tracked                                   │
│     ├─ Error frequency monitored                               │
│     └─ Alerts on error spikes                                  │
│                                                                  │
│  ✅ User Experience                                             │
│     ├─ Clear error messages                                   │
│     ├─ Retry status visible                                    │
│     ├─ Error code help links                                   │
│     └─ Actionable guidance                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Complete Flow Visualization

### Enhanced Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              COMPLETE ERROR HANDLING FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Error Occurs                                          │   │
│  │    try:                                                  │   │
│  │        result = await operation()                        │   │
│  │    except Exception as e:                                │   │
│  │        classification = classifier.classify(e)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│        ┌──────────────────┼──────────────────┐                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │Transient │      │Permanent │      │ Partial  │              │
│  │          │      │          │      │          │              │
│  │ Retry    │      │ Fail     │      │ Continue │              │
│  │          │      │          │      │          │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│        │                  │                  │                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ Retry    │      │ Emit     │      │ Emit     │              │
│  │ Manager  │      │ Error    │      │ Warning  │              │
│  │          │      │ Event    │      │ Event    │              │
│  │ Backoff  │      │          │      │          │              │
│  │ Retry    │      │ Update   │      │ Continue │              │
│  │          │      │ Status   │      │ Workflow │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│        │                  │                  │                  │
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. Propagate to All Channels                             │   │
│  │    ├─ SSE Event (frontend)                                │   │
│  │    ├─ Database (historical)                              │   │
│  │    ├─ Structured Log (observability)                     │   │
│  │    └─ Langfuse Trace (LLM observability)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Summary

### New Components

1. **ErrorClassifier** - Classifies errors and determines retry strategy
2. **RetryStrategyManager** - Executes retries with backoff
3. **Enhanced Error Events** - Rich error information with retry details
4. **Status-Aware Orchestrator** - Respects workflow status, no validation for failures

### Modified Components

1. **Orchestrator** - Check workflow_status before validation
2. **Status Updater** - Allow refinement transitions
3. **SSE Helpers** - Enhanced error events
4. **Workflow Nodes** - Add retry logic
5. **Frontend** - Enhanced error display

### Configuration

- Retry strategies (exponential, linear, fixed)
- Max retries per error type
- Backoff parameters
- Error code mappings
- User message templates

---

**Status**: Ready for Implementation  
**Estimated Time**: 8-10 hours  
**Dependencies**: None (can be implemented incrementally)

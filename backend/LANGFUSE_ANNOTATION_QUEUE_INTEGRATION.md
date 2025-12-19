# Langfuse Annotation Queue Integration

## Overview

This integration enables SkillForge to automatically queue low-quality artifacts and negative feedback in Langfuse's Annotation Queue for human review. This provides a UI-based workflow for reviewers to annotate and score artifacts.

## Components

### 1. Setup Script (`scripts/setup_langfuse_annotation_queue.py`)

**Purpose:** Check if the annotation queue exists and configure the queue ID.

**Usage:**
```bash
poetry run python scripts/setup_langfuse_annotation_queue.py
```

**What it does:**
- Connects to Langfuse API at `LANGFUSE_HOST`
- Lists all annotation queues via `GET /api/public/annotation-queues`
- Finds queue named "SkillForge Review Queue"
- Automatically updates `.env` with `LANGFUSE_ANNOTATION_QUEUE_ID`
- Provides instructions to create queue if not found

**Environment Variables Required:**
- `LANGFUSE_ENABLED=true`
- `LANGFUSE_PUBLIC_KEY=<your-key>`
- `LANGFUSE_SECRET_KEY=<your-key>`
- `LANGFUSE_HOST=http://localhost:3000` (optional)

### 2. Configuration (`app/core/config.py`)

**New Setting:**
```python
LANGFUSE_ANNOTATION_QUEUE_ID: str | None = Field(
    default=None,
    description="Langfuse Annotation Queue ID for human review workflow"
)
```

**Example `.env` entry:**
```bash
# Langfuse Annotation Queue Configuration
LANGFUSE_ANNOTATION_QUEUE_ID=aq_abc123xyz
```

### 3. Service Integration (`app/core/annotation_service.py`)

**New Method: `_add_to_langfuse_queue()`**

Submits items to Langfuse Annotation Queue via `POST /api/public/annotation-queues/{queueId}/items`

**Payload Format:**
```json
{
  "objectId": "uuid-of-artifact",
  "objectType": "artifact",
  "traceId": "langfuse-trace-id",
  "data": {
    "reason": "low_quality | negative_feedback",
    "quality_scores": {"relevance": 0.5, "depth": 0.4},
    "queued_at": "2025-12-19T13:00:00Z"
  }
}
```

**Updated Method: `_queue_artifact()`**

Now performs dual queuing:
1. **Local database** (existing) - for API access
2. **Langfuse queue** (new) - for UI-based review

**Graceful Degradation:**
- If `LANGFUSE_ANNOTATION_QUEUE_ID` not set → skips Langfuse queue
- If `LANGFUSE_ENABLED=false` → skips Langfuse queue
- If API call fails → logs warning, continues operation
- Always succeeds for local database queuing

## Setup Instructions

### Step 1: Start Langfuse

```bash
docker-compose up -d langfuse-web langfuse-worker
```

### Step 2: Create Annotation Queue

1. Open Langfuse UI: http://localhost:3000
2. Navigate to **Settings → Annotation Queues**
3. Click **Create Queue**
4. Set:
   - Name: `SkillForge Review Queue`
   - Description: `Queue for reviewing SkillForge artifacts`
5. Save

### Step 3: Configure Queue ID

```bash
cd backend
poetry run python scripts/setup_langfuse_annotation_queue.py
```

This will:
- Find the queue ID
- Update `.env` with `LANGFUSE_ANNOTATION_QUEUE_ID=<id>`

### Step 4: Restart Backend

```bash
# Restart to load new env var
docker-compose restart backend
```

## Testing

### Unit Tests

```bash
poetry run pytest tests/unit/core/test_annotation_service.py::TestLangfuseQueueIntegration -v
```

**Coverage:**
- ✅ Successful queue submission
- ✅ Graceful degradation when queue_id not configured
- ✅ Graceful degradation when Langfuse disabled
- ✅ Graceful degradation when credentials missing
- ✅ Graceful degradation on API errors
- ✅ Integration with existing `_queue_artifact()` flow

**All 6 new tests pass ✓**

### Manual Testing

1. **Submit negative feedback:**
```bash
curl -X POST http://localhost:8500/api/v1/annotations/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "<uuid>",
    "trace_id": "<trace-id>",
    "feedback": "thumbs_down",
    "comment": "Not helpful"
  }'
```

2. **Check Langfuse UI:**
   - Go to http://localhost:3000/annotation-queues
   - Find "SkillForge Review Queue"
   - Verify item appears with metadata

3. **Verify local database:**
```bash
# Check annotation_queue table
SELECT * FROM annotation_queue ORDER BY created_at DESC LIMIT 1;
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  DUAL QUEUING ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User Feedback / Quality Gate                                   │
│         │                                                       │
│         ▼                                                       │
│  AnnotationService._queue_artifact()                            │
│         │                                                       │
│         ├─────────────────┬──────────────────┐                 │
│         ▼                 ▼                  ▼                  │
│  Local Database    Langfuse Queue     (Future: Slack)          │
│  (annotation_      (UI-based          (Notifications)          │
│   queue table)      review)                                     │
│         │                 │                                     │
│         ▼                 ▼                                     │
│  API Access        Human Review                                 │
│  GET /queue        Annotations                                  │
│                    Scores                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits

1. **UI-Based Review:** Reviewers can use Langfuse's annotation UI (polished, well-designed)
2. **Centralized Workflow:** All traces, scores, and annotations in one place
3. **Flexible Integration:** Can link artifacts to traces for full context
4. **Graceful Degradation:** Works even if Langfuse is unavailable
5. **Future-Proof:** Easy to add more annotation workflows

## Limitations

- **Queue Creation:** Must be done via UI (no public API for creation)
- **One-Way Sync:** Items are only pushed to Langfuse, not pulled back
- **No Bulk Operations:** Each item submitted individually

## Related Issues

- **#382:** Human Annotation Workflow (this implementation)
- **#378:** Session & User Tracking (trace attribution)
- **#379:** Langfuse Prompt Management
- **#385:** Langfuse MCP Integration

## Files Modified

- ✅ `backend/app/core/config.py` - Added `LANGFUSE_ANNOTATION_QUEUE_ID` setting
- ✅ `backend/app/core/annotation_service.py` - Added Langfuse queue integration
- ✅ `backend/.env.example` - Documented new env var with setup instructions
- ✅ `backend/scripts/setup_langfuse_annotation_queue.py` - New setup script
- ✅ `backend/tests/unit/core/test_annotation_service.py` - Added 6 new tests

## Next Steps

1. **Frontend Integration:** Add UI to display queued items
2. **Score Configs:** Create Langfuse score configs for annotations
3. **Analytics:** Track annotation metrics in Langfuse dashboard
4. **A/B Testing:** Use annotations to measure prompt improvements

---

**Implementation Date:** December 19, 2025
**Status:** ✅ Complete & Tested (28/28 tests passing)

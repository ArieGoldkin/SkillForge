# Silent Failures Fix - Implementation Summary

## Problem
Workflow tasks (aggregation, artifact generation, extraction, embedding) were catching exceptions and returning fallback data without recording errors to the database. This made failures invisible to users and debugging difficult.

## Solution
Added comprehensive error recording to all workflow tasks using a centralized `ErrorRecorder` service.

## Files Created

### 1. Error Code Constants
**File:** `/Users/yonatangross/coding/SkillForge/backend/app/domains/analysis/constants/error_codes.py`

Defines standard error codes for all workflow stages:
- Agent errors: `SECURITY_AUDITOR_FAILED`, `TECH_COMPARATOR_FAILED`, etc.
- Workflow errors: `EXTRACTION_FAILED`, `AGGREGATION_FAILED`, `EMBEDDING_FAILED`, etc.
- Provides `AGENT_ERROR_CODES` mapping for agent type to error code conversion

### 2. Error Recorder Service Enhancement
**File:** `/Users/yonatangross/coding/SkillForge/backend/app/domains/analysis/services/persistence/error_recorder.py`

Added `record_warning()` method for non-fatal errors (G-Eval failures, queue failures, etc.)
- Fatal errors: `record()` - Updates analysis status to "failed" in database
- Non-fatal warnings: `record_warning()` - Logs warning without failing analysis
- Both methods are idempotent and gracefully handle their own failures

### 3. Test Suite
**File:** `/Users/yonatangross/coding/SkillForge/backend/tests/unit/domains/analysis/services/persistence/test_error_recorder.py`

Comprehensive test coverage:
- ✅ Successful error recording
- ✅ Analysis not found (graceful handling)
- ✅ Long message truncation (2000 char limit)
- ✅ Database error handling (doesn't raise)
- ✅ Warning recording (logs only)

## Files Modified

### 1. Aggregation Task
**File:** `app/domains/analysis/workflows/tasks/aggregate_findings.py`

**Changes:**
- `_handle_aggregation_error()` now records errors to database BEFORE returning fallback data
- Uses `AGGREGATION_FAILED` error code
- Stage: `aggregate_findings`

**Code Added:**
```python
from app.domains.analysis.constants.error_codes import AGGREGATION_FAILED
from app.domains.analysis.services.persistence.error_recorder import error_recorder

await error_recorder.record(
    analysis_id=UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id,
    error_code=AGGREGATION_FAILED,
    error_message=str(error),
    stage="aggregate_findings",
)
```

### 2. Artifact Generation Task
**File:** `app/domains/analysis/workflows/tasks/generate_artifact.py`

**Changes:**
- Added warning recording for G-Eval scoring failures (line 227-233)
- Added warning recording for annotation queue failures (line 144-150)
- Both use `record_warning()` to avoid marking analysis as failed

**Code Added:**
```python
# G-Eval failure (non-fatal)
await error_recorder.record_warning(
    analysis_id=UUID(analysis_id),
    warning_code="ARTIFACT_G_EVAL_SCORING_FAILED",
    warning_message=str(e),
    stage="artifact_generation",
)

# Queue failure (non-fatal)
await error_recorder.record_warning(
    analysis_id=UUID(analysis_id),
    warning_code="ARTIFACT_QUEUING_FAILED",
    warning_message=str(e),
    stage="artifact_generation",
)
```

### 3. Content Extraction Task
**File:** `app/domains/analysis/workflows/tasks/extract_content.py`

**Changes:**
- Records errors to database before emitting SSE events and raising exceptions
- Uses `EXTRACTION_FAILED` or JinaReader-specific error codes
- Stage: `extraction`
- Added `noqa: PLR0915` to suppress "too many statements" warning

**Code Added:**
```python
from app.domains.analysis.services.persistence.error_recorder import error_recorder

await error_recorder.record(
    analysis_id=UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id,
    error_code=error_code,
    error_message=str(e),
    stage="extraction",
)
```

### 4. Embedding Generation Task
**File:** `app/domains/analysis/workflows/tasks/generate_embedding.py`

**Changes:**
- Records errors to database in BOTH `generate_embedding()` and `generate_embeddings_batch()`
- Uses `EMBEDDING_FAILED` error code
- Stage: `embedding`

**Code Added:**
```python
from app.domains.analysis.constants.error_codes import EMBEDDING_FAILED
from app.domains.analysis.services.persistence.error_recorder import error_recorder

await error_recorder.record(
    analysis_id=UUID(analysis_id) if isinstance(analysis_id, str) else analysis_id,
    error_code=EMBEDDING_FAILED,
    error_message=str(e),
    stage="embedding",
)
```

## Database Schema
Uses existing fields in `analyses` table:
- `error_code`: String(50) - Error code constant
- `error_message`: Text - Human-readable error (truncated to 2000 chars)
- `failed_at_stage`: String(50) - Workflow stage name
- `status`: Set to "failed" when `record()` is called

## Error Recording Pattern

### Fatal Errors (Analysis Failed)
```python
from app.domains.analysis.constants.error_codes import STAGE_FAILED
from app.domains.analysis.services.persistence.error_recorder import error_recorder

await error_recorder.record(
    analysis_id=analysis_uuid,
    error_code=STAGE_FAILED,
    error_message=str(exception),
    stage="stage_name",
)
```

### Non-Fatal Warnings (Analysis Continues)
```python
from app.domains.analysis.services.persistence.error_recorder import error_recorder

await error_recorder.record_warning(
    analysis_id=analysis_uuid,
    warning_code="WARNING_CODE",
    warning_message=str(exception),
    stage="stage_name",
)
```

## Key Design Decisions

1. **Idempotency**: Recording the same error multiple times doesn't cause issues
2. **Graceful Degradation**: Error recording failures never break the workflow
3. **Separation of Concerns**: Fatal errors vs non-fatal warnings
4. **Consistent Interface**: Same pattern across all workflow tasks
5. **Database First**: Always record to database before emitting SSE events

## Testing
All tests passing:
```bash
# Error recorder tests
poetry run pytest tests/unit/domains/analysis/services/persistence/test_error_recorder.py -v
# ============================== 5 passed in 4.31s ===============================

# Aggregation tests (including error handling)
poetry run pytest tests/unit/domains/analysis/workflows/tasks/test_aggregate_findings.py -v
# ======================= 43 passed, 13 warnings in 5.64s ========================

# All persistence service tests
poetry run pytest tests/unit/domains/analysis/services/persistence/ -v
# ============================= 24 passed in 14.51s ==============================
```

All linting and type checks passing:
```bash
poetry run ruff format --check app/domains/analysis/
poetry run ruff check app/domains/analysis/
poetry run ty check app/domains/analysis/
# All checks passed!
```

## Impact
- ✅ Aggregation failures are now visible in database
- ✅ Extraction failures are recorded before raising
- ✅ Embedding failures are persisted
- ✅ Artifact generation warnings are logged (non-fatal)
- ✅ All errors queryable via `error_code` and `failed_at_stage` fields
- ✅ Comprehensive test coverage ensures reliability

## Future Enhancements
1. Create separate `analysis_warnings` table for non-fatal warnings
2. Add warning count/severity to `analyses` table
3. Dashboard to query/filter by error codes
4. Automatic retry logic based on error codes

## Verification
To verify errors are being recorded:
```sql
-- Check for failed analyses
SELECT id, url, error_code, error_message, failed_at_stage, created_at
FROM analyses
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;

-- Count failures by error code
SELECT error_code, COUNT(*) as count
FROM analyses
WHERE status = 'failed'
GROUP BY error_code
ORDER BY count DESC;

-- Count failures by stage
SELECT failed_at_stage, COUNT(*) as count
FROM analyses
WHERE status = 'failed'
GROUP BY failed_at_stage
ORDER BY count DESC;
```

# Known Bugs & Historical Fixes

This document contains historical bug fixes for reference when debugging similar issues.

> **Note**: This file was extracted from CLAUDE.md to follow best practices of keeping the main config file concise (<60 lines).

---

## SSE Race Condition (Fixed Dec 2025)

- **Problem**: Frontend shows 0% progress, "Waiting for agent activity..." while backend runs
- **Root Cause**: EventBroadcaster had no buffering - events published before SSE subscriber connects were lost
- **Fix**: Added event buffering with `deque(maxlen=100)` per channel, events replayed to new subscribers
- **Location**: `backend/app/services/event_broadcaster.py`
- **Tests**: `backend/tests/unit/test_event_broadcaster.py` (5 buffer tests)

---

## Quality Gate ValidationError (Fixed Dec 2025)

- **Problem**: `pydantic.v1.error_wrappers.ValidationError: 3 validation errors for Run`
- **Root Cause**: LangSmith `Run` schema required `start_time` and `trace_id` fields (pre-Langfuse migration)
- **Fix**: Added `start_time=datetime.now(UTC)` and `trace_id=uuid4()` to mock Run object
- **Location**: `backend/app/workflows/nodes/quality_gate_node.py` lines 102-129
- **Note**: Now using Langfuse for observability (Dec 2025 migration)

---

## Workflow Timeout (Configured Dec 2025)

- **Problem**: Workflow times out during multi-agent execution
- **Fix**: Increased `STEP_TIMEOUT` from 90s to 300s (5 minutes)
- **Location**: `backend/app/core/timeout_config.py`

---

## Redis Connection Keepalive (Fixed Dec 2025)

- **Problem**: "Connection closed by server" errors, semantic cache completely broken
- **Root Cause**: No socket keepalive configured - idle connections >5min dropped by OS/firewall
- **Fix**: Added connection pooling with keepalive, timeouts, health checks, retry policy
- **Location**: `backend/app/shared/services/cache/redis_connection.py` (NEW)
- **Config**: `backend/app/core/config.py` (5 new REDIS_* settings)
- **Tests**: `backend/tests/unit/shared/services/cache/test_redis_connection.py`

---

## G-Eval Gemini Response Parsing (Fixed Dec 2025)

- **Problem**: "Failed to parse judge response: [{'type': 'text', 'text': '10', ...}]"
- **Root Cause**: Gemini (Dec 2025+) returns dict format, parser expected simple string
- **Fix**: Added `_extract_text_from_llm_response()` to handle Gemini's dict format
- **Location**: `backend/app/shared/services/g_eval/scorer.py:129-154`
- **Tests**: `backend/tests/unit/evaluation/test_quality_evaluator.py::test_parse_gemini_dict_response`

---

## Quality Truncation Limits (Fixed Dec 2025)

- **Problem**: Depth scores 5/10 (AWFUL), content truncated before evaluation
- **Root Cause**: Aggressive truncation (200-2000 chars) destroyed analytical depth
- **Fix**: Increased limits: scorer 2000→8000, quality 8000→15000, compression 200→500
- **Location**: Multiple files (scorer.py, quality.py, compress_findings.py, quality_gate_node.py)
- **Docs**: `docs/QUALITY_INITIATIVE_FIXES.md` for full details

---

## Artifact API Endpoint (Fixed Dec 2025)

- **Problem**: GET /api/v1/artifacts/{id} returns 404
- **Root Cause**: Endpoint never defined, only /download variant existed
- **Fix**: Added `get_artifact_by_id()` route exposing existing repository method
- **Location**: `backend/app/api/v1/artifacts.py`
- **Tests**: `backend/tests/unit/api/v1/test_artifacts.py`

---

## UI Status Contradiction (Fixed Dec 2025)

- **Problem**: Green "Complete" badge shown despite failed stages
- **Root Cause**: Status logic didn't account for partial failures
- **Fix**: Show "Complete with Errors" (red) when failures exist, added error details display
- **Location**: `frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx`

---

## CI Marker Override (Fixed Dec 2025)

- **Problem**: Tests marked `@pytest.mark.slow` still ran in CI, causing flaky failures
- **Root Cause**: CI used `-m "not external"` which OVERRIDES default `addopts` from pytest.ini
- **Fix**: Updated `.github/workflows/backend-ci.yml` to use `-m "not slow and not external"`
- **Location**: `.github/workflows/backend-ci.yml:185`
- **Note**: When CI command includes `-m`, it replaces (not extends) the default marker filter

---

## Retrieval Ranking Quality (Improved Dec 2025)

- **Problem**: Expected chunks ranked 6-10 instead of top-5 (91.1% pass rate)
- **Root Cause**: Query-time tsvector (5-10x slower), low fetch multiplier, no metadata boosting
- **Fix**:
  1. Use pre-indexed `content_tsvector` column (5-10x faster)
  2. Increase `HYBRID_FETCH_MULTIPLIER` from 2x to 3x for better RRF coverage
  3. Add section title boosting (1.5x) when query matches section
  4. Add document path boosting (1.15x) when query matches path
  5. Add technical query detection for code_block boosting (1.2x)
  6. Dynamic `top_k` in evaluation based on expected chunks count
- **Location**: `backend/app/db/repositories/chunk_repository.py`, `backend/app/shared/services/search/search_service.py`
- **Constants**: `backend/app/core/constants.py` (HYBRID_FETCH_MULTIPLIER, SECTION_TITLE_BOOST_FACTOR, etc.)
- **Tests**: `backend/tests/unit/services/search/test_search_service.py` (20 tests)
- **Results**: 185/203 → 186/203 (+0.5%), Hard MRR 0.647 → 0.686 (+6%)

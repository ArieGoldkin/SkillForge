# Issue #378: Add Session & User Tracking to Langfuse Traces

**Status:** 📋 Planned
**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** Langfuse Migration Phase 2
**Priority:** ⚡ HIGH
**Estimated Effort:** 1-2 hours
**Dependencies:** Issue #372 (Langfuse Migration) ✅ Complete

---

## Summary

Add `session_id` and `user_id` tracking to all Langfuse traces, enabling:
- **Session grouping**: Group all traces for a single analysis or tutoring session
- **User analytics**: Track activity per user in Langfuse dashboard
- **Conversation tracking**: Enable multi-turn tutoring session analysis
- **Foundation for auth**: Prepare infrastructure for future authentication

## Key Features

- Session ID format: `analysis-{uuid}` or `tutor-{uuid}`
- Default user_id: `"anonymous"` (until auth implemented)
- Automatic propagation to nested traces
- No breaking changes (additive only)
- Session visibility in Langfuse UI

## Current State

### ✅ What's Working
- Langfuse v3 SDK integrated with `@observe` decorator
- `update_current_trace()` already supports `session_id` and `user_id`
- Workflow runner sets `session_id` for analysis (line 320)
- Tutor nodes use `session_id` (assess_readiness.py line 79)

### ❌ What's Missing
- Inconsistent session_id usage across nodes
- No user_id tracking (defaults to None)
- Some workflow tasks don't set session context
- API layer missing user extraction (auth not implemented)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  SESSION TRACKING ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ANALYSIS WORKFLOW                                               │
│  ═════════════════                                              │
│  POST /api/v1/analysis/analyze                                  │
│       ↓                                                          │
│  workflow_runner.py                                              │
│       → session_id = f"analysis-{analysis_id}"                  │
│       → user_id = "anonymous"                                    │
│       → update_current_trace(session_id, user_id)               │
│       ↓                                                          │
│  [Workflow Nodes]                                               │
│       → extract_content (inherit session)                        │
│       → supervisor (inherit session)                             │
│       → 8 agents (inherit session)                              │
│       → aggregate (inherit session)                              │
│       → quality_gate (inherit session)                           │
│       → generate_artifact (inherit session)                      │
│                                                                 │
│  TUTOR WORKFLOW                                                 │
│  ═════════════                                                  │
│  POST /api/v1/tutor/sessions                                    │
│       ↓                                                          │
│  tutor_graph.py                                                  │
│       → session_id = f"tutor-{session_id}"                      │
│       → user_id = "anonymous"                                    │
│       ↓                                                          │
│  [Tutor Nodes]                                                  │
│       → generate_syllabus (inherit session)                      │
│       → deliver_lesson (inherit session)                         │
│       → ask_socratic (inherit session)                           │
│       → ... (all tutor nodes)                                    │
│                                                                 │
│  LANGFUSE UI                                                    │
│  ═══════════                                                    │
│  Sessions Tab → Grouped traces by session_id                    │
│  Users Tab → Activity by user_id                                │
│  Analytics → Per-user cost, latency, quality                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Checklist

### Phase 1: Core Infrastructure (2 hours)

- [ ] **Update workflow_runner.py** (15 min)
  - Add `user_id="anonymous"` to update_current_trace()
  - Verify session_id is passed to all workflow nodes

- [ ] **Update 8 agent nodes** (1 hour)
  - Add `update_current_trace()` at function start
  - Extract `analysis_id` from state
  - Set `session_id=f"analysis-{analysis_id}"`, `user_id="anonymous"`
  - Files:
    - `tech_comparator_node.py`
    - `security_auditor_node.py`
    - `performance_analyst_node.py`
    - `dependency_mapper_node.py`
    - `trend_validator_node.py`
    - `integration_feasibility_node.py`
    - `code_quality_critic_node.py`
    - `implementation_planner_node.py`

- [ ] **Update workflow tasks** (30 min)
  - `extract_content.py`
  - `generate_embedding.py`
  - `aggregate_findings.py`
  - `generate_artifact.py` (already has update_current_trace)

- [ ] **Update supervisor and quality gate** (15 min)
  - `supervisor.py`
  - `quality_gate_node.py`

### Phase 2: Tutor Workflow (30 min)

- [ ] **Verify tutor nodes** (all 7 files)
  - Ensure consistent `session_id=str(session_id)` pattern
  - Add `user_id="anonymous"` to all nodes
  - Files:
    - `ask_socratic.py`
    - `assess_readiness.py`
    - `conduct_review.py`
    - `deliver_lesson.py`
    - `final_challenge.py`
    - `generate_syllabus.py`
    - `guide_reflection.py`
    - `rephrase_explain.py`

### Phase 3: Testing (1 hour)

- [ ] **Unit tests**
  - Create `test_session_tracking.py` (analysis)
  - Create `test_session_tracking.py` (tutor)
  - Update `test_tracing.py` with session/user scenarios

- [ ] **Integration testing**
  - Start Langfuse: `docker-compose up -d langfuse-web`
  - Run analysis workflow
  - Verify session_id in Langfuse UI
  - Run tutor session
  - Verify tutor traces grouped

- [ ] **Validation checklist**
  - [ ] Analysis workflow: Root trace has session_id
  - [ ] Analysis workflow: All agent nodes inherit session_id
  - [ ] Analysis workflow: user_id = "anonymous"
  - [ ] Tutor workflow: Root trace has session_id
  - [ ] Tutor workflow: All nodes inherit session_id
  - [ ] Langfuse UI: Sessions tab shows grouped traces
  - [ ] Langfuse UI: User analytics shows "anonymous"

## Session ID Patterns

### Analysis Workflow
```python
session_id = f"analysis-{analysis_id}"
# Example: "analysis-550e8400-e29b-41d4-a716-446655440000"
```

### Tutor Workflow
```python
session_id = str(session_id)  # Already a UUID
# Example: "7c9e6679-7425-40de-944b-e07fc1f90ae7"
# Note: Don't add "tutor-" prefix (keep clean for DB FK)
```

## Code Pattern

```python
from app.core.tracing import update_current_trace

@robust_traceable(name="agent_name", run_type="chain")
async def agent_node(state: AnalysisState, config: RunnableConfig) -> dict:
    # FIRST: Update trace context
    analysis_id = state["analysis_id"]
    update_current_trace(
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",  # Will be dynamic after auth
        metadata={"agent_name": "tech_comparator"},
    )

    # THEN: Execute node logic
    ...
```

## Edge Cases & Error Handling

### Missing analysis_id
```python
analysis_id = state.get("analysis_id")
if analysis_id:
    update_current_trace(session_id=f"analysis-{analysis_id}", user_id="anonymous")
else:
    logger.warning("Missing analysis_id in state, skipping session tracking")
```

### Nested workflows
- Langfuse automatically propagates session_id to child traces
- No special handling needed

### Langfuse unavailable
- `update_current_trace()` has try/except (tracing.py lines 154-177)
- Fails silently - app continues without tracing

## Acceptance Criteria

### Functional Requirements
- [ ] All analysis workflow traces include `session_id="analysis-{uuid}"`
- [ ] All tutor workflow traces include `session_id="tutor-{uuid}"`
- [ ] All traces include `user_id="anonymous"`
- [ ] Session IDs propagate to nested traces
- [ ] Langfuse UI groups traces by session_id
- [ ] Langfuse UI shows "anonymous" user

### Code Quality
- [ ] All modified files pass linting: `ruff format --check && ruff check && ty check`
- [ ] Test coverage ≥80% maintained
- [ ] New session tracking tests pass
- [ ] Existing tests still pass

### Traceability
- [ ] Every agent node sets session_id and user_id
- [ ] Workflow runner sets session_id before invocation
- [ ] Tutor nodes consistently use session_id from state
- [ ] No hardcoded user IDs

## Future Enhancements (Out of Scope)

- **User Authentication**: Extract user_id from JWT tokens
- **Per-User Analytics**: Langfuse dashboard filtering by user
- **Session Metadata**: Add skill_level, analysis_type to metadata
- **Cross-Session Analytics**: Track user journey across analyses

## Files to Modify

### Core (1 file)
- `backend/app/core/tracing.py` - Document session/user patterns

### Analysis Workflow (16 files)
- `backend/app/api/v1/analysis/workflow_runner.py` - Add user_id
- `backend/app/domains/analysis/workflows/nodes/agents/*.py` (8 files)
- `backend/app/domains/analysis/workflows/tasks/*.py` (4 files)
- `backend/app/domains/analysis/workflows/nodes/supervisor.py`
- `backend/app/domains/analysis/workflows/nodes/quality_gate_node.py`

### Tutor Workflow (8 files)
- `backend/app/api/v1/tutor/sessions.py`
- `backend/app/domains/tutor/workflows/nodes/*.py` (7 files)

### Testing (3 new + updates)
- `backend/tests/unit/core/test_tracing.py` (update)
- `backend/tests/unit/api/v1/analysis/test_session_tracking.py` (new)
- `backend/tests/unit/domains/tutor/test_session_tracking.py` (new)

## Related Issues

- **#372**: Langfuse Migration (dependency, complete)
- **#383**: Token/Cost Tracking (complementary)
- **#379**: Prompt Management (uses sessions for A/B testing)

## Resources

- [Langfuse Sessions Documentation](https://langfuse.com/docs/observability/features/sessions)
- [Langfuse User Tracking](https://langfuse.com/docs/user-explorer)
- [LangGraph + Langfuse Discussion](https://github.com/orgs/langfuse/discussions/7331)

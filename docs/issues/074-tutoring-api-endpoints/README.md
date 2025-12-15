# Issue 74 – Tutoring API Endpoints

## Summary
Implement real tutoring endpoints (REST + SSE) to replace the current frontend mock. Provide session/message CRUD, streaming tutor replies, and structured error handling.

## Scope
- REST: create session, get session (includes message history), post user message, update session status.
- SSE: stream tutor workflow events (progress, chunk, done, error) per session.
- Validation, logging with `request_id`, DI-wired repositories, and repo-pattern compliance.
- Align with LangGraph tutor workflow (#213) and persistence (#79).

## Proposed Endpoints
- `POST /api/v1/tutor/sessions` → create session, return `session_id`.
- `GET /api/v1/tutor/sessions/{session_id}` → session metadata.
- `POST /api/v1/tutor/sessions/{session_id}/messages` → submit user message; triggers workflow continuation.
- `PATCH /api/v1/tutor/sessions/{session_id}` → update session status (completed/abandoned).
- `GET /api/v1/tutor/sessions/{session_id}/stream` → SSE for progress/chunks/done/error.

## SSE Event Shapes
- `progress`: `{type="progress", session_id, stage, status, timestamp, ...}`
- `chunk`: `{type="chunk", session_id, stage, status, timestamp, content, index?}`
- `done`: `{type="done", session_id, stage, status, timestamp, ...}`
- `error`: `{type="error", session_id, stage, status, timestamp, error, ...}`

## Dependencies
- #79 Tutoring Session Persistence (models/repos/migrations)
- #213 Tutoring LangGraph Workflow & SSE
- #214 Tutoring API Contract & Integration Coverage
- Frontend #113 TutorChat to consume these endpoints/streams

## Acceptance Criteria
- All endpoints respond with validated schemas; 404/422 handled explicitly.
- SSE stream emits typing → chunk(s) → final (or error) and cleans up with `aclosing()`.
- request_id propagated to logs and SSE events.
- Tests: integration coverage for REST + SSE shapes using test DB and stubbed workflow.

## Open Questions
- Pagination/limit defaults for message history.
- Token/latency budgets for tutor replies.
- Auth not in scope unless specified later.


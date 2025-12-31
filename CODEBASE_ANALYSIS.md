# Codebase Analysis - SkillForge

**Date:** December 31, 2025  
**Purpose:** Analyze current patterns, inconsistencies, and conventions to inform CONVENTIONS.md

---

## 1. Patterns Currently Observed

### Architecture Patterns

**Backend:**
- **Repository Pattern** - Consistently used across database operations (`IAnalysisRepository`, `IArtifactRepository`)
- **Dependency Injection** - FastAPI `Depends()` pattern used throughout
- **Service Layer** - Clear separation: `app/services/`, `app/shared/services/`
- **Domain-Driven Structure** - `app/domains/analysis/`, `app/domains/tutor/`
- **LangGraph Workflows** - Functional API with `@entrypoint` and `@task` decorators

**Frontend:**
- **Feature-Based Organization** - `src/features/analysis/`, `src/features/library/`
- **Shared Components** - `src/shared/components/`, `src/shared/hooks/`
- **Zustand State Management** - Store pattern for SSE and analysis state
- **TanStack Router** - File-based routing with type-safe params
- **React 19** - Server components patterns, modern hooks

### Coding Styles

**Python (Backend):**
- Type hints: **MANDATORY** (enforced in `.cursorrules`)
- Async/await: Used consistently for I/O operations
- Structured logging: `structlog` with event-based logging (not f-strings)
- File size limits: 200 lines (source), 150 lines (repositories), 300 lines (tests)
- Function complexity: Max 5 parameters, max 4 nesting levels, max 15 cyclomatic complexity

**TypeScript (Frontend):**
- TypeScript strict mode enabled
- ESLint rules: Max 180 lines per file, max 50 lines per function, max 4 depth
- React hooks: All dependencies declared, `useCallback`/`useMemo` for optimization
- Named exports preferred over default exports for components
- Import order: React → external → internal → shared → features

### Naming Conventions

**Backend:**
- Functions: `snake_case` (e.g., `get_analysis`, `create_workflow`)
- Classes: `PascalCase` (e.g., `WorkflowOrchestrator`, `AnalysisRepository`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- Private methods: Leading underscore (`_handle_task_completion`)
- Type hints: Full annotations required

**Frontend:**
- Components: `PascalCase` (e.g., `AnalyzeResult`, `StageItem`)
- Functions/hooks: `camelCase` (e.g., `useAnalysisProgress`, `getStageDescription`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CONTENT_TYPE_ICONS`)
- Props interfaces: `ComponentNameProps` suffix
- Selectors: `select*` prefix (e.g., `selectEvents`, `selectConnectionState`)

### Error Handling Patterns

**Backend:**
- Custom exceptions: `app.core.exceptions` module (e.g., `SkillForgeException`, `ConfigurationError`)
- Structured error responses: `ErrorResponse` schema with `code`, `message`, `details`
- HTTP status codes: 200, 201, 400, 404, 422, 500
- Logging: `logger.error()` with structured context, never expose internal errors to clients
- Exception handling: Specific exception types, not bare `except:`

**Frontend:**
- Error boundaries: Not yet implemented (potential gap)
- API error handling: Consistent `APIError` interface
- User feedback: Error messages from backend, no stack traces

---

## 2. Inconsistencies Found

### Backend Inconsistencies

1. **Function Size Violations:**
   - `backend/app/api/v1/analysis/library.py:55` - `get_library()` function marked with `# noqa: PLR0913, PLR0912, PLR0915` (too many params, too many branches, too many statements)
   - Multiple files approaching/exceeding 200-line limit

2. **TODO Comments:**
   - Found 10+ files with TODO/FIXME comments (should be tracked in issues per `.cursorrules`)
   - Examples: `backend/app/api/v1/analysis/endpoints.py`, `backend/app/domains/analysis/workflows/agents/community_pulse.py`

3. **Import Organization:**
   - Some files have inconsistent import ordering (standard library → third-party → local)
   - Ruff should enforce this, but some legacy files may not follow

4. **Error Handling Variations:**
   - Some endpoints use `HTTPException` directly, others use custom exception handlers
   - GeneratorExit handling is consistent (good), but some nodes may not use `robust_traceable`

### Frontend Inconsistencies

1. **File Size:**
   - `frontend/src/features/analysis/AnalyzeResult.tsx` - 306 lines (exceeds 180-line limit)
   - ESLint disable comments used (`/* eslint-disable max-lines */`)

2. **Export Patterns:**
   - Mix of named exports (`export function`) and default exports
   - Some components use `memo()` wrapper, others don't (inconsistency in optimization)

3. **Type Safety:**
   - Some components use `any` or `unknown` (should use `unknown` per rules)
   - Interface vs type alias inconsistency (both used, no clear preference)

4. **Error Handling:**
   - No error boundaries implemented (React best practice)
   - Error handling scattered across components, not centralized

### Cross-Stack Inconsistencies

1. **Type Definitions:**
   - Backend uses Pydantic schemas, frontend should regenerate TypeScript types
   - Manual type definitions may drift from backend (see `docs/INTEGRATION_POINTS.md`)

2. **API Response Formats:**
   - Backend returns consistent `ErrorResponse`, but frontend may not handle all error codes uniformly

---

## 3. Code Smells Identified

### Backend

1. **Large Function:**
   - `get_library()` function violates complexity rules (too many parameters, branches, statements)
   - Should be refactored into smaller functions

2. **Comment Suppression:**
   - Multiple `# noqa` comments indicate violations that should be fixed
   - Examples: `PLR0913` (too many args), `PLR0915` (too many statements)

3. **Legacy Patterns:**
   - Some files in `app/evaluation/` have relaxed linting rules (experimental code)
   - `app/workflows/studio_compat.py` marked as placeholder (dead code?)

### Frontend

1. **Large Files:**
   - `AnalyzeResult.tsx` exceeds 180-line limit with ESLint disable comment
   - Should be split into smaller components

2. **Complex Selectors:**
   - Zustand selectors are consolidated (good), but some could be memoized better
   - Multiple re-renders possible with current selector pattern

3. **Missing Patterns:**
   - No error boundaries (React best practice for production)
   - No centralized error handling service

---

## 4. Implicit Conventions

### Backend

1. **Workflow Patterns:**
   - All LangGraph nodes emit SSE events via `emit_streaming_event()`
   - All nodes use `@robust_traceable` for Langfuse observability
   - State dictionaries use typed keys (not plain dicts)

2. **Repository Pattern:**
   - All repositories implement interface protocols (`I*Repository`)
   - Dependency injection via FastAPI `Depends()`
   - Async methods only (`async def`)

3. **Testing:**
   - Test files mirror source structure: `tests/unit/app/...`
   - Pytest fixtures in `conftest.py`
   - Mock external dependencies (APIs, LLMs)

### Frontend

1. **Component Structure:**
   - Components exported as named exports
   - Props interfaces defined inline or adjacent
   - Hooks extracted to `hooks/` subdirectories

2. **State Management:**
   - Zustand stores in `stores/` directory
   - Selectors consolidated to reduce re-renders
   - Actions grouped in store file

3. **Routing:**
   - TanStack Router with file-based routes
   - Route params typed via `getRouteApi()`
   - No manual route definitions

---

## 5. Technical Debt Markers

### Backend

1. **Dead Code:**
   - `app/workflows/studio_compat.py` - marked as placeholder, not imported anywhere
   - `app/shared/services/quality_scorer.py` - unused legacy scorer (per coverage config)

2. **Temporary Solutions:**
   - `app/evaluation/` directory has relaxed linting (experimental code)
   - Some TODOs marked for future refactoring

3. **Legacy Patterns:**
   - Some agent files use older patterns (should migrate to LangGraph v1.0 functional API)

### Frontend

1. **Disabled Rules:**
   - ESLint disable comments for file size limits indicate technical debt
   - Some components need refactoring to meet size constraints

2. **Missing Patterns:**
   - Error boundaries not implemented
   - No centralized error handling service

3. **Type Generation:**
   - Manual TypeScript types may drift from backend Pydantic schemas
   - Should automate type generation from backend schemas

---

## 6. Specific File References

### Files Exceeding Size Limits

**Backend:**
- `backend/app/api/v1/analysis/endpoints.py` - 772 lines (should be split)
- `backend/app/api/v1/analysis/library.py` - Large function with complexity violations

**Frontend:**
- `frontend/src/features/analysis/AnalyzeResult.tsx` - 306 lines (exceeds 180)
- `frontend/src/shared/components/ui/*.stories.tsx` - Some story files may be large

### Files with TODO Comments

- `backend/app/api/v1/analysis/endpoints.py` - Multiple TODOs
- `backend/app/domains/analysis/workflows/agents/community_pulse.py`
- `backend/app/shared/services/mcp/README_INTERCEPTORS.md`

### Files with Code Smells

- `backend/app/api/v1/analysis/library.py:55` - Complex function (`get_library()`)
- `frontend/src/features/analysis/AnalyzeResult.tsx` - Large file with disabled linting

---

## Summary

**Strengths:**
- Clear architectural patterns (Repository, Service Layer, Domain-Driven)
- Strong type safety (mandatory type hints, TypeScript strict)
- Consistent async/await patterns
- Structured logging with context
- Modern frameworks (LangGraph v1.0, React 19, TanStack Router)

**Weaknesses:**
- Some files exceed size limits (technical debt)
- TODO comments in code (should be in issues)
- Missing error boundaries in frontend
- Large functions need refactoring
- Some inconsistencies in export patterns

**Recommendations:**
1. Create CONVENTIONS.md documenting target state vs current state
2. Refactor large files/functions incrementally
3. Implement error boundaries in frontend
4. Automate TypeScript type generation from backend
5. Track TODOs in issue tracker, remove from code

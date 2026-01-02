# SkillForge Project Conventions

**Purpose:** Guide LLM code generation to match project standards and target architecture patterns.

---

## Architecture

### Backend Architecture
- **Pattern:** Domain-Driven Design with Repository Pattern
- **Layers:** API → Services → Repositories → Database
- **Dependency Injection:** FastAPI `Depends()` for all repositories and services
- **Async First:** All I/O operations use `async/await`, `AsyncSession` for database

### Frontend Architecture
- **Pattern:** Feature-Based Organization with Shared Components
- **State Management:** Zustand stores for global state, React hooks for local state
- **Routing:** TanStack Router with file-based routes and type-safe params
- **React Version:** React 19 with modern patterns (Server Components where applicable)

### Workflow Orchestration
- **Pattern:** LangGraph v1.0 Functional API (`@entrypoint`, `@task`)
- **Observability:** All nodes use `@robust_traceable` for Langfuse tracing
- **SSE Events:** All workflow nodes emit SSE events via `emit_streaming_event()`
- **Checkpointing:** PostgreSQL-based checkpoints for workflow state persistence

---

## Naming Conventions

### Backend (Python)

**Functions & Variables:**
- `snake_case` for all functions and variables
- Descriptive names: `get_analysis_by_id`, `create_workflow_orchestrator`
- Private functions: Leading underscore `_handle_task_completion`

**Classes:**
- `PascalCase` for classes: `WorkflowOrchestrator`, `AnalysisRepository`
- Interface protocols: `I*` prefix (`IAnalysisRepository`)

**Constants:**
- `UPPER_SNAKE_CASE`: `MAX_RETRIES`, `DEFAULT_TIMEOUT`

**Type Hints:**
- Always use type hints for function parameters and return values
- Never use `Any` - use `Unknown` or proper types
- Use `from typing import TYPE_CHECKING` for forward references

### Frontend (TypeScript)

**Components:**
- `PascalCase` for components: `AnalyzeResult`, `StageItem`
- Export as named exports: `export function ComponentName() {}`
- Props interfaces: `ComponentNameProps` suffix

**Functions & Hooks:**
- `camelCase` for functions and hooks: `useAnalysisProgress`, `getStageDescription`
- Hooks: `use*` prefix, utilities: descriptive verb + noun

**Constants:**
- `UPPER_SNAKE_CASE`: `CONTENT_TYPE_ICONS`, `MAX_RETRIES`

**Types & Interfaces:**
- Prefer `interface` for object shapes, `type` for unions/intersections
- Generic types: `T*` prefix where applicable

---

## Error Handling

### Backend

**Exception Types:**
- Custom exceptions inherit from `SkillForgeException` (in `app.core.exceptions`)
- Specific exceptions: `ConfigurationError`, `ContentTypeError`, etc.
- Never use bare `except:` - always catch specific exception types

**Error Responses:**
- Use `ErrorResponse` schema with `code`, `message`, `details` fields
- HTTP status codes: 200 (Success), 201 (Created), 400 (Bad Request), 404 (Not Found), 422 (Unprocessable Entity), 500 (Internal Server Error)

**Logging:**
- Use `structlog` via `get_logger(__name__)`
- Structured logging with event names: `logger.info("workflow_extraction_complete", analysis_id=id, ...)`
- Never use f-strings in logging - pass as structured fields
- Never expose internal errors to clients - sanitize error messages

### Frontend

**Error Handling:**
- Catch API errors and display user-friendly messages
- Never show stack traces to users
- Use error boundaries (to be implemented) for component tree error handling
- Centralized error handling via error service (to be implemented)

**API Error Format:**
```typescript
interface APIError {
  error: {
    code: string;      // "INVALID_URL", "NOT_FOUND", etc.
    message: string;   // Human-readable error
    details?: object;  // Optional extra context
  }
}
```

---

## Code Style

### Backend (Python)

**File Size Limits:**
- Source files: **200 lines maximum** (refactor when approaching)
- Repository files: **150 lines maximum**
- Service files: **200 lines maximum**
- Test files: **300 lines maximum**

**Function Complexity:**
- Maximum parameters: **5 per function**
- Maximum nesting depth: **4 levels**
- Maximum cyclomatic complexity: **15**

**Code Formatting:**
- Ruff formatter (line length: 100)
- Import order: Standard library → Third-party → Local
- Type hints: Always required

**Async Patterns:**
- Use `async/await` for all I/O operations
- Use `AsyncSession` for database operations
- Use `async` context managers (`async with`)
- Use `aclosing()` for async generator cleanup

### Frontend (TypeScript)

**File Size Limits:**
- Source files: **180 lines maximum** (skip blank lines and comments)
- Components: Should be smaller, extract hooks and utilities when possible
- Test files: No strict limit, but prefer focused tests

**Function Complexity:**
- Maximum lines per function: **50 lines** (skip blank lines and comments)
- Maximum nesting depth: **4 levels**
- Maximum cyclomatic complexity: **15**
- Maximum parameters: **4 per function**

**Code Formatting:**
- Biome formatter (preferred) or ESLint auto-fix
- Import order: React → External → Internal (@/**) → Shared → Features
- Semicolons: Yes (enforced by ESLint)

**React Patterns:**
- Use functional components with hooks
- Extract custom hooks to `hooks/` subdirectories
- Use `useCallback`/`useMemo` for expensive computations
- Declare all hook dependencies explicitly

---

## ⚠️ CRITICAL: This Codebase Is in Transition

### What the agent currently sees (DO NOT replicate):

**Backend:**
- Some files exceed 200-line limit (e.g., `backend/app/api/v1/analysis/endpoints.py` - 772 lines)
- Complex functions with many parameters/branches (e.g., `get_library()` with `# noqa` suppressions)
- TODO comments in code (should be tracked in issues, not in code)
- Some legacy patterns in `app/evaluation/` directory (experimental code with relaxed linting)
- Dead code: `app/workflows/studio_compat.py` (placeholder, not imported)

**Frontend:**
- Some files exceed 180-line limit with ESLint disable comments (e.g., `AnalyzeResult.tsx` - 306 lines)
- Missing error boundaries (React best practice)
- No centralized error handling service
- Mix of export patterns (named vs default) - prefer named exports
- Some components not using `memo()` where they should for optimization

**Cross-Stack:**
- TypeScript types manually maintained (may drift from backend Pydantic schemas)
- Should automate type generation from backend (documented but not implemented)

### Target state (ALWAYS use for new code):

**Backend:**
- All files under 200 lines (source), 150 lines (repositories)
- All functions under complexity limits (5 params, 15 complexity, 4 nesting)
- All TODOs tracked in GitHub issues, removed from code
- Consistent async/await patterns with proper cleanup
- Repository pattern with dependency injection for all database access
- Structured logging with `structlog`, never f-strings
- All workflow nodes use `@robust_traceable` with metadata
- All workflow nodes emit SSE events

**Frontend:**
- All files under 180 lines
- All functions under 50 lines
- Error boundaries implemented for component tree error handling
- Centralized error handling service
- Consistent named exports (no default exports for components)
- Proper use of `memo()` for expensive components
- All hooks dependencies explicitly declared
- Zustand selectors consolidated to reduce re-renders

**Cross-Stack:**
- Automated TypeScript type generation from backend Pydantic schemas
- Consistent API error handling across all endpoints
- Type-safe routing with TanStack Router

### When refactoring existing code:

- **Always move toward target state** - Don't replicate legacy patterns even if surrounding code uses them
- **Flag large files for decomposition** - Any file over 200 lines (backend) or 180 lines (frontend) should be split
- **Remove TODO comments** - Create GitHub issues and link them, remove TODOs from code
- **Fix complexity violations** - Break down large functions, extract helpers
- **Add missing patterns** - Error boundaries, centralized error handling, etc.

---

## Agent-Specific Instructions

When generating code for this project:

### Backend (Python)

1. **Check existing patterns before creating new:**
   - Look for similar functionality in `app/domains/` or `app/shared/services/`
   - Prefer extending existing repositories over creating new ones
   - Reuse existing exception types rather than creating new ones

2. **Always follow these patterns:**
   - Repository pattern with interface protocols (`I*Repository`)
   - Dependency injection via FastAPI `Depends()`
   - Structured logging with `structlog` (event names, structured fields)
   - Type hints for all functions (never use `Any`, use `Unknown` if needed)
   - Async/await for all I/O operations
   - SSE event emission in all workflow nodes

3. **Workflow nodes must:**
   - Use `@robust_traceable` decorator with metadata
   - Emit SSE events via `emit_streaming_event()` (start and complete)
   - Use proper async generator cleanup with `aclosing()`
   - Handle errors gracefully and log with context

4. **Testing:**
   - One test file per source file: `test_{module_name}.py`
   - Mock external dependencies (APIs, LLMs, databases)
   - Use pytest fixtures for common setup
   - Descriptive test names: `test_extract_content_returns_dict_with_content`

### Frontend (TypeScript)

1. **Check existing patterns before creating new:**
   - Look for similar components in `src/features/` or `src/shared/components/`
   - Prefer extending existing hooks over creating new ones
   - Reuse Zustand stores and selectors

2. **Always follow these patterns:**
   - Feature-based organization (components in feature directories)
   - Named exports for components (`export function ComponentName()`)
   - Type-safe routing with TanStack Router `getRouteApi()`
   - Zustand stores in `stores/` directory with consolidated selectors

3. **React components must:**
   - Use functional components with hooks
   - Extract custom hooks to `hooks/` subdirectories
   - Use `useCallback`/`useMemo` for expensive computations
   - Declare all hook dependencies explicitly
   - Handle loading and error states

4. **Type safety:**
   - Never use `any` - use `unknown` if type is truly unknown
   - Prefer `interface` for object shapes, `type` for unions
   - Use TypeScript strict mode patterns
   - Match backend API types (regenerate from Pydantic when backend changes)

5. **Performance:**
   - Use `memo()` for expensive components
   - Consolidate Zustand selectors to reduce re-renders
   - Use `useShallow` for Zustand selectors when needed
   - Lazy load routes/components when appropriate

---

## Testing Standards

### Backend

- **Coverage:** ≥80% (hard block if below)
- **Test Structure:** Mirror source structure: `tests/unit/app/...`
- **Fixtures:** Use `conftest.py` for shared fixtures
- **Mocking:** Mock external dependencies (APIs, LLMs, databases)
- **Test Names:** Descriptive: `test_extract_content_returns_dict_with_content`

### Frontend

- **Coverage:** ≥85% (hard block if below)
- **Test Structure:** Co-located with source or in `__tests__/` directories
- **Testing Library:** React Testing Library for component tests
- **Mocking:** MSW for API mocking, Vitest for unit tests
- **E2E:** Playwright for end-to-end tests

---

## Documentation Standards

### Docstrings (Backend)

- Include docstrings for all public functions/classes
- Use Google-style docstrings:
  ```python
  def extract_content(url: str, analysis_id: str) -> dict:
      """Extract content from URL.
      
      Args:
          url: The URL to extract content from
          analysis_id: Unique identifier for the analysis
          
      Returns:
          Dictionary with 'content', 'title', 'metadata'
          
      Raises:
          JinaReaderError: If extraction fails
      """
  ```

### Code Comments

- Explain **why**, not **what**
- Remove commented-out code
- Update comments when code changes
- No TODO comments in code (track in GitHub issues)

---

## Git Workflow

### Branch Naming
- Feature: `feature/issue-{number}-{description}`
- Bugfix: `bugfix/issue-{number}-{description}`
- Hotfix: `hotfix/{description}`

### Commit Messages
Use conventional commits format:
```
feat: add health check endpoint

- Implement /api/v1/health endpoint
- Add HealthStatus Pydantic model
- Add tests for health check

Closes #1
```

### Pre-Commit Quality Gates

**Backend:**
```bash
ruff check --select=E,F,I,N,W,UP .
ruff format --check .
mypy app
pytest tests/ --cov=app --cov-fail-under=80
```

**Frontend:**
```bash
npm run lint
npm run format:check
npm run typecheck
```

---

## References

- **Backend Rules:** `.cursorrules` (comprehensive Python/FastAPI standards)
- **Frontend Rules:** `frontend/eslint.config.js` (TypeScript/React standards)
- **Architecture:** `docs/ARCHITECTURE.md`
- **API Contract:** `docs/INTEGRATION_POINTS.md`
- **Codebase Analysis:** `CODEBASE_ANALYSIS.md` (current state assessment)

---

**Last Updated:** December 31, 2025  
**Maintained By:** SkillForge Development Team

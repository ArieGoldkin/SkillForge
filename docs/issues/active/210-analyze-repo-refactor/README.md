# Issue 210 – Analyze endpoints repository refactor

## Summary
- Refactored `GET /api/v1/analyze/{id}` and `POST /api/v1/analyze` to use injected repositories (no direct `AsyncSession` access).
- Added repository methods `get_by_id` and `create_analysis` for analyses; reused artifact repository for latest artifact lookups.
- Updated unit/integration tests to align with 200/404 contract and repository injection; adjusted mocks accordingly.
- Skipped external LLM-heavy integration tests when API keys are missing or placeholders to avoid false failures in CI.

## Files touched (high level)
- `backend/app/api/v1/analyze.py` – endpoints now depend on `IAnalysisRepository` / `IArtifactRepository`.
- `backend/app/db/repositories/analysis_repository.py` – added `get_by_id` and `create_analysis`.
- Tests updated across unit/integration suites for the new dependency signatures and behaviors.
- `backend/tests/conftest.py`, `backend/tests/integration/workflows/*`, `backend/tests/unit/api/v1/test_analyze.py` – placeholder-key skips and mock fixes.

## Testing
- `poetry run ruff check .`
- `poetry run mypy app`
- `poetry run pytest --maxfail=1` (LLM/Jina dependent tests skip when keys are placeholder/missing)


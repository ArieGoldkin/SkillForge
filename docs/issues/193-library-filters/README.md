# Issue #193 - Library filters: status/tag not applied

## Summary
Status and tag filters in the Library were not wired to the backend. Selecting statuses or tags did not change results, and the “Show completed only” toggle could override status choices. We mapped filters to backend params, made status single-select (backend limitation), and added tests.

## Scope of work
- Map status filter → backend `status` query param.
- Map tag filter → backend `content_type` query param (article/video/repo).
- Disable “Show completed only” when a status is selected to avoid override.
- Keep client-side filtering only for dimensions not supported by backend (difficulty/duration).
- Add frontend tests for filter mapping and status param wiring.

## Changes (code)
- `frontend/src/features/library/Library.tsx` – map filters to query params; reset pagination on change; disable completed-only when status is chosen.
- `frontend/src/features/library/components/SkillFilters/hooks/useSkillFilters.ts` – single-select status (radio-like).
- `frontend/src/features/library/hooks/useFilteredSkills.ts` – limit client filtering to difficulty/duration.

## Tests
- `npx vitest run src/features/library/__tests__/Library.filters.test.tsx src/features/library/__tests__/filterMapping.test.ts src/features/analysis/hooks/__tests__/useAnalysisStatus.test.ts`
  - Verifies status → backend param mapping, content_type mapping, and status refetch handling.

## Status
- Fix implemented on branch `feature/issue-168-persist-workflow-results`.
- GitHub issue: https://github.com/ArieGoldkin/SkillForge/issues/193


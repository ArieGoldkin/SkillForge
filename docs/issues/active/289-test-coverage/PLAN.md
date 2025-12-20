# Issue #289: Backend Test Coverage 76% → 80%

**Status**: Planning
**Target**: Increase backend test coverage from 76% to 80% (+4%)
**Estimated Effort**: 3-4 days
**Priority**: Medium (Technical Debt)

---

## Executive Summary

This plan provides a structured approach to increase backend test coverage by 4 percentage points. Analysis identified **7 files below 80% threshold** (including 2 at 0%) and **~1,815 lines** needing coverage. The strategy prioritizes high-impact targets with existing test patterns.

```
Coverage Delta Required: 76% → 80% = ~1,815 lines
├── Phase 1: Critical Gaps (0% files)     ~400 lines   [Day 1]
├── Phase 2: High-Impact Targets          ~900 lines   [Day 2-3]
├── Phase 3: Quick Wins                   ~300 lines   [Day 3]
└── Phase 4: Polish (if needed)           ~200 lines   [Day 4]
```

---

## Current State Analysis

### Files Below 80% Threshold

| Priority | File | Coverage | Missing | Impact |
|----------|------|----------|---------|--------|
| P0 | `app/api/dependencies.py` | **0%** | 11 lines | Every endpoint depends on this |
| P0 | `app/workflows/nodes/agent_tools.py` | **0%** | 27 lines | Supervisor routing core |
| P1 | `app/workflows/nodes/parallel_agents.py` | 65.4% | 9 lines | Parallel coordination |
| P1 | `app/workflows/agents/base.py` | 67.7% | 20 lines | Agent creation framework |
| P1 | `app/workflows/agents/response_processing.py` | 68.4% | 6 lines | Response validation |
| P2 | `app/core/agent_config.py` | 71.4% | 6 lines | Agent registry |
| P2 | `app/main.py` | 75.8% | 15 lines | App startup + error handling |

### Under-Tested Critical Paths (High Line Coverage Potential)

| Target | Lines | Current Tests | Est. Coverage Gain |
|--------|-------|---------------|-------------------|
| `db/repositories/chunk_repository.py` | 450 | None | 350-400 lines |
| `api/v1/library.py` | 334 | Basic | 250-300 lines |
| `services/cleanup/orphan_cleanup.py` | 385 | Shallow mocks | 300-350 lines |
| `db/repositories/tutor_*.py` | 464 | None | 280-320 lines |
| `api/v1/analyze.py` | 224 | Limited | 180-220 lines |

---

## Implementation Plan

### Phase 1: Critical Gaps (P0) — Day 1

**Goal**: Eliminate 0% coverage files that affect every request

#### 1.1 Test `app/api/dependencies.py` (0% → 100%)

**Create**: `tests/unit/api/test_dependencies.py`

```python
# Test cases to implement:
class TestGetDatabaseSession:
    async def test_yields_valid_session(self)
    async def test_session_cleanup_on_success(self)
    async def test_session_cleanup_on_exception(self)

class TestGetAppSettings:
    def test_returns_settings_singleton(self)
    def test_settings_cached_across_calls(self)
```

**Fixtures needed**: Mock `AsyncSession`, `Settings`
**Estimated effort**: 1-2 hours
**Lines covered**: ~11

#### 1.2 Test `app/workflows/nodes/agent_tools.py` (0% → 100%)

**Create**: `tests/unit/workflows/nodes/test_agent_tools.py`

```python
# Test cases to implement:
class TestToolDefinitions:
    @pytest.mark.parametrize("tool_func", [
        tech_comparator_tool,
        security_auditor_tool,
        integration_feasibility_tool,
        implementation_planner_tool,
        performance_analyst_tool,
        code_quality_critic_tool,
        trend_validator_tool,
        dependency_mapper_tool,
    ])
    def test_tool_returns_valid_schema(self, tool_func)
    def test_tool_has_name_and_description(self, tool_func)
    def test_tool_schema_matches_agent_input(self, tool_func)

class TestToolToAgentMap:
    def test_all_tools_have_agent_mapping(self)
    def test_agent_mapping_references_valid_agents(self)
    def test_no_duplicate_tool_names(self)

class TestAgentToolsList:
    def test_agent_tools_contains_all_tools(self)
    def test_tools_are_callable(self)
```

**Fixtures needed**: None (pure data validation)
**Estimated effort**: 2-3 hours
**Lines covered**: ~27

---

### Phase 2: High-Impact Targets (P1) — Days 2-3

**Goal**: Cover critical business logic with highest line-count potential

#### 2.1 Test `db/repositories/chunk_repository.py`

**Create**: `tests/unit/db/repositories/test_chunk_repository.py`

```python
# Test cases to implement:
class TestSemanticSearch:
    async def test_search_returns_similar_chunks(self, db_session)
    async def test_search_respects_top_k_limit(self, db_session)
    async def test_search_with_zero_results(self, db_session)
    async def test_search_with_metadata_filter(self, db_session)

class TestKeywordSearch:
    async def test_tsvector_search_matches_terms(self, db_session)
    async def test_search_case_insensitivity(self, db_session)
    async def test_search_with_special_characters(self, db_session)

class TestChunkDeduplication:
    async def test_dedup_removes_exact_duplicates(self, db_session)
    async def test_dedup_preserves_unique_chunks(self, db_session)

class TestMetadataExtraction:
    async def test_extract_metadata_from_chunk(self, db_session)
    async def test_null_metadata_handling(self, db_session)
```

**Fixtures needed**: `db_session`, chunk fixtures with embeddings
**Estimated effort**: 4-5 hours
**Lines covered**: ~350-400

#### 2.2 Test `api/v1/library.py`

**Extend**: `tests/unit/api/test_library.py`

```python
# Additional test cases:
class TestHybridSearch:
    async def test_hybrid_mode_uses_rrf_fusion(self, client)
    async def test_semantic_weight_affects_results(self, client)
    async def test_keyword_weight_affects_results(self, client)

class TestSearchFiltering:
    async def test_filter_by_content_type(self, client)
    async def test_filter_by_status(self, client)
    async def test_filter_combination(self, client)

class TestPagination:
    async def test_pagination_offset_and_limit(self, client)
    async def test_pagination_bounds_validation(self, client)
    async def test_empty_page_returns_empty_list(self, client)

class TestErrorHandling:
    async def test_invalid_search_mode_returns_422(self, client)
    async def test_negative_limit_returns_422(self, client)
```

**Fixtures needed**: `client`, mock `SearchService`
**Estimated effort**: 3-4 hours
**Lines covered**: ~250-300

#### 2.3 Test `workflows/agents/base.py` (67.7% → 90%+)

**Extend**: `tests/unit/workflows/agents/test_base.py`

```python
# Additional test cases:
class TestCreateToolEnabledAgent:
    async def test_creates_agent_with_tools(self)
    async def test_tool_binding_matches_schema(self)
    async def test_error_on_invalid_tool_config(self)

class TestBuildToolEnhancedPrompt:
    def test_prompt_includes_tool_descriptions(self)
    def test_prompt_formatting_with_multiple_tools(self)

class TestSaveAgentFinding:
    async def test_save_finding_success(self, mock_session)
    async def test_save_finding_handles_db_error(self, mock_session)

class TestEmitAgentProgress:
    async def test_emit_progress_broadcasts_event(self)
    async def test_emit_progress_handles_channel_error(self)
```

**Fixtures needed**: `mock_session`, agent fixtures
**Estimated effort**: 3-4 hours
**Lines covered**: ~20

#### 2.4 Test `workflows/agents/response_processing.py` (68.4% → 95%+)

**Extend**: `tests/unit/workflows/agents/test_response_processing.py`

```python
# Additional test cases for error paths:
class TestExtractStructuredResponse:
    def test_invalid_result_type_raises_error(self)
    def test_missing_structured_response_raises_error(self)
    def test_non_pydantic_response_converted(self)
    def test_valid_pydantic_response_returned(self)
```

**Fixtures needed**: Mock agent responses
**Estimated effort**: 1-2 hours
**Lines covered**: ~6

---

### Phase 3: Quick Wins — Day 3

**Goal**: Simple, high-value tests that boost coverage with minimal effort

#### 3.1 Test `services/extraction/content_type.py`

**Create**: `tests/unit/services/extraction/test_content_type.py`

```python
class TestContentTypeDetection:
    @pytest.mark.parametrize("url,expected", [
        ("https://example.com/article", "article"),
        ("https://github.com/org/repo", "repo"),
        ("https://youtube.com/watch?v=xyz", "video"),
        # Edge cases
        ("HTTPS://GITHUB.COM/ORG/REPO", "repo"),  # Case insensitivity
        ("http://example.com", "article"),  # No path
        ("", None),  # Empty
    ])
    def test_detect_content_type(self, url, expected)

class TestURLValidation:
    def test_invalid_url_format_raises_error(self)
    def test_missing_scheme_raises_error(self)
```

**Estimated effort**: 1 hour
**Lines covered**: ~50-70

#### 3.2 Test `services/embeddings_utils.py`

**Create**: `tests/unit/services/test_embeddings_utils.py`

```python
class TestVectorNormalization:
    def test_l2_normalize_unit_vector(self)
    def test_l2_normalize_zero_vector(self)
    def test_l2_normalize_large_values(self)
    def test_normalize_preserves_direction(self)
```

**Estimated effort**: 30 minutes
**Lines covered**: ~30-40

#### 3.3 Test `core/utils.py`

**Extend**: `tests/unit/core/test_utils.py`

```python
class TestUUIDNormalization:
    def test_valid_uuid_passthrough(self)
    def test_invalid_uuid_generates_uuid5(self)
    def test_consistent_uuid5_generation(self)
    def test_empty_string_handling(self)
```

**Estimated effort**: 30 minutes
**Lines covered**: ~50-65

#### 3.4 Test `core/agent_config.py` (71.4% → 90%+)

**Extend**: `tests/unit/core/test_agent_config.py`

```python
class TestGetAgentConfig:
    def test_valid_agent_type_returns_config(self)
    def test_invalid_agent_type_raises_keyerror(self)
    def test_logs_warning_for_unknown_agent(self)
```

**Estimated effort**: 1 hour
**Lines covered**: ~6

---

### Phase 4: Polish (If Needed) — Day 4

#### 4.1 Test `app/main.py` (75.8% → 85%+)

```python
class TestLifespanStartup:
    async def test_exception_handler_setup(self)
    async def test_langfuse_connection_success(self)
    async def test_langfuse_connection_fallback(self)

class TestExceptionHandlers:
    async def test_skillforge_exception_handler(self, client)
    async def test_global_exception_handler(self, client)
```

**Estimated effort**: 2-3 hours
**Lines covered**: ~15

#### 4.2 Test `workflows/nodes/parallel_agents.py` (65.4% → 85%+)

```python
class TestParallelAgentExecution:
    async def test_parallel_execution_collects_results(self)
    async def test_error_aggregation_from_multiple_agents(self)
    async def test_partial_failure_handling(self)
```

**Estimated effort**: 2-3 hours
**Lines covered**: ~9

---

## Test File Structure

```
tests/
├── unit/
│   ├── api/
│   │   ├── test_dependencies.py          [NEW - Phase 1]
│   │   └── test_library.py               [EXTEND - Phase 2]
│   ├── core/
│   │   ├── test_agent_config.py          [EXTEND - Phase 3]
│   │   └── test_utils.py                 [EXTEND - Phase 3]
│   ├── db/
│   │   └── repositories/
│   │       └── test_chunk_repository.py  [NEW - Phase 2]
│   ├── services/
│   │   ├── extraction/
│   │   │   └── test_content_type.py      [NEW - Phase 3]
│   │   └── test_embeddings_utils.py      [NEW - Phase 3]
│   └── workflows/
│       ├── agents/
│       │   ├── test_base.py              [EXTEND - Phase 2]
│       │   └── test_response_processing.py [EXTEND - Phase 2]
│       └── nodes/
│           ├── test_agent_tools.py       [NEW - Phase 1]
│           └── test_parallel_agents.py   [EXTEND - Phase 4]
```

---

## Verification Checklist

After implementation, verify:

```bash
# Run full coverage report
cd backend
poetry run pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Check specific files hit 80%+
poetry run pytest --cov=app/api/dependencies --cov-fail-under=80
poetry run pytest --cov=app/workflows/nodes/agent_tools --cov-fail-under=80
poetry run pytest --cov=app/workflows/agents/base --cov-fail-under=80

# Verify no regressions
poetry run pytest tests/unit/ -v
poetry run ruff check app/
poetry run mypy app/
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Database fixtures slow down tests | Use `AsyncMock` for unit tests, reserve DB for integration |
| Agent tools have complex dependencies | Test data structures only, mock LLM calls |
| Coverage calculation varies | Pin pytest-cov version, run same command |
| Tests become flaky | Use deterministic fixtures, avoid time-based assertions |

---

## Definition of Done

- [ ] All 7 files below 80% reach 80%+ coverage
- [ ] New test files follow existing patterns (conftest fixtures, markers)
- [ ] All tests pass locally: `pytest tests/unit/ -v`
- [ ] CI passes: lint + typecheck + tests
- [ ] Coverage report shows 80%+ overall
- [ ] No flaky tests introduced

---

## Appendix: Available Test Fixtures

From `tests/conftest.py`:

| Fixture | Type | Use Case |
|---------|------|----------|
| `client` | Sync | FastAPI TestClient |
| `db_session` | Async | Database with auto-rollback |
| `test_settings` | Sync | Override app settings |
| `create_test_analysis` | Async | Create Analysis records |
| `mock_session` | Sync | AsyncMock for DB session |
| `requires_database` | Skip | Skip if no DATABASE_URL |
| `requires_llm` | Skip | Skip if no LLM API key |

From `tests/unit/workflows/agents/conftest.py`:

| Fixture | Type | Use Case |
|---------|------|----------|
| `mock_session` | Sync | Pre-configured AsyncMock session |
| `mock_agent` | Sync | Mock agent with ainvoke |

---

*Plan created: 2025-12-12*
*Target completion: 3-4 days*

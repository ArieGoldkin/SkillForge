# Test Analysis: Context Engineering Tests

## Executive Summary

**Critical Finding**: The tests labeled as "integration tests" in `tests/integration/workflows/` are **not actual integration tests**. They use `unittest.mock.patch` for all database and external service interactions, making them functionally equivalent to unit tests.

**Impact**: No tests validate actual database interactions, memory storage/retrieval, or the integration between components against real PostgreSQL.

---

## Test Classification Matrix

| Test File | Location | Label | **Actual Type** | Uses Real DB? | Uses Real LLM? |
|-----------|----------|-------|-----------------|---------------|----------------|
| `test_aggregate_findings.py` | `tests/unit/` | Unit | ✅ Unit | ❌ No | ❌ No |
| `test_runners.py` | `tests/unit/` | Unit | ✅ Unit | ❌ No | ❌ No |
| `test_agent_router.py` | `tests/unit/` | Unit | ✅ Unit | ❌ No | ❌ No |
| `test_context_engineering.py` | `tests/integration/` | Integration | ❌ **Component** | ❌ No | ❌ No |
| `test_context_engineering_scale.py` | `tests/integration/` | Integration | ❌ **Component** | ❌ No | ❌ No |
| `test_agent_routing.py` | `tests/integration/` | Integration | ❌ **Component** | ❌ No | ❌ No |
| `test_semantic_search.py` | `tests/smoke/` | Smoke | ✅ Smoke | ✅ Yes | ✅ Yes |

---

## Detailed Analysis by Test File

### 1. Unit Tests (`tests/unit/`) - ✅ CORRECTLY IMPLEMENTED

#### `test_aggregate_findings.py` (43 tests)
```python
# Pattern: Heavy mocking
with patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize:
    mock_synthesize.return_value = mock_structured_response
```

**Assessment**: ✅ Good unit test patterns
- Properly mocks external dependencies (LLM)
- Tests pure business logic
- Good edge case coverage

#### `test_runners.py` (19 tests)
```python
# Pattern: Mocks database session and agent functions
@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_with_session(...):
```

**Assessment**: ✅ Good unit test patterns
- Tests session management wrappers in isolation
- Properly mocks underlying agent functions

#### `test_agent_router.py` (14 tests)
```python
# Pattern: Mocks memory service
with patch("app.workflows.nodes.agent_router._fetch_agent_memory", new_callable=AsyncMock) as mock_fetch:
    mock_fetch.return_value = "## Relevant Context\n\nSome prior memory..."
```

**Assessment**: ✅ Good unit test patterns
- Tests routing logic without database
- Properly tests edge cases (empty agents, unknown agents)

---

### 2. "Integration" Tests (`tests/integration/`) - ❌ INCORRECTLY LABELED

#### `test_context_engineering.py` (21 tests)

**What it claims to test** (from docstring):
> Integration tests for Sprint 11 Context Engineering features.

**What it actually does**:
```python
# Line 157-161 - Mocks memory fetch
with patch(
    "app.workflows.nodes.agent_router._fetch_agent_memory",
    new_callable=AsyncMock,
) as mock_fetch:
    mock_fetch.return_value = mock_memory

# Line 391-407 - Mocks database session factory
with (
    patch("app.workflows.tasks.aggregate_findings.get_session_factory") as mock_factory,
    patch("app.workflows.tasks.aggregate_findings.AgentMemoryService") as mock_service_class,
):
    mock_session = AsyncMock()
    mock_factory.return_value = MagicMock(return_value=mock_session)
```

**Problems**:
1. ❌ Never uses `db_session` fixture (available in root conftest.py)
2. ❌ Never creates real `AgentMemory` records
3. ❌ Never tests actual PostgreSQL queries
4. ❌ Never tests vector similarity search
5. ❌ Never tests actual embedding generation

#### `test_context_engineering_scale.py` (14 tests)

**What it claims to test**:
> Scale and concurrency tests for Sprint 11 Context Engineering.

**What it actually does**:
```python
# Line 91-105 - All database operations mocked
with (
    patch("app.workflows.tasks.aggregate_findings.get_session_factory") as mock_factory,
    patch("app.workflows.tasks.aggregate_findings.AgentMemoryService") as mock_service_class,
):
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_factory.return_value = MagicMock(return_value=mock_session)
```

**Problems**:
1. ❌ "Concurrency tests" don't test real database concurrency
2. ❌ No connection pool behavior tested
3. ❌ No transaction isolation tested
4. ❌ Scale tests measure Python code, not database performance

---

## Testing Pyramid Violation

```
Current State:                   Best Practice:

    [E2E]  ← Missing             [E2E]   ← Few comprehensive tests
       │                            │
       │                            │
    [Int]  ← MOCKED             [Int]   ← Real DB integration
       │                            │
       │                            │
    [Unit] ← All here            [Unit]  ← Most tests here
       │                            │
  ─────────────                 ─────────────
```

**Current Coverage**:
- Unit tests: 76 tests (but some labeled as integration)
- Real Integration tests: 0 tests
- Smoke tests with real DB: 4 tests (retrieval only)

---

## What Real Integration Tests Should Look Like

### Example from `tests/smoke/retrieval/conftest.py` (lines 213-235)

```python
@pytest_asyncio.fixture
async def smoke_db_session(
    check_database_available,
    reset_engine_connections,
) -> AsyncGenerator[AsyncSession]:
    """Create database session for smoke tests.
    Uses REAL database - no mocking."""
    from app.db.session import AsyncSessionLocal

    session = AsyncSessionLocal()
    try:
        await session.begin()
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### What Context Engineering Integration Tests Should Test:

```python
# ❌ Current approach (mocked)
async def test_store_findings_with_mocked_db():
    with patch("...AgentMemoryService") as mock_service:
        mock_service.store.return_value = MagicMock(id=uuid4())
        # Never actually tests PostgreSQL

# ✅ Recommended approach (real DB)
@pytest.mark.asyncio
async def test_store_findings_with_real_db(db_session, create_test_analysis):
    """Test actual memory storage in PostgreSQL."""
    analysis = await create_test_analysis(
        analysis_id=str(uuid4()),
        url="https://example.com",
    )

    service = AgentMemoryService(db_session)

    # Actually store in PostgreSQL
    memory = await service.store(
        analysis_id=analysis.id,
        agent_type="security_auditor",
        content="SQL injection vulnerability found",
        memory_type=MemoryType.VULNERABILITY_PATTERN,
    )

    # Verify in database
    assert memory.id is not None

    # Test retrieval actually works
    retrieved = await service.fetch_by_analysis(analysis.id)
    assert len(retrieved) == 1
    assert retrieved[0].content == "SQL injection vulnerability found"
```

---

## Specific Issues Found

### Issue 1: Memory Storage Never Tested (#269)

The `_store_findings_as_memories` function is implemented but never tested against real PostgreSQL:

```python
# Production code (aggregate_findings.py:45-293)
async def _store_findings_as_memories(analysis_id: str, agent_findings: list) -> int:
    """Store findings as memories for future analysis context."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = AgentMemoryService(session)
        for finding in agent_findings:
            await service.store(...)  # This is NEVER tested with real DB
```

**Risk**: SQL errors, constraint violations, or transaction issues would only be caught in production.

### Issue 2: Proactive Recall Never Tested (#266)

The memory retrieval path is mocked in all tests:

```python
# Current test (mocked)
mock_fetch.return_value = "## Prior Context\n\n1. Previous SQL injection patterns..."

# What should be tested:
# 1. Actual vector similarity search works
# 2. Memory filtering by agent_type works
# 3. Relevance scoring produces correct ordering
# 4. Large result sets are handled correctly
```

### Issue 3: Context Scoping Performance Claims Unvalidated

```python
# test_context_engineering_scale.py:401-424
def test_scoping_is_fast_for_large_states(self):
    """Test that scoping completes quickly even for large states."""
    # This tests Python dict operations, not database operations
```

This test validates that Python dictionary operations are fast, but doesn't test:
- Database query performance for loading scoped state
- Memory overhead under concurrent requests
- PostgreSQL connection pool behavior

---

## Recommendations

### Option A: Reclassify and Extend (Recommended)

1. **Rename current "integration" tests**:
   ```
   tests/integration/workflows/ → tests/component/workflows/
   ```

2. **Create actual integration tests**:
   ```
   tests/integration/workflows/
   ├── test_memory_storage_integration.py  # Real DB tests for #269
   ├── test_proactive_recall_integration.py  # Real vector search for #266
   ├── test_artifact_loading_integration.py  # Real artifact store for #268
   └── conftest.py  # Uses db_session fixture
   ```

3. **Integration test template**:
   ```python
   @pytest.mark.asyncio
   @pytest.mark.integration
   async def test_memory_storage_integration(
       db_session: AsyncSession,
       create_test_analysis,
   ):
       """Test actual memory storage and retrieval."""
       # 1. Create real analysis in database
       analysis = await create_test_analysis(...)

       # 2. Use real service with real session
       service = AgentMemoryService(db_session)

       # 3. Store real data
       memory = await service.store(...)

       # 4. Verify with actual PostgreSQL query
       result = await db_session.execute(
           select(AgentMemory).where(AgentMemory.id == memory.id)
       )
       assert result.scalar_one() is not None
   ```

### Option B: Accept as Component Tests

If the team decides the current tests provide sufficient coverage:

1. **Update documentation** to clarify these are "component tests"
2. **Add disclaimer** in test files explaining what's mocked
3. **Accept risk** that database-level bugs won't be caught until production

---

## Implementation Plan

### Phase 1: Reclassification (Low Effort)
- [ ] Move `tests/integration/workflows/*.py` to `tests/component/workflows/`
- [ ] Update CI/CD to run component tests separately
- [ ] Document test categories in `backend/tests/README.md`

### Phase 2: Real Integration Tests (Medium Effort)
- [ ] Create `tests/integration/workflows/conftest.py` with DB fixtures
- [ ] Write 5-10 integration tests for critical paths:
  - Memory storage (#269)
  - Memory retrieval (#266)
  - Artifact loading (#268)
- [ ] Add to CI/CD with database service

### Phase 3: Comprehensive Coverage (Higher Effort)
- [ ] Add integration tests for all Context Engineering features
- [ ] Add transaction isolation tests
- [ ] Add concurrent access tests with real DB
- [ ] Add performance benchmarks with real PostgreSQL

---

## Test Coverage Gaps

| Feature | Unit Tests | Integration Tests | Smoke Tests |
|---------|------------|-------------------|-------------|
| Context Scoping | ✅ | ❌ | ❌ |
| Memory Storage (#269) | ✅ (mocked) | ❌ | ❌ |
| Memory Retrieval (#266) | ✅ (mocked) | ❌ | ❌ |
| Artifact Loading (#268) | ✅ (mocked) | ❌ | ❌ |
| Tutor Compiler (#270) | ✅ (mocked) | ❌ | ❌ |
| Session Compaction (#247) | ✅ (mocked) | ❌ | ❌ |
| Vector Search | ❌ | ❌ | ✅ (retrieval only) |

---

## Conclusion

The Context Engineering tests provide good **unit test coverage** of business logic, but **zero integration test coverage** of database interactions. The "integration" label is misleading.

**Recommended action**: Implement Phase 1 (reclassification) immediately, followed by Phase 2 (real integration tests) for critical paths.

---

*Analysis performed: 2025-12-11*
*Sprint: 11 - Context Engineering*

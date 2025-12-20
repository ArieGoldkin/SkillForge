# Test Separation Analysis & Fix Plan

## Problem Statement

Unit tests in `tests/unit/` are making real external calls instead of using mocks:
- **Database connections**: Tests using `AsyncSessionLocal` without proper mocking
- **External APIs**: Tests calling real embedding services, OpenAI, etc.
- **No clear separation**: Tests that should be integration tests are in `tests/unit/`

## Current Issues

### 1. Database Connection Issues

**Files affected:**
- `tests/unit/workflows/tasks/test_runners.py` - Uses `AsyncSessionLocal` without proper mocking
- `tests/unit/workflows/nodes/test_inject_context_node.py` - Uses `get_session_factory` but may not mock properly
- Many other files using database sessions

**Symptoms:**
- `CancelledError` in tests (connection timeouts)
- Tests failing when database is not available
- Slow test execution

### 2. External API Calls

**Files affected:**
- Tests calling `EmbeddingService.generate_embedding()` without mocks
- Tests making real OpenAI API calls
- Tests using real Jina API calls

**Symptoms:**
- Tests requiring API keys
- Tests failing when external services are down
- Slow test execution
- Cost from real API calls

### 3. Missing Test Markers

**Problem:**
- No `@pytest.mark.unit` or `@pytest.mark.integration` markers
- Can't easily filter unit vs integration tests
- All tests run together

## Solution Plan

### Phase 1: Audit & Categorize Tests

1. **Identify unit tests making real calls:**
   ```bash
   # Find tests using real database
   grep -r "AsyncSessionLocal\|get_session_factory" tests/unit/ --include="*.py"
   
   # Find tests using real APIs
   grep -r "EmbeddingService\|OpenAI\|generate_embedding" tests/unit/ --include="*.py"
   ```

2. **Categorize each test:**
   - **True Unit Test**: No external calls, all dependencies mocked
   - **Integration Test**: Uses real database or external services
   - **Needs Fixing**: Unit test making real calls (should be mocked)

### Phase 2: Fix Unit Tests (Add Mocks)

**For database operations:**
```python
# ❌ BAD: Real database connection
async def test_something():
    async with AsyncSessionLocal() as session:
        # This tries to connect to real DB
        result = await some_function(session)

# ✅ GOOD: Mocked session
@patch("app.db.session.AsyncSessionLocal")
async def test_something(mock_session_local, mock_session):
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_session_local.return_value.__aexit__.return_value = None
    
    result = await some_function(mock_session)
```

**For external APIs:**
```python
# ❌ BAD: Real API call
async def test_embedding():
    service = EmbeddingService()
    embedding = await service.generate_embedding("text")  # Real API call!

# ✅ GOOD: Mocked service
@patch("app.shared.services.embeddings.service.EmbeddingService.generate_embedding")
async def test_embedding(mock_generate):
    mock_generate.return_value = [0.1] * 1536
    service = EmbeddingService()
    embedding = await service.generate_embedding("text")  # Mocked!
```

### Phase 3: Move Integration Tests

**Files to move to `tests/integration/`:**
- Tests that require real database connections
- Tests that test database operations end-to-end
- Tests that verify database schema/migrations

**Example:**
```python
# tests/integration/db/test_repository.py
@pytest.mark.integration
async def test_create_analysis_in_database():
    """Test that creates real database record."""
    async with AsyncSessionLocal() as session:
        # Real database operation
        analysis = Analysis(url="https://example.com")
        session.add(analysis)
        await session.commit()
```

### Phase 4: Add Test Markers

**Add markers to all tests:**
```python
@pytest.mark.unit
async def test_pure_function():
    """Unit test - no external dependencies."""
    pass

@pytest.mark.integration
async def test_database_operation():
    """Integration test - uses real database."""
    pass

@pytest.mark.external
async def test_api_integration():
    """External test - uses real API."""
    pass
```

### Phase 5: Update Test Configuration

**Update `pytest.ini` to enforce separation:**
```ini
[pytest]
# Default: run unit tests only
addopts = -m unit

# Markers
markers =
    unit: marks tests as unit tests (fast, mocked dependencies)
    integration: marks tests as integration tests (real database/APIs)
    external: marks tests that require external services
```

**Update CI to run both:**
```yaml
# Run unit tests (fast, no external deps)
- pytest tests/unit/ -m unit

# Run integration tests (slower, requires DB)
- pytest tests/integration/ -m integration
```

## Implementation Checklist

### Immediate Fixes (High Priority)

- [ ] Fix `test_runners.py` - Mock `AsyncSessionLocal` properly
- [ ] Fix `test_inject_context_node.py` - Mock `get_session_factory` properly
- [ ] Add embedding service mocks to all unit tests
- [ ] Fix tests with `CancelledError` (database connection issues)

### Medium Priority

- [ ] Add `@pytest.mark.unit` to all true unit tests
- [ ] Move database integration tests to `tests/integration/`
- [ ] Create shared fixtures for common mocks (session, embedding service)
- [ ] Update test documentation

### Low Priority

- [ ] Add test markers to all tests
- [ ] Update CI configuration
- [ ] Create test guidelines document

## Success Criteria

1. **All unit tests run without external dependencies:**
   - No database connections
   - No API calls
   - All dependencies mocked

2. **Clear separation:**
   - Unit tests in `tests/unit/` with `@pytest.mark.unit`
   - Integration tests in `tests/integration/` with `@pytest.mark.integration`

3. **Fast execution:**
   - Unit tests: < 30 seconds total
   - Integration tests: Can be slower but isolated

4. **No flaky tests:**
   - Tests don't depend on external services being available
   - Tests are deterministic

## Files to Fix

### High Priority (Making Real Calls)

1. `tests/unit/workflows/tasks/test_runners.py` - Database sessions
2. `tests/unit/workflows/nodes/test_inject_context_node.py` - Database sessions
3. `tests/unit/services/test_embeddings_errors.py` - Real embedding service calls
4. Any test file with `CancelledError` failures

### Medium Priority (Needs Better Mocks)

1. Tests using `get_session_factory` without proper mocking
2. Tests using `EmbeddingService` without mocking
3. Tests that should be integration tests

## Next Steps

1. Run audit script to identify all problematic tests
2. Fix high-priority tests first (database connection issues)
3. Add proper mocks for external services
4. Move integration tests to correct directory
5. Add test markers
6. Update CI configuration

## Key Issue Found: AsyncSessionLocal Mocking

**Problem:**
- `AsyncSessionLocal` is imported **inside** functions (lazy import pattern)
- Tests patch `app.db.session.AsyncSessionLocal` but the import happens at runtime
- Mock setup may not work correctly because `AsyncSessionLocal()` returns an async context manager

**Solution:**
```python
# ❌ Current (may not work):
@patch("app.db.session.AsyncSessionLocal")
async def test_something(mock_session_local, mock_session):
    mock_session_local.return_value = mock_session  # Wrong - AsyncSessionLocal() is a callable

# ✅ Correct:
@patch("app.db.session.AsyncSessionLocal")
async def test_something(mock_session_local, mock_session):
    # AsyncSessionLocal() should return an async context manager
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_session_local.return_value = mock_context_manager
```

**Better Solution - Patch where it's used:**
```python
# Patch in the runners module namespace (where it's imported)
@patch("app.domains.analysis.workflows.tasks.runners.AsyncSessionLocal")
async def test_something(mock_session_local, mock_session):
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_session_local.return_value = mock_context_manager
```


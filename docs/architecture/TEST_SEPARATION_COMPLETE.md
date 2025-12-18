# Test Separation - Complete

## Summary

Successfully separated unit tests from integration tests by:
1. ✅ Fixed AsyncSessionLocal mocking in all unit tests
2. ✅ Added `@pytest.mark.unit` to all test files in `tests/unit/`
3. ✅ Moved repository tests (integration tests) to `tests/integration/db/repositories/`

## Changes Made

### 1. Fixed AsyncSessionLocal Mocking
- Created `mock_async_session_local` fixture in `tests/conftest.py`
- Fixed all 19 tests in `test_runners.py` to use proper mocking
- All tests now pass without real database connections

### 2. Added Test Markers
- Added `@pytest.mark.unit` to 156 test files in `tests/unit/`
- Tests can now be filtered: `pytest -m unit` or `pytest -m integration`

### 3. Moved Integration Tests
- Moved repository tests from `tests/unit/db/repositories/` to `tests/integration/db/repositories/`
- Updated markers from `@pytest.mark.unit` to `@pytest.mark.integration`
- Files moved:
  - `test_analysis_repository.py`
  - `test_artifact_repository.py`
  - `test_chunk_repository.py`
  - `test_library_repository.py`

## Test Structure

```
tests/
├── unit/              # Unit tests (mocked, fast)
│   └── ...            # All marked with @pytest.mark.unit
└── integration/       # Integration tests (real DB/APIs)
    └── db/
        └── repositories/  # Repository tests (real database)
            └── ...        # All marked with @pytest.mark.integration
```

## Running Tests

```bash
# Run only unit tests (fast, no external dependencies)
pytest -m unit

# Run only integration tests (requires database)
pytest -m integration

# Run all tests
pytest
```

## Next Steps

1. Review other test files that might need to be moved to integration
2. Update CI to run unit and integration tests separately
3. Add more shared fixtures for common mocking patterns


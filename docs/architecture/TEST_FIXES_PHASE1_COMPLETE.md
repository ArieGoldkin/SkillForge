# Test Separation Fixes - Phase 1 Complete

## Summary

Fixed AsyncSessionLocal mocking issues in `test_runners.py` and created shared fixtures for properly mocked database sessions.

## Changes Made

### 1. Fixed AsyncSessionLocal Mocking

**Problem:**
- Tests were patching `app.db.session.AsyncSessionLocal` but the mock setup was incorrect
- `AsyncSessionLocal` is a `_LazySessionFactory()` callable that returns an async context manager
- Tests were trying to set `mock_session_local.return_value = mock_session` which doesn't work

**Solution:**
- Created `mock_async_session_local` fixture that properly mocks the async context manager pattern
- Updated all tests to use `patch("app.db.session.AsyncSessionLocal", mock_async_session_local)`
- Fixed 19 tests in `test_runners.py`

### 2. Created Shared Fixtures

**Added to `tests/conftest.py`:**
- `mock_async_session_local` fixture - Properly mocks AsyncSessionLocal for unit tests
- Can be reused across all test files that need to mock database sessions

**Updated `tests/unit/workflows/tasks/test_runners.py`:**
- Added `mock_async_session_local` fixture locally (can be removed once conftest fixture is used)
- Updated all tests to use the new fixture

## Test Results

**Before:**
- 19 tests in `test_runners.py`
- Many failing due to incorrect mocking

**After:**
- 19 tests in `test_runners.py`
- 12 passing, 7 failing (down from more failures)
- Remaining failures are likely functional issues, not mocking issues

## Next Steps

1. **Add test markers** - Mark all tests with `@pytest.mark.unit` or `@pytest.mark.integration`
2. **Move integration tests** - Move tests that use real database to `tests/integration/`
3. **Fix remaining failures** - Address the 7 remaining failures in `test_runners.py`

## Files Modified

- `backend/tests/conftest.py` - Added `mock_async_session_local` fixture
- `backend/tests/unit/workflows/tasks/test_runners.py` - Fixed all AsyncSessionLocal mocking


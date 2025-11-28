# Test Execution Guide

**Version:** 1.0  
**Last Updated:** November 28, 2025

---

## Quick Start

### Run Fast Tests (Default)
```bash
# Runs unit tests excluding slow/external tests
# Uses parallel execution automatically
poetry run pytest
```

### Run All Tests
```bash
# Run all tests including slow/external
poetry run pytest -m ""
```

### Run Specific Test Groups
```bash
# Unit tests only
poetry run pytest tests/unit/

# Integration tests only
poetry run pytest tests/integration/

# Fast tests only (no slow/external)
poetry run pytest -m "not slow and not external"

# Slow tests only
poetry run pytest -m "slow"
```

---

## Parallel Execution

**pytest-xdist is configured for parallel test execution.**

### Automatic (Recommended)
```bash
# Auto-detect CPU cores (default)
poetry run pytest -n auto
```

### Manual Worker Count
```bash
# Use 4 workers
poetry run pytest -n 4

# Use 8 workers
poetry run pytest -n 8
```

### Disable Parallel (Debugging)
```bash
# Run sequentially (single process)
poetry run pytest -n 1
```

**Performance:**
- **Before:** ~60 seconds for unit tests (sequential)
- **After:** ~20 seconds for unit tests (parallel, 3x speedup)
- **CPU Utilization:** 80-100% (all cores) vs 25% (single core)

---

## Test Markers

Tests are organized with markers for easy selection:

### Markers Available

- `@pytest.mark.slow` - Tests that take >10 seconds
- `@pytest.mark.external` - Tests requiring external services (OpenAI, Jina)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.timeout(N)` - Custom timeout in seconds

### Usage Examples

```bash
# Run fast tests only (default)
poetry run pytest -m "not slow and not external"

# Run slow tests
poetry run pytest -m "slow"

# Run external service tests
poetry run pytest -m "external"

# Run integration tests
poetry run pytest -m "integration"
```

---

## Database-Dependent Tests

Tests that require PostgreSQL will **skip gracefully** if database is unavailable.

### Fast Skipping

- Connection timeout: **0.5-1.0 seconds** (prevents hanging)
- Tests skip immediately if database is unreachable
- No hanging or long waits

### Running Database Tests

**Prerequisites:**
1. PostgreSQL running on localhost:5432
2. `DATABASE_URL` configured in `.env` or environment

**Run database tests:**
```bash
# All tests (will skip if DB unavailable)
poetry run pytest

# Force database tests (will fail if DB unavailable)
poetry run pytest -m "integration"
```

---

## Test Execution Profiles

### Profile 1: Fast Feedback (Default)
```bash
poetry run pytest
# Runs: Unit tests, excludes slow/external
# Time: ~20-30 seconds
# Use: During development for quick feedback
```

### Profile 2: Full Unit Tests
```bash
poetry run pytest tests/unit/ -n auto
# Runs: All unit tests
# Time: ~20-30 seconds
# Use: Before committing code
```

### Profile 3: Integration Tests
```bash
poetry run pytest tests/integration/ -n auto
# Runs: Integration tests (requires database)
# Time: ~1-2 minutes
# Use: Before pushing to remote
```

### Profile 4: Full Suite
```bash
poetry run pytest -m "" -n auto
# Runs: All tests including slow/external
# Time: ~5-10 minutes (depends on external services)
# Use: CI/CD or before major releases
```

---

## Troubleshooting

### Tests Hang or Timeout

**Issue:** Tests hang waiting for database or external services.

**Solution:**
- Check if PostgreSQL is running: `pg_isready`
- Check if external services are accessible
- Tests should skip automatically if services unavailable
- Use `-n 1` to disable parallel execution for debugging

### Parallel Execution Issues

**Issue:** Tests fail when run in parallel but pass sequentially.

**Solution:**
- Check for shared state between tests
- Ensure fixtures properly clean up
- Use `-n 1` to isolate the issue
- Review test isolation (database transactions, event broadcaster cleanup)

### Database Connection Failures

**Issue:** Many tests fail with "Connect call failed" errors.

**Solution:**
- Start PostgreSQL: `brew services start postgresql` (macOS)
- Or use Docker: `docker-compose up -d postgres`
- Tests will skip gracefully if database unavailable
- Check `DATABASE_URL` in `.env` file

---

## Performance Tips

1. **Use parallel execution** - Always use `-n auto` for faster runs
2. **Run fast tests during development** - Default excludes slow/external
3. **Run full suite before commits** - Catch integration issues early
4. **Use test markers** - Selectively run relevant test groups
5. **Monitor CPU usage** - Should see 80-100% utilization with parallel execution

---

## Configuration

Test configuration is in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Default: parallel execution, fast tests only
addopts = "-n auto --dist worksteal -m 'not slow and not external'"
```

**To change defaults:**
- Edit `addopts` in `pyproject.toml`
- Or override with command-line flags

---

## CI/CD Integration

For CI/CD pipelines, use:

```bash
# Fast tests (quick feedback)
poetry run pytest -n auto -m "not slow and not external"

# Full suite (comprehensive)
poetry run pytest -n auto -m ""
```

**Recommended CI Strategy:**
1. Run fast tests on every commit (quick feedback)
2. Run full suite on pull requests (comprehensive)
3. Use parallel execution for all runs

---

## Success Metrics

**Target Performance:**
- Fast tests: <30 seconds
- Unit tests: <30 seconds
- Integration tests: <2 minutes
- Full suite: <5 minutes (with parallel execution)

**Current Performance:**
- Unit tests: ~21 seconds (parallel, 16 workers)
- 3x speedup vs sequential execution
- CPU utilization: 80-100% (all cores)

---

For questions or issues, see test files for examples or check `backend/tests/conftest.py` for fixture documentation.

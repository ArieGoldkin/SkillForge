---
description: Run test suite with visible progress
---

Run tests for: $ARGUMENTS

## Backend Tests (default if no args)
```bash
cd backend
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tee /tmp/test_results.log
```

## Specific test file or pattern
```bash
cd backend
poetry run pytest tests/unit/$ARGUMENTS -v --tb=short 2>&1 | tee /tmp/test_results.log
```

## Frontend Tests
```bash
cd frontend
npm run test 2>&1 | tee /tmp/frontend_test_results.log
```

## Quick summary (fast)
```bash
cd backend
poetry run pytest tests/unit/ --tb=no -q 2>&1 | tail -20
```

## With coverage
```bash
cd backend
poetry run pytest tests/unit/ --cov=app --cov-report=term-missing -v
```

Options:
- `--maxfail=3`: Stop after 3 failures
- `-k "test_name"`: Run specific test by name
- `-x`: Stop on first failure
- `--lf`: Run only last failed tests

Always show test output so user can watch progress!

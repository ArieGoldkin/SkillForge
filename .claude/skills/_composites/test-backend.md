---
name: test-backend
description: Complete Python/FastAPI backend testing composite
version: 1.0.0
type: composite
includes:
  - testing/unit-testing-fundamentals
  - testing/unit-testing-python
  - testing/api-mocking-vcr
  - testing/integration-testing
  - testing/ai-llm-testing
trigger: "backend/**/*.py"
tags: [testing, backend, python, composite]
---

# Backend Testing Composite

Combines atomic skills for complete Python/FastAPI testing.

## Included Skills

| Skill | Purpose |
|-------|---------|
| unit-testing-fundamentals | AAA pattern, isolation, test design |
| unit-testing-python | pytest, fixtures, parametrize, async |
| api-mocking-vcr | HTTP recording/playback for external APIs |
| integration-testing | Database, API endpoint testing |
| ai-llm-testing | LLM mock patterns, timeout handling |

## Quick Start

```bash
# Install dependencies
pip install pytest pytest-cov pytest-asyncio pytest-vcr httpx

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v --vcr-record=none
pytest --cov=app --cov-fail-under=80
```

## Project Structure

```
tests/
├── conftest.py          # Shared fixtures
├── cassettes/           # VCR recordings
├── unit/
│   ├── test_services.py
│   └── test_models.py
└── integration/
    ├── test_api.py
    └── test_repositories.py
```

## Recommended Fixtures

```python
# conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db_session():
    # Fresh database session per test
    async with TestSession() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="module")
def vcr_config():
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "none" if os.getenv("CI") else "once",
        "filter_headers": ["authorization"],
    }
```

## Coverage Targets

- **Business logic**: 90%+
- **API endpoints**: 80%+
- **Critical paths** (auth, payments): 100%
- **LLM integrations**: Mock in unit, VCR in integration

---
name: api-mocking-vcr
description: VCR.py for Python HTTP recording and playback
version: 1.0.0
tags: [testing, python, vcr, http, mocking]
size: atomic
domain: testing
---

# VCR.py - HTTP Recording (2025 Python Standard)

Record real HTTP responses once, replay deterministically forever.

## Setup

```bash
pip install pytest-vcr vcrpy
```

## Configuration

```python
# conftest.py
import pytest

@pytest.fixture(scope="module")
def vcr_config():
    return {
        "cassette_library_dir": "tests/cassettes",
        "record_mode": "once",
        "match_on": ["uri", "method"],
        "filter_headers": ["authorization", "x-api-key"],
        "filter_query_parameters": ["api_key", "token"],
    }
```

## Basic Usage

```python
import pytest

# Decorator style (recommended)
@pytest.mark.vcr()
def test_fetch_user():
    response = requests.get("https://api.example.com/users/1")
    assert response.status_code == 200
    assert response.json()["name"] == "John Doe"

# Context manager style
def test_fetch_data():
    with vcr.use_cassette("tests/cassettes/data.yaml"):
        response = requests.get("https://api.example.com/data")
        assert response.status_code == 200
```

## Async Support

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_async_api_call():
    async with AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        assert response.status_code == 200
```

## Recording Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `once` | Record if missing, then replay | Default |
| `new_episodes` | Record new, replay existing | Adding tests |
| `none` | Never record, fail on new | CI |
| `all` | Always record | Refresh cassettes |

```python
# CI-safe configuration
@pytest.fixture(scope="module")
def vcr_config():
    import os
    return {
        "record_mode": "none" if os.environ.get("CI") else "once",
        "cassette_library_dir": "tests/cassettes",
    }
```

## Filtering Sensitive Data

```python
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": [
            "authorization",
            "x-api-key",
            "cookie",
        ],
        "filter_query_parameters": [
            "api_key",
            "access_token",
        ],
        "before_record_request": filter_request,
    }

def filter_request(request):
    if request.body:
        import json
        try:
            body = json.loads(request.body)
            if "password" in body:
                body["password"] = "REDACTED"
            request.body = json.dumps(body)
        except json.JSONDecodeError:
            pass
    return request
```

## Cassette File Example

```yaml
# tests/cassettes/test_fetch_user.yaml
interactions:
- request:
    body: null
    headers:
      Content-Type: application/json
    method: GET
    uri: https://api.example.com/users/1
  response:
    body:
      string: '{"id": 1, "name": "John Doe"}'
    headers:
      Content-Type: application/json
    status:
      code: 200
      message: OK
version: 1
```

## Refresh Cassettes

```bash
# Delete and re-record
rm tests/cassettes/test_fetch_user.yaml
pytest tests/test_api.py::test_fetch_user -v

# Or force re-record
VCR_RECORD_MODE=all pytest tests/ -v
```

## Anti-Patterns

```python
# BAD - Commit cassettes with real API keys
# headers:
#   authorization: Bearer sk-real-key

# BAD - Use "all" mode in CI
# record_mode: "all"

# BAD - Skip VCR for HTTP tests
def test_api():
    requests.get("https://real-api.com")  # Makes real call!

# GOOD - Always wrap HTTP tests
@pytest.mark.vcr()
def test_api():
    requests.get("https://api.example.com")
```

---
name: unit-testing-python
description: pytest patterns, fixtures, parametrize, async testing
version: 1.0.0
tags: [testing, python, pytest]
size: atomic
domain: testing
---

# Python Unit Testing with pytest

## Setup

```bash
pip install pytest pytest-cov pytest-asyncio
```

## Basic Test Structure

```python
# tests/test_calculator.py
import pytest
from app.calculator import Calculator

class TestCalculator:
    def test_add_positive_numbers(self):
        calc = Calculator()
        assert calc.add(2, 3) == 5

    def test_divide_by_zero_raises_error(self):
        calc = Calculator()
        with pytest.raises(ZeroDivisionError):
            calc.divide(10, 0)
```

## Fixtures

```python
# conftest.py
import pytest
from app.database import Database

@pytest.fixture
def db():
    """Fresh database for each test."""
    database = Database(":memory:")
    database.create_tables()
    yield database
    database.close()

@pytest.fixture
def sample_user(db):
    """Create a sample user."""
    return db.create_user(email="test@example.com", name="Test User")

# tests/test_user_service.py
def test_get_user_by_email(db, sample_user):
    user = db.get_user_by_email("test@example.com")
    assert user.id == sample_user.id
```

## Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
    ("123abc", "123ABC"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected

@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
    (100, 200, 300),
])
def test_addition(a, b, expected):
    assert a + b == expected
```

## Async Testing

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_fetch():
    result = await fetch_data("https://api.example.com/data")
    assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_timeout_handling():
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.1):
            await slow_operation()
```

## Mocking

```python
from unittest.mock import Mock, AsyncMock, patch

def test_with_mock():
    mock_service = Mock()
    mock_service.get_data.return_value = {"id": 1}

    result = process_data(mock_service)

    mock_service.get_data.assert_called_once()
    assert result["processed"] is True

@pytest.mark.asyncio
async def test_async_mock():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"data": "test"}

    result = await handler(mock_client)
    assert result == {"data": "test"}

def test_with_patch():
    with patch("app.services.external_api") as mock_api:
        mock_api.call.return_value = "mocked"
        result = my_function()
        assert result == "mocked"
```

## Coverage

```bash
# Run with coverage
pytest --cov=app --cov-report=html

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=80
```

## Running Tests

```bash
pytest                           # All tests
pytest tests/unit/               # Specific directory
pytest -k "test_user"            # Match pattern
pytest -v --tb=short             # Verbose, short traceback
pytest -x                        # Stop on first failure
pytest --lf                      # Rerun last failed
```

# Development Guidelines

This document provides comprehensive development guidelines for the SkillForge backend.

## Code Style Guide

### Import Organization

Imports must follow this order (enforced by ruff):

1. **Standard library imports**
2. **Third-party imports**
3. **Local application imports**

```python
# Standard library
import os
from pathlib import Path

# Third-party
import httpx
from fastapi import APIRouter

# Local
from app.core.config import settings
from app.core.logging import get_logger
```

### Naming Conventions

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE` (defined in `app/core/constants.py`)
- **Type Aliases**: `PascalCase` (defined in `app/core/types.py`)
- **Private Methods**: `_leading_underscore`

### Docstrings

All public functions and classes must have Google-style docstrings:

```python
def extract_content(url: str, analysis_id: AnalysisID) -> dict:
    """Extract content from URL using JinaReader.

    Args:
        url: The URL to extract content from
        analysis_id: Unique identifier for this analysis

    Returns:
        Dictionary with 'raw_content' and 'extraction_metadata'

    Raises:
        JinaReaderError: If extraction fails

    Example:
        >>> result = await extract_content("https://example.com", "123")
        >>> "raw_content" in result
        True
    """
    pass
```

## Error Handling Patterns

### Exception Hierarchy

Always use custom exceptions from `app/core/exceptions.py`:

```python
# ✅ GOOD
from app.core.exceptions import EmbeddingError

if embedding is None:
    raise EmbeddingError("Embedding generation failed")

# ❌ BAD
if embedding is None:
    raise Exception("Embedding generation failed")
```

### Exception Handling

- **Catch specific exceptions**: Use specific exception types, not bare `except:`
- **Re-raise with context**: Use `raise ... from e` to preserve exception chain
- **Log before raising**: Include context in log messages

```python
# ✅ GOOD
try:
    result = await service.call()
except ServiceException as e:
    logger.error("service_call_failed", error=str(e), exc_info=True)
    raise EmbeddingError("Service call failed") from e

# ❌ BAD
try:
    result = await service.call()
except:
    raise Exception("Failed")
```

## Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions with mocked dependencies
- **Integration tests**: Test with real services (requires API keys)
- **Test naming**: `test_<function_name>_<scenario>`

### Test Organization

```
tests/
├── unit/              # Unit tests (mocked)
│   ├── test_constants.py
│   ├── test_exceptions.py
│   └── workflows/
│       └── test_analysis.py
└── integration/       # Integration tests (real services)
    └── workflows/
        └── test_analysis.py
```

### Test Configuration

The project uses `pytest-timeout` to prevent tests from hanging:

- **Default timeout**: 5 minutes (configured in `pytest.ini`)
- **Test-level timeouts**: Use `@pytest.mark.timeout(seconds)` to override
- **Timeout method**: Thread-based (works with async tests)
- **Asyncio mode**: Auto (configured in `pytest.ini`)

### Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.integration`: Integration tests requiring real services
- `@pytest.mark.external`: Tests requiring external services (Ollama, Jina, etc.)
- `@pytest.mark.timeout(N)`: Override default timeout for specific test

### Writing Tests

**Unit Test Example:**
```python
import pytest
from unittest.mock import AsyncMock, patch

from app.core.exceptions import EmbeddingError
from app.services.embeddings import EmbeddingService

@pytest.mark.asyncio
async def test_generate_embedding_success():
    """Test successful embedding generation."""
    service = EmbeddingService()
    with patch.object(service.client, "post") as mock_post:
        mock_post.return_value.json.return_value = {"embedding": [0.1] * 768}
        result = await service.generate_embedding("test text")
        assert len(result) == 768
    await service.close()  # Clean up resources
```

**Integration Test Example:**
```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(120)  # 2 minute timeout
async def test_workflow_end_to_end(requires_database, reset_engine_connections):
    """Test workflow with real services."""
    try:
        result = await analysis_workflow.ainvoke({
            "url": "https://example.com",
            "analysis_id": "test-123",
        })
        assert "raw_content" in result
    finally:
        await engine.dispose()  # Clean up database connections
```

**Async Fixture Example:**
```python
import pytest_asyncio

@pytest_asyncio.fixture  # Use pytest_asyncio.fixture, not @pytest.fixture
async def async_resource():
    """Create async resource with proper cleanup."""
    resource = await create_resource()
    try:
        yield resource
    finally:
        await cleanup_resource(resource)
```

### Preventing Hanging Tests

To prevent tests from hanging indefinitely:

1. **Use `@pytest.mark.timeout(seconds)`** for slow/integration tests
2. **Wrap async operations in `asyncio.wait_for()`** with timeouts
3. **Cancel background tasks** explicitly in `finally` blocks
4. **Use `reset_engine_connections` fixture** for database tests
5. **Clean up event broadcaster subscriptions** (automatic via fixture)
6. **Await cancelled tasks** to ensure proper cleanup

```python
@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_with_background_task():
    """Test with background task that must be cleaned up."""
    task = asyncio.create_task(long_running_operation())
    try:
        result = await asyncio.wait_for(task, timeout=30.0)
        assert result is not None
    finally:
        # Always cancel and await background tasks
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
```

### Test Coverage

- **Minimum**: 80% coverage (hard block)
- **Target**: 90%+ coverage for critical paths
- **Run**: `poetry run pytest --cov=app --cov-report=html`

## Constants Usage

### No Magic Numbers

Always use constants from `app/core/constants.py`:

```python
# ✅ GOOD
from app.core.constants import MAX_TEXT_LENGTH, HTTP_ERROR_THRESHOLD

if len(text) > MAX_TEXT_LENGTH:
    text = text[:MAX_TEXT_LENGTH]

# ❌ BAD
if len(text) > 8000:
    text = text[:8000]
```

### Adding New Constants

When adding new constants:

1. Add to `app/core/constants.py` with descriptive name
2. Add docstring comment explaining the constant
3. Update all usages to use the constant
4. Add unit test in `tests/unit/test_constants.py`

## Type Safety

### Type Hints Required

All functions must have type hints:

```python
# ✅ GOOD
async def generate_embedding(text: str) -> EmbeddingVector:
    pass

# ❌ BAD
async def generate_embedding(text):
    pass
```

### Use Type Aliases

Use type aliases from `app/core/types.py` for complex types:

```python
# ✅ GOOD
from app.core.types import EmbeddingVector, AnalysisID

async def process(analysis_id: AnalysisID) -> EmbeddingVector:
    pass

# ❌ BAD
async def process(analysis_id: str) -> list[float]:
    pass
```

### Avoid `Any`

Never use `Any` unless absolutely necessary (and document why):

```python
# ✅ GOOD
from typing import Unknown

data: dict[str, Unknown] = response.json()

# ❌ BAD
from typing import Any

data: dict[str, Any] = response.json()
```

## File Size Limits

- **Source files**: Maximum 200 lines
- **Test files**: Maximum 300 lines
- **Refactor** when approaching limits

If a file exceeds limits:
1. Extract functions to separate modules
2. Split classes into smaller components
3. Move utilities to shared modules

## Code Quality Checks

### Pre-Commit

Run these checks before committing:

```bash
# Format code
poetry run ruff format app tests

# Lint code
poetry run ruff check app tests

# Type check
poetry run mypy app

# Run tests
poetry run pytest
```

### Pre-Push

Run comprehensive checks:

```bash
# Full test suite with coverage
poetry run pytest --cov=app --cov-report=html --cov-fail-under=80

# All quality checks
poetry run ruff check .
poetry run mypy app
```

## Best Practices

### Async/Await

- Use `async def` for all I/O operations
- Use `async with` for context managers
- Use `AsyncSession` for database operations

### Logging

- Use structured logging with `get_logger(__name__)`
- Include context in log messages (analysis_id, request_id, etc.)
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)

### Resource Management

- Always close resources in `finally` blocks
- Use context managers for file/network operations
- Dispose database connections properly

### Security

- Never log sensitive data (API keys, passwords, tokens)
- Validate all user inputs
- Use environment variables for secrets
- Sanitize error messages before exposing to clients

## Common Patterns

### Service Initialization

```python
class MyService:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        logger.info("service_initialized", service="MyService")

    async def close(self) -> None:
        await self.client.aclose()
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.constants import MAX_RETRY_ATTEMPTS, RETRY_MIN_WAIT_JINA, RETRY_MAX_WAIT_JINA

@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(min=RETRY_MIN_WAIT_JINA, max=RETRY_MAX_WAIT_JINA),
    reraise=True,
)
async def call_external_api():
    pass
```

### Dependency Injection

```python
from fastapi import Depends
from app.api.dependencies import get_database_session

@router.post("/items")
async def create_item(db: AsyncSession = Depends(get_database_session)):
    # Use db session
    pass
```

## Troubleshooting

### Import Errors

If imports fail:
1. Ensure you're in Poetry shell: `poetry shell`
2. Verify dependencies: `poetry install`
3. Check Python version: `python --version` (must be 3.13)

### Type Errors

If mypy reports errors:
1. Check type hints are correct
2. Use type aliases from `app/core/types.py`
3. Add `# type: ignore` only when necessary (with comment explaining why)

### Linting Errors

If ruff reports errors:
1. Run `ruff format .` to auto-format
2. Run `ruff check . --fix` to auto-fix
3. Review remaining errors manually

## Resources

- **Architecture**: [docs/ARCHITECTURE.md](./ARCHITECTURE.md)
- **Backend Tasks**: [docs/YONATAN_BACKEND_TASKS.md](./YONATAN_BACKEND_TASKS.md)
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/

---

**Last Updated:** November 24, 2025  
**Maintained By:** Backend Team

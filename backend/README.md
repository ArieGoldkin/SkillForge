# SkillForge Backend API

Backend API for the SkillForge Research-to-Implementation Pipeline built with FastAPI, Python 3.13, and Poetry.

## Quick Start

### Prerequisites

- **Python 3.13** (required)
- **Poetry** (for dependency management)
- **Docker Desktop** (for local PostgreSQL and Ollama)

### Installation

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   cd backend
   poetry install
   ```

3. **Activate Poetry shell**:
   ```bash
   poetry shell
   # OR use: poetry run <command>
   ```

4. **Copy environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the server**:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

6. **Visit**:
   - API: http://localhost:8500
   - OpenAPI Docs: http://localhost:8500/docs
   - Health Check: http://localhost:8500/api/v1/health

## Project Structure

```
backend/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization
│   │
│   ├── api/                      # API layer (HTTP endpoints)
│   │   ├── __init__.py
│   │   ├── dependencies.py       # Shared FastAPI dependencies
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── health.py         # Health check endpoint
│   │       ├── analyze.py        # Analysis endpoints (future)
│   │       ├── tutor.py          # Tutoring endpoints (future)
│   │       └── library.py        # Library endpoints (future)
│   │
│   ├── core/                     # Core configuration & utilities
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings
│   │   ├── logging.py            # structlog configuration
│   │   └── exceptions.py         # Custom exception handlers (future)
│   │
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   ├── base.py               # SQLAlchemy Base class
│   │   └── session.py            # AsyncSession factory (future)
│   │
│   ├── models/                   # SQLAlchemy ORM models (future)
│   │   └── __init__.py
│   │
│   ├── schemas/                  # Pydantic request/response schemas (future)
│   │   └── __init__.py
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   └── extraction/           # Content extraction services
│   │       ├── __init__.py
│   │       ├── jina_reader.py    # Jina AI Reader service
│   │       └── content_type.py   # Content type detection
│   │
│   └── workflows/                # LangGraph workflows
│       ├── __init__.py
│       └── analysis.py           # Analysis workflow (extract → embed)
│
├── alembic/                      # Database migrations
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── unit/                     # Unit tests (mocked services)
│   │   ├── __init__.py
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── test_analysis.py  # Workflow unit tests
│   │   └── services/
│   │       └── __init__.py
│   ├── integration/              # Integration tests (real services)
│   │   ├── __init__.py
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── test_analysis.py  # Workflow integration tests
│   │   └── services/
│   │       └── __init__.py
│   ├── test_main.py              # Endpoint tests
│   ├── test_config.py            # Configuration tests
│   ├── test_jina_reader.py       # Jina Reader service unit tests
│   ├── test_jina_integration.py  # Jina Reader integration tests
│   ├── test_jina_extended.py     # Jina Reader extended tests
│   └── test_anthropic_article.py # Specific article integration test
│
├── .env.example                  # Environment variable template
├── pyproject.toml                # Poetry configuration
├── poetry.lock                   # Locked dependency versions
└── README.md                     # This file
```

## Development

### Running the Server

```bash
# Development mode with auto-reload
poetry run uvicorn app.main:app --reload --port 8500

# Production mode
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8500
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_main.py

# Run with verbose output
poetry run pytest -v
```

### Code Quality Checks

```bash
# Format code with Ruff (replaces Black - 30x faster!)
poetry run ruff format app tests

# Lint with Ruff
poetry run ruff check app tests

# Type check with mypy
poetry run mypy app
```

### Pre-commit Checks (Recommended)

You can set up pre-commit hooks to run these checks automatically:

```bash
# Install pre-commit (optional)
poetry add --group dev pre-commit

# Create .pre-commit-config.yaml
# Add hooks for ruff (format + lint), mypy
```

## Configuration

### Environment Variables

All configuration is loaded from environment variables or `.env` file. See `.env.example` for all available options.

Key variables:
- `ENVIRONMENT`: Runtime environment (`development`, `staging`, `production`)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `CORS_ORIGINS`: Allowed CORS origins (JSON array)
- `DATABASE_URL`: PostgreSQL connection string (future)
- `OLLAMA_BASE_URL`: Ollama API base URL (future)
- `JINA_API_KEY`: Jina AI API key (future, optional for dev)

### CORS Configuration

CORS is configured for the frontend dev server by default (`http://localhost:5173`). Update `CORS_ORIGINS` in `.env` for production.

## Workflows

The application uses LangGraph v1.0 Functional API for workflow orchestration.

### Analysis Workflow

The `analysis_workflow` performs content extraction and embedding generation:

```python
from app.workflows import analysis_workflow

# Run workflow
result = await analysis_workflow.ainvoke({
    "url": "https://example.com/article",
    "analysis_id": "unique-analysis-id",
})

# Result contains:
# - analysis_id: str
# - url: str
# - content_type: str
# - raw_content: str
# - extraction_metadata: dict
# - content_embedding: list[float]
```

### Workflow Structure

- **Extract Content**: Uses JinaReader to extract content from URL
- **Generate Embedding**: Uses EmbeddingService to create vector embeddings
- **Checkpointing**: Automatically saves state to PostgreSQL (or MemorySaver in dev)

### Test Structure

Tests are organized into unit and integration tests:

```
tests/
├── unit/
│   ├── workflows/
│   │   └── test_analysis.py      # Unit tests (mocked services)
│   └── services/
│       └── test_*.py             # Service unit tests
├── integration/
│   ├── workflows/
│   │   └── test_analysis.py     # Integration tests (real services)
│   └── services/
│       └── test_*.py             # Service integration tests
└── conftest.py                   # Shared fixtures
```

## Logging

The application uses `structlog` for structured logging:

- **Development**: Human-readable console output
- **Production**: JSON output for log aggregation

All logs include:
- Request ID for tracing
- Timestamp in ISO format
- Log level
- Structured context (request_id, analysis_id, etc.)

Example log entry:
```json
{
  "event": "request_completed",
  "method": "GET",
  "path": "/api/v1/health",
  "status_code": 200,
  "process_time_ms": 12.34,
  "request_id": "abc-123",
  "timestamp": "2025-11-20T10:30:00Z"
}
```

## API Documentation

FastAPI automatically generates OpenAPI documentation:

- **Swagger UI**: http://localhost:8500/docs
- **ReDoc**: http://localhost:8500/redoc
- **OpenAPI JSON**: http://localhost:8500/openapi.json

## Testing

### Test Structure

- `tests/conftest.py`: Pytest fixtures and configuration
- `tests/test_main.py`: Endpoint integration tests
- `tests/test_config.py`: Configuration unit tests
- `pytest.ini`: Pytest configuration (timeouts, markers, asyncio mode)

### Test Configuration

The project uses `pytest-timeout` to prevent tests from hanging indefinitely:

- **Default timeout**: 5 minutes (300 seconds) for all tests
- **Test-level timeouts**: Use `@pytest.mark.timeout(seconds)` to override
- **Timeout method**: Thread-based (works with async tests)
- **Asyncio mode**: Auto (allows mixing sync and async fixtures/tests)

### Test Markers

Tests are categorized with markers for selective execution:

- `@pytest.mark.slow`: Slow-running tests (deselect with `-m "not slow"`)
- `@pytest.mark.integration`: Integration tests requiring real services
- `@pytest.mark.external`: Tests requiring external services (Ollama, Jina, etc.)
- `@pytest.mark.timeout(N)`: Override default timeout for specific test

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_main.py

# Run only fast tests (exclude slow)
poetry run pytest -m "not slow"

# Run with verbose output
poetry run pytest -v

# Run with specific timeout
poetry run pytest --timeout=60
```

### Writing Tests

**Sync Test Example:**
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

**Async Test Example:**
```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

**Async Fixture Example:**
```python
import pytest_asyncio

@pytest_asyncio.fixture
async def async_resource():
    resource = await create_resource()
    try:
        yield resource
    finally:
        await cleanup_resource(resource)
```

### Test Best Practices

1. **Use `@pytest_asyncio.fixture` for async fixtures** (not `@pytest.fixture`)
2. **Add timeouts to slow/integration tests** with `@pytest.mark.timeout(seconds)`
3. **Clean up resources** in `finally` blocks or fixture teardown
4. **Cancel background tasks** explicitly to prevent hanging
5. **Use `reset_engine_connections` fixture** for database tests
6. **Mark slow/external tests** appropriately for selective execution

## Troubleshooting

### Poetry Installation Issues

If Poetry installation fails:
```bash
# Use pip as fallback
pip install poetry

# OR use pipx
pipx install poetry
```

### Python Version Mismatch

Ensure Python 3.13 is installed:
```bash
python3.13 --version

# Use pyenv to manage Python versions
pyenv install 3.13.0
pyenv local 3.13.0
```

### Port Conflicts

If port 8500 is already in use:
1. Change `PORT` in `.env` file
2. Or specify port directly: `poetry run uvicorn app.main:app --port 8501`

### CORS Errors

If frontend can't connect:
1. Verify `CORS_ORIGINS` in `.env` includes frontend URL
2. Check backend is running on correct host/port
3. Verify CORS middleware is configured in `app/main.py`

### Import Errors

If imports fail:
1. Ensure you're in Poetry shell: `poetry shell`
2. Or prefix commands with `poetry run`
3. Verify dependencies installed: `poetry install`

## Architecture

The backend follows a layered architecture with clear separation of concerns:

- **API Layer**: FastAPI routers and endpoints (`app/api/`)
- **Service Layer**: Business logic and external integrations (`app/services/`)
- **Workflow Layer**: LangGraph orchestration (`app/workflows/`)
- **Database Layer**: SQLAlchemy models and repositories (`app/db/`, `app/models/`)
- **Core Layer**: Configuration, logging, exceptions, constants (`app/core/`)

For detailed architecture documentation, see [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

### Key Patterns

- **Repository Pattern**: Abstract database access (see `docs/ARCHITECTURE.md`)
- **Service Layer**: Encapsulate business logic
- **Dependency Injection**: FastAPI Depends() for testability
- **Structured Logging**: structlog with request ID tracking
- **Error Handling**: Custom exception hierarchy (see Error Handling section)

## Constants

Application-wide constants are centralized in `app/core/constants.py`:

- **HTTP Status Codes**: `HTTP_OK`, `HTTP_NOT_FOUND`, `HTTP_ERROR_THRESHOLD`
- **Timeouts**: `DEFAULT_TIMEOUT`, `EMBEDDING_TIMEOUT`, `DB_TIMEOUT`
- **Text Limits**: `MAX_TEXT_LENGTH`, `MAX_ERROR_MESSAGE_LENGTH`
- **Retry Configuration**: `MAX_RETRY_ATTEMPTS`, retry wait times
- **Database Pool**: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`
- **Content Types**: `CONTENT_TYPE_ARTICLE`, `CONTENT_TYPE_VIDEO`, `CONTENT_TYPE_REPO`

**Usage:**
```python
from app.core.constants import MAX_TEXT_LENGTH, HTTP_ERROR_THRESHOLD

if len(text) > MAX_TEXT_LENGTH:
    text = text[:MAX_TEXT_LENGTH]

if response.status_code >= HTTP_ERROR_THRESHOLD:
    raise Error("HTTP error")
```

## Error Handling

The application uses a structured exception hierarchy for consistent error handling:

```
SkillForgeException (base)
├── ServiceException
│   ├── EmbeddingError
│   └── JinaReaderError
├── WorkflowError
└── DatabaseError
```

**Raising Exceptions:**
```python
from app.core.exceptions import EmbeddingError

if embedding is None:
    raise EmbeddingError("Embedding generation failed")
```

**Handling Exceptions:**
- Custom exceptions are caught by `SkillForgeException` handler in `main.py`
- All exceptions include request ID for tracing
- Error responses follow consistent format:
  ```json
  {
    "error": {
      "code": "EmbeddingError",
      "message": "Error message",
      "request_id": "abc-123"
    }
  }
  ```

See `app/core/exceptions.py` for the full exception hierarchy.

## Type Safety

Type aliases are defined in `app/core/types.py` for better code readability:

- `EmbeddingVector`: `list[float]` - Embedding vectors
- `AnalysisID`: `str` - Analysis identifiers
- `ChannelName`: `str` - SSE channel names
- `EventData`: `dict[str, object]` - SSE event data
- `ExtractionResult`: `dict[str, str | int | dict[str, str]]` - Extraction results

**Usage:**
```python
from app.core.types import EmbeddingVector, AnalysisID

async def generate_embedding(text: str) -> EmbeddingVector:
    # Returns list[float]
    pass
```

## Contributing

### Code Quality Standards

- **File Size Limits**: 200 lines (source), 300 lines (tests)
- **Type Coverage**: 100% type hints, use type aliases from `app/core/types.py`
- **Constants**: Use constants from `app/core/constants.py`, no magic numbers
- **Exceptions**: Use custom exceptions from `app/core/exceptions.py`
- **Documentation**: Comprehensive docstrings for all public functions/classes

### Pre-Commit Checklist

- [ ] All tests pass: `poetry run pytest`
- [ ] No linting errors: `poetry run ruff check .`
- [ ] Code formatted: `poetry run ruff format .`
- [ ] Type checking passes: `poetry run mypy app`
- [ ] Coverage ≥80%: `poetry run pytest --cov=app --cov-fail-under=80`
- [ ] Docstrings added for new functions
- [ ] Constants used instead of magic numbers
- [ ] Custom exceptions used instead of generic Exception

### Development Workflow

1. **Create feature branch**: `git checkout -b feature/issue-XX-description`
2. **Make changes**: Follow code quality standards
3. **Run tests**: `poetry run pytest`
4. **Check quality**: `poetry run ruff check . && poetry run mypy app`
5. **Commit**: Use conventional commits format
6. **Push**: `git push origin feature/issue-XX-description`

### Code Style

- **Imports**: Standard library → Third-party → Local (ruff auto-formats)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Google-style with Args, Returns, Raises sections
- **Type Hints**: Required for all function parameters and return values

See `docs/DEVELOPMENT.md` for detailed development guidelines.

## Next Steps

After completing this setup:

1. **Task 1.1.2**: Environment Configuration (already included)
2. **Task 1.1.3**: Structured Logging (already included)
3. **Task 1.2.1**: Install & Configure Alembic
4. **Task 1.2.2**: Create SQLAlchemy Models
5. **Task 1.4.1**: Research & Setup Jina AI

See `docs/YONATAN_BACKEND_TASKS.md` for full task breakdown.

## License

MIT License - see LICENSE file for details.

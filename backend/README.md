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
│   └── workflows/                # LangGraph workflows (future)
│       └── __init__.py
│
├── alembic/                      # Database migrations (future)
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
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

### Writing Tests

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

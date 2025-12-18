# API Layer

RESTful API endpoints for the SkillForge application.

## Structure

```
api/
├── v1/              # API version 1 (current)
│   ├── analyze.py   # Analysis workflow endpoints
│   ├── artifacts.py # Artifact retrieval/download
│   ├── health.py    # Health check endpoint
│   ├── library.py   # Library listing/search
│   ├── search.py    # Semantic/hybrid search
│   └── tutor/       # Socratic tutoring endpoints
└── dependencies.py  # Shared FastAPI dependencies
```

## API Versioning

- **Current version**: `v1`
- **Base path**: `/api/v1`
- **OpenAPI docs**: http://localhost:8500/docs
- **ReDoc**: http://localhost:8500/redoc

## Core Endpoints

### Analysis

- `POST /api/v1/analyze` - Create new analysis
- `GET /api/v1/analyze/{id}/stream` - SSE progress stream
- `GET /api/v1/analyze/{id}` - Get analysis status

### Artifacts

- `GET /api/v1/analyze/{analysis_id}/artifact` - Get artifact metadata by analysis ID
- `GET /api/v1/artifacts/{artifact_id}` - Get artifact metadata by artifact ID
- `GET /api/v1/artifacts/{artifact_id}/download` - Download markdown file

### Library

- `GET /api/v1/library` - List/search analyses
- `DELETE /api/v1/analyses/{id}` - Delete analysis

### Search

- `GET /api/v1/search/similar` - Semantic similarity search
- `POST /api/v1/search` - Advanced search (semantic/keyword/hybrid)

### Tutor

- `POST /api/v1/tutor/sessions` - Create tutoring session
- `GET /api/v1/tutor/sessions/{id}` - Get session details
- `POST /api/v1/tutor/sessions/{id}/messages` - Send message
- `GET /api/v1/tutor/sessions/{id}/stream` - SSE response stream

## Response Formats

All endpoints return JSON with consistent structure:

### Success Response

```json
{
  "analysis_id": "uuid",
  "status": "complete",
  "data": {...}
}
```

### Error Response

```json
{
  "detail": "Error message",
  "error_code": "ERROR_TYPE_CODE"
}
```

## Server-Sent Events (SSE)

Real-time progress updates via SSE streams:

```typescript
const eventSource = new EventSource('/api/v1/analyze/{id}/stream')
eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data)
  console.log(data.stage, data.status)
})
```

### Event Types

- `progress` - Workflow stage updates
- `agent` - Agent execution events
- `complete` - Analysis completion
- `error` - Error events

## Authentication

**Status**: Not yet implemented (Issue #TBD)

Future: API key authentication via `X-API-Key` header.

## Rate Limiting

**Status**: Rate limiter exists but not applied (Issue #TBD)

Future: Token bucket rate limiting on expensive endpoints.

## Development

### Running Locally

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8500
```

### API Testing

```bash
# Health check
curl http://localhost:8500/api/v1/health

# Create analysis
curl -X POST http://localhost:8500/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# View OpenAPI docs
open http://localhost:8500/docs
```

## Error Handling

All endpoints use standardized exception handling via `SkillForgeException`:

```python
from app.core.exceptions import SkillForgeException

raise SkillForgeException(
    message="Validation failed",
    error_code="VALIDATION_ERROR",
    status_code=400
)
```

## Middleware

- **CORS**: Configured for frontend origin (localhost:5173)
- **Request ID**: Adds `X-Request-ID` header for tracing
- **Logging**: Structured logs via structlog

## Related Documentation

- [OpenAPI Schema](http://localhost:8500/openapi.json)
- [Workflow Documentation](../workflows/README.md)
- [Database Repositories](../db/repositories/)

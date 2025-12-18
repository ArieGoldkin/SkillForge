# Database Layer

PostgreSQL database with PGVector extension for semantic search capabilities.

## Structure

```
db/
├── models/              # SQLAlchemy ORM models
│   ├── analysis.py      # Analysis entity
│   ├── artifact.py      # Generated artifacts
│   ├── chunk.py         # Content chunks for search
│   ├── agent_finding.py # Agent execution results
│   └── tutor/           # Tutoring session models
├── repositories/        # Repository pattern for data access
│   ├── analysis_repository.py
│   ├── artifact_repository.py
│   ├── chunk_repository.py
│   └── tutor_repository.py
├── session.py           # Database session management
└── migrations/          # Alembic migration files (../alembic/)
```

## Database Configuration

### Connection

```python
from app.db.session import SessionLocal

async with SessionLocal() as session:
    # Use session here
    pass
```

### Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_POOL_SIZE` - Connection pool size (default: 10)
- `DATABASE_MAX_OVERFLOW` - Max overflow connections (default: 20)

## Models

### Analysis

Core entity for content analysis workflows.

**Fields:**
- `id` (UUID) - Primary key
- `url` (String) - Source URL
- `content_type` (Enum) - article, video, repo
- `status` (Enum) - pending, processing, complete, failed
- `title` (String) - Extracted title
- `raw_content` (Text) - Original content
- `content_embedding` (Vector) - OpenAI text-embedding-3-small (1536 dims)

**Relationships:**
- `artifacts` - Generated artifacts (1:N)
- `chunks` - Content chunks (1:N)
- `agent_findings` - Agent results (1:N)

### Artifact

Generated implementation guides.

**Fields:**
- `id` (UUID) - Primary key
- `analysis_id` (UUID) - Foreign key to Analysis
- `markdown_content` (Text) - Generated markdown
- `metadata` (JSONB) - Artifact metadata
- `download_count` (Integer) - Download analytics

### Chunk

Content chunks for semantic search.

**Fields:**
- `id` (UUID) - Primary key
- `analysis_id` (UUID) - Foreign key to Analysis
- `content` (Text) - Chunk text
- `embedding` (Vector) - Chunk embedding (1536 dims)
- `metadata` (JSONB) - Chunk metadata (section, path, etc.)

**Indexes:**
- `idx_chunk_embedding_ivfflat` - IVFFlat index for vector search
- `idx_chunk_bm25` - GIN index for full-text search

### AgentFinding

Results from specialized analysis agents.

**Fields:**
- `id` (UUID) - Primary key
- `analysis_id` (UUID) - Foreign key to Analysis
- `agent_type` (String) - Agent identifier
- `findings` (JSONB) - Structured findings
- `confidence_score` (Float) - 0-1 confidence
- `processing_time_ms` (Integer) - Execution time

## Repositories

Repository pattern provides abstraction over data access:

```python
from app.db.repositories.analysis_repository import get_analysis_repository

async def my_function(
    repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)]
):
    analysis = await repo.get_by_id(analysis_id)
    # ...
```

### Available Repositories

- `AnalysisRepository` - CRUD + search operations
- `ArtifactRepository` - Artifact retrieval
- `ChunkRepository` - Vector + full-text search
- `TutorRepository` - Session management

## Migrations

Using Alembic for schema versioning.

### Create Migration

```bash
cd backend
poetry run alembic revision --autogenerate -m "Description"
```

### Apply Migrations

```bash
# Upgrade to latest
poetry run alembic upgrade head

# Downgrade one step
poetry run alembic downgrade -1

# View history
poetry run alembic history
```

### Migration Files

Located in `backend/alembic/versions/`

## Vector Search

PGVector extension enables semantic similarity search.

### Embedding Storage

```python
# 1536-dimensional vectors (OpenAI text-embedding-3-small)
content_embedding = Column(Vector(1536))
```

### Similarity Search

```sql
-- Cosine similarity search
SELECT id, 1 - (embedding <=> query_embedding) AS similarity
FROM chunks
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

### Indexing Strategy

- **IVFFlat index**: Fast approximate search (100 lists)
- **Exact search**: Used for small datasets or precise ranking

## Full-Text Search

PostgreSQL tsvector for keyword search.

### TSVector Generation

```python
# Automatic tsvector generation via trigger
tsvector = Column(TSVector)
```

### Search Query

```sql
SELECT ts_rank(tsvector, query) AS rank
FROM chunks
WHERE tsvector @@ to_tsquery('english', 'PostgreSQL & search')
ORDER BY rank DESC;
```

## Hybrid Search (RRF)

Reciprocal Rank Fusion combines semantic + keyword search.

```python
from app.db.repositories.chunk_repository import ChunkRepository

results = await repo.search(
    query="PostgreSQL full-text search",
    mode="hybrid",  # Combines vector + keyword
    top_k=10
)
```

## Performance Optimization

### N+1 Query Prevention

```python
# Use select_related for foreign keys
analysis = await session.execute(
    select(Analysis)
    .options(selectinload(Analysis.artifacts))
    .where(Analysis.id == id)
)
```

### Connection Pooling

```python
# Configured in app/core/config.py
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
```

### Query Monitoring

Enable query logging for development:

```bash
export DATABASE_ECHO=true
```

## Testing

### Test Database

```python
# tests/conftest.py provides test session
@pytest.fixture
async def session(test_db):
    async with test_db() as sess:
        yield sess
```

### Fixtures

```python
@pytest.fixture
async def sample_analysis(session):
    analysis = Analysis(url="https://example.com")
    session.add(analysis)
    await session.commit()
    return analysis
```

## Related Documentation

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PGVector GitHub](https://github.com/pgvector/pgvector)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)

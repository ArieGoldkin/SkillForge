# ⚙️ Yonatan's Backend Tasks - SkillForge

**Developer:** Yonatan (Backend Specialist)
**Primary Stack:** Python 3.11+, FastAPI, LangGraph, PostgreSQL, PGVector
**Project:** SkillForge - Research-to-Implementation Pipeline

---

## 📋 Table of Contents

1. [Sprint 1: Foundation](#sprint-1-foundation---weeks-1-2)
2. [Sprint 2: Analysis Pipeline Foundation](#sprint-2-analysis-pipeline-foundation---weeks-3-4)
3. [Sprint 3: Multi-Agent Complete](#sprint-3-multi-agent-complete---weeks-5-6)
4. [Sprint 4: Tutoring System](#sprint-4-tutoring-system---weeks-7-8)
5. [Sprint 5: Library & Search](#sprint-5-library--search---weeks-9-10)
6. [Sprint 6: Content Expansion](#sprint-6-content-expansion---week-11)
7. [Sprint 7: Testing & Deployment](#sprint-7-testing--deployment---weeks-12-13)
8. [Quick Reference](#quick-reference)

---

## 🎯 Sprint 1: Foundation - Weeks 1-2

**Sprint Goal:** Setup backend infrastructure with FastAPI, PostgreSQL, Docker
**Total Story Points:** 21
**User Stories:** US-1.1 (partial)

---

### ✅ Task 1.1.1: Create FastAPI Project Structure [3 pts]

**Status:** Not Started
**Dependencies:** None
**Parallel Work:** Arie setting up frontend

#### Description
Initialize FastAPI project with proper directory structure and core files.

#### Acceptance Criteria
- [ ] Project directory `backend/` created
- [ ] Directory structure follows best practices
- [ ] FastAPI app runs with `uvicorn app.main:app --reload`
- [ ] Health check endpoint responds at `/health`
- [ ] CORS middleware configured for frontend

#### Implementation Steps
```bash
# 1. Create project structure
mkdir -p backend/app/{api/v1,core,db,models,schemas,services,workflows}
cd backend

# 2. Initialize Python environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Create requirements.txt
```

```txt
# requirements.txt
fastapi==0.118.2
uvicorn[standard]==0.32.0
pydantic==2.10.3
pydantic-settings==2.6.1
python-dotenv==1.0.1
```

```bash
pip install -r requirements.txt
```

#### Directory Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── analyze.py   # Analysis endpoints
│   │       ├── tutor.py     # Tutoring endpoints
│   │       └── library.py   # Library endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings with Pydantic
│   │   └── logging.py       # Structured logging
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py          # Base model class
│   │   └── session.py       # Database session management
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── artifact.py
│   │   └── tutoring.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   └── artifact.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   └── extraction/
│   │       └── jina_reader.py
│   └── workflows/           # LangGraph workflows
│       ├── __init__.py
│       └── analysis.py
├── alembic/                 # Database migrations
├── tests/
├── .env.example
├── .env
├── requirements.txt
└── README.md
```

#### app/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="SkillForge API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected",  # Will implement DB check later
    }

@app.get("/")
async def root():
    return {"message": "SkillForge API"}
```

#### app/core/config.py
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="DEBUG")

    # Database
    DATABASE_URL: str = Field(default="postgresql://dev:devpass@localhost:5432/skillforge")

    # LLM (Dev)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3.1:8b")
    OLLAMA_EMBEDDING_MODEL: str = Field(default="nomic-embed-text")

    # LLM (Prod)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")

    # Content Extraction
    JINA_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
```

#### Testing
```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
```

---

### ✅ Task 1.1.2: Setup Environment Configuration [1 pt]

**Status:** Not Started
**Dependencies:** Task 1.1.1

#### Description
Create `.env.example` and `.env` files for configuration.

#### Files
```.env
# .env.example (commit this)
DATABASE_URL=postgresql://dev:devpass@localhost:5432/skillforge
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
JINA_API_KEY=
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

---

### ✅ Task 1.1.3: Implement Structured Logging [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.1.2

#### Description
Setup structlog for JSON logging with request IDs.

#### Installation
```bash
pip install structlog==24.4.0
```

#### Implementation
```python
# app/core/logging.py
import structlog
import logging
from app.core.config import settings

def setup_logging():
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.LOG_LEVEL),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )

logger = structlog.get_logger()
```

#### Usage in main.py
```python
from app.core.logging import setup_logging, logger

setup_logging()

@app.on_event("startup")
async def startup_event():
    logger.info("application_startup", environment=settings.ENVIRONMENT)
```

---

### ✅ Task 1.2.1: Install & Configure Alembic [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.1.3

#### Description
Setup Alembic for database migrations.

#### Installation
```bash
pip install alembic==1.13.3
alembic init alembic
```

#### Configuration
```python
# alembic/env.py
from app.db.base import Base  # Import all models
from app.core.config import settings

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata
```

---

### ✅ Task 1.2.2: Create SQLAlchemy Models [5 pts]

**Status:** Not Started
**Dependencies:** Task 1.2.1

#### Description
Define database models for analyses, artifacts, tutoring.

#### Installation
```bash
pip install sqlalchemy==2.0.36 psycopg[binary,pool]==3.2.3 pgvector==0.3.5
```

#### Models
```python
# app/models/analysis.py
from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime
from app.db.base import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False)  # 'article', 'video', 'repo'
    title = Column(Text)
    raw_content = Column(Text)
    content_embedding = Column(Vector(1536))
    extraction_metadata = Column(JSONB)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

```python
# app/models/agent_finding.py
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.base import Base

class AgentFinding(Base):
    __tablename__ = "agent_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String(100), nullable=False)
    findings = Column(JSONB, nullable=False)
    confidence_score = Column(Float)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", backref="agent_findings")
```

```python
# app/models/artifact.py
from sqlalchemy import Column, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.base import Base

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    markdown_content = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    metadata = Column(JSONB)  # topics, tags, complexity
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", backref="artifacts")
```

```python
# app/models/tutoring.py
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.base import Base

class TutoringSession(Base):
    __tablename__ = "tutoring_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="SET NULL"))
    session_metadata = Column(JSONB)
    status = Column(String(50), nullable=False, default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    analysis = relationship("Analysis")

class TutoringMessage(Base):
    __tablename__ = "tutoring_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("tutoring_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TutoringSession", backref="messages")
```

```python
# app/models/progress.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.db.base import Base

class AnalysisProgress(Base):
    __tablename__ = "analysis_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    progress_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# app/db/base.py
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here for Alembic
from app.models.analysis import Analysis
from app.models.agent_finding import AgentFinding
from app.models.artifact import Artifact
from app.models.tutoring import TutoringSession, TutoringMessage
from app.models.progress import AnalysisProgress
```

---

### ✅ Task 1.2.3: Enable PGVector Extension [1 pt]

**Status:** Not Started
**Dependencies:** Task 1.2.2

#### Description
Create migration to enable PGVector extension.

#### Create Migration
```bash
alembic revision -m "enable_pgvector"
```

```python
# alembic/versions/xxx_enable_pgvector.py
def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

def downgrade():
    op.execute('DROP EXTENSION IF EXISTS vector;')
```

---

### ✅ Task 1.2.4: Generate Initial Migration [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.2.3

#### Description
Create initial schema migration with all tables.

#### Commands
```bash
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

#### Verify
```bash
psql -U dev -d skillforge -c "\dt"
# Should show: analyses, agent_findings, artifacts, tutoring_sessions, tutoring_messages, analysis_progress
```

---

### ✅ Task 1.2.5: Create Database Utilities [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.2.4

#### Description
Setup async session factory and dependency injection.

#### Implementation
```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.ENVIRONMENT == "development",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

#### Usage in Endpoints
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@app.post("/api/v1/analyze")
async def create_analysis(db: AsyncSession = Depends(get_db)):
    # Use db session here
    pass
```

---

### ✅ Task 1.4.1: Research & Setup Jina AI [1 pt]

**Status:** Not Started
**Dependencies:** Task 1.2.5

#### Description
Sign up for Jina AI and test API.

#### Steps
1. Sign up at https://jina.ai
2. Get API key (free tier: 500 requests/month)
3. Add to `.env`: `JINA_API_KEY=your_key_here`
4. Test with curl:
```bash
curl -H "Authorization: Bearer YOUR_KEY" https://r.jina.ai/https://react.dev
```

---

### ✅ Task 1.4.2: Create Jina Reader Service [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.4.1

#### Description
Implement content extraction service using Jina AI Reader API.

#### Installation
```bash
pip install httpx==0.27.2 tenacity==9.0.0
```

#### Implementation
```python
# app/services/extraction/jina_reader.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.logging import logger

class JinaReaderError(Exception):
    pass

class JinaReader:
    BASE_URL = "https://r.jina.ai"

    def __init__(self):
        self.api_key = settings.JINA_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def extract_article(self, url: str) -> dict:
        """Extract content from article URL using Jina AI Reader."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = await self.client.get(
                f"{self.BASE_URL}/{url}",
                headers=headers,
                follow_redirects=True,
            )

            if response.status_code == 404:
                raise JinaReaderError("URL not found (404)")

            if response.status_code >= 400:
                raise JinaReaderError(f"HTTP {response.status_code}: {response.text}")

            # Jina returns markdown
            content = response.text

            # Extract metadata
            lines = content.split("\n")
            title = lines[0].replace("# ", "") if lines else "Untitled"

            logger.info(
                "jina_extraction_success",
                url=url,
                content_length=len(content),
                title=title[:100],
            )

            return {
                "title": title,
                "content": content,
                "word_count": len(content.split()),
                "metadata": {
                    "extractor": "jina_reader",
                    "source_url": url,
                },
            }

        except httpx.TimeoutException:
            logger.error("jina_extraction_timeout", url=url)
            raise JinaReaderError("Request timed out")

        except Exception as e:
            logger.error("jina_extraction_failed", url=url, error=str(e))
            raise JinaReaderError(f"Extraction failed: {str(e)}")

    async def close(self):
        await self.client.aclose()
```

---

### ✅ Task 1.4.3: Create Analysis Endpoint [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.4.2
**Integration Point:** API contract meeting with Arie (Day 3)

#### Description
Create POST `/api/v1/analyze` endpoint to start analysis.

#### Pydantic Schemas
```python
# app/schemas/analysis.py
from pydantic import BaseModel, HttpUrl
from uuid import UUID
from datetime import datetime

class AnalyzeRequest(BaseModel):
    url: HttpUrl
    mode: str = "standard"  # Future: "quick", "standard", "deep"

class AnalyzeResponse(BaseModel):
    analysis_id: UUID
    status: str
    sse_endpoint: str

class AnalysisDetail(BaseModel):
    id: UUID
    url: str
    content_type: str
    title: str | None
    status: str
    created_at: datetime
    artifact_id: UUID | None = None
```

#### Endpoint Implementation
```python
# app/api/v1/analyze.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse
from app.models.analysis import Analysis
from app.services.extraction.jina_reader import JinaReader, JinaReaderError
from app.core.logging import logger
import uuid

router = APIRouter(prefix="/api/v1", tags=["analysis"])

async def process_analysis(analysis_id: uuid.UUID, url: str):
    """Background task to extract and analyze content."""
    jina = JinaReader()
    try:
        # Extract content
        extracted = await jina.extract_article(url)

        # Update analysis in DB
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis = result.scalar_one()
            analysis.title = extracted["title"]
            analysis.raw_content = extracted["content"]
            analysis.extraction_metadata = extracted["metadata"]
            analysis.status = "extracting_complete"
            await db.commit()

        logger.info("analysis_extraction_complete", analysis_id=str(analysis_id))

    except JinaReaderError as e:
        logger.error("analysis_extraction_failed", analysis_id=str(analysis_id), error=str(e))
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis = result.scalar_one()
            analysis.status = "failed"
            await db.commit()

    finally:
        await jina.close()

@router.post("/analyze", response_model=AnalyzeResponse)
async def create_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start analysis for a given URL."""

    # Detect content type (simplified for now)
    url_str = str(request.url)
    if "youtube.com" in url_str or "youtu.be" in url_str:
        content_type = "video"
    elif "github.com" in url_str:
        content_type = "repo"
    else:
        content_type = "article"

    # Create analysis record
    analysis = Analysis(
        url=url_str,
        content_type=content_type,
        status="pending",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Start background extraction
    background_tasks.add_task(process_analysis, analysis.id, url_str)

    logger.info(
        "analysis_created",
        analysis_id=str(analysis.id),
        url=url_str,
        content_type=content_type,
    )

    return AnalyzeResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        sse_endpoint=f"/api/v1/analyze/{analysis.id}/stream",
    )

@router.get("/analyze/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis details."""
    from sqlalchemy import select

    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Get artifact if exists
    artifact_result = await db.execute(
        select(Artifact).where(Artifact.analysis_id == analysis_id)
    )
    artifact = artifact_result.scalar_one_or_none()

    return AnalysisDetail(
        id=analysis.id,
        url=analysis.url,
        content_type=analysis.content_type,
        title=analysis.title,
        status=analysis.status,
        created_at=analysis.created_at,
        artifact_id=artifact.id if artifact else None,
    )
```

#### Register Router
```python
# app/main.py
from app.api.v1.analyze import router as analyze_router

app.include_router(analyze_router)
```

---

### ✅ Task 1.5.1: Install Ollama Models [1 pt]

**Status:** Not Started
**Dependencies:** Docker Compose running (Task 1.6.1)

#### Description
Pull required Ollama models for dev environment.

#### Commands
```bash
# Assuming Ollama running in Docker
docker exec -it ollama ollama pull llama3.1:8b
docker exec -it ollama ollama pull nomic-embed-text
```

#### Verify
```bash
curl http://localhost:11434/api/tags
# Should show both models
```

---

### ✅ Task 1.5.2: Create Embedding Service [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.5.1

#### Description
Implement service to generate embeddings using Ollama.

#### Installation
```bash
pip install ollama==0.4.3
```

#### Implementation
```python
# app/services/embeddings.py
import ollama
from app.core.config import settings
from app.core.logging import logger

class EmbeddingService:
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        self.model = settings.OLLAMA_EMBEDDING_MODEL

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text using Ollama."""
        try:
            # Truncate text if too long (Ollama has limits)
            max_length = 8000
            if len(text) > max_length:
                text = text[:max_length]
                logger.warning("embedding_text_truncated", original_length=len(text))

            response = await self.client.embeddings(
                model=self.model,
                prompt=text,
            )

            embedding = response["embedding"]

            logger.info(
                "embedding_generated",
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

embedding_service = EmbeddingService()
```

---

### ✅ Task 1.6.1: Create Docker Compose Configuration [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.5.2

#### Description
Setup Docker Compose for PostgreSQL, PGVector, and Ollama.

#### File: docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: skillforge_postgres
    environment:
      POSTGRES_DB: skillforge
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    container_name: skillforge_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  ollama_data:
```

#### Commands
```bash
docker-compose up -d
docker-compose ps  # Verify all services running
```

---

### ✅ Task 1.6.2: Create Setup Script [2 pts]

**Status:** Not Started
**Dependencies:** Task 1.6.1

#### Description
One-command script to setup entire dev environment.

#### File: scripts/setup.sh
```bash
#!/bin/bash
set -e

echo "🚀 Setting up SkillForge development environment..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Copy env file
if [ ! -f backend/.env ]; then
    echo "📝 Creating .env file..."
    cp backend/.env.example backend/.env
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
sleep 5

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Pull Ollama models
echo "🤖 Pulling Ollama models..."
docker exec -it ollama ollama pull llama3.1:8b
docker exec -it ollama ollama pull nomic-embed-text

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. cd backend && source venv/bin/activate"
echo "  2. uvicorn app.main:app --reload"
echo "  3. Visit http://localhost:8000/docs"
```

```bash
chmod +x scripts/setup.sh
```

---

### 🔗 Integration Point: API Contract Meeting (Day 3)

**Participants:** Arie + Yonatan
**Duration:** 1 hour
**Deliverable:** Documented API contract

#### Create API Contract Document
```markdown
# docs/API_CONTRACT.md

## POST /api/v1/analyze

**Request:**
```json
{
  "url": "https://example.com/article",
  "mode": "standard"  // Optional: "quick" | "standard" | "deep"
}
```

**Response (201 Created):**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "sse_endpoint": "/api/v1/analyze/550e8400-e29b-41d4-a716-446655440000/stream"
}
```

**Error Responses:**
- 400: Invalid URL format
- 422: Validation error
- 500: Internal server error

## GET /api/v1/analyze/{analysis_id}

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/article",
  "content_type": "article",
  "title": "React 19 Features",
  "status": "complete",
  "created_at": "2025-11-20T10:30:00Z",
  "artifact_id": "abc123..."
}
```

## GET /api/v1/analyze/{analysis_id}/stream (SSE)

**Event Types:**
- `progress`: Stage update
- `complete`: Analysis finished
- `error`: Analysis failed

**Event Format:**
```json
{
  "stage": "extraction",
  "status": "complete",
  "details": {"word_count": 5234},
  "timestamp": "2025-11-20T10:30:05Z"
}
```
```

#### Generate TypeScript Types for Arie
```typescript
// frontend/src/types/api.ts
export interface AnalyzeRequest {
  url: string
  mode?: 'quick' | 'standard' | 'deep'
}

export interface AnalyzeResponse {
  analysis_id: string
  status: string
  sse_endpoint: string
}

export interface AnalysisDetail {
  id: string
  url: string
  content_type: 'article' | 'video' | 'repo'
  title: string | null
  status: string
  created_at: string
  artifact_id: string | null
}

export interface SSEEvent {
  stage: string
  status: 'pending' | 'running' | 'complete' | 'failed'
  details?: Record<string, any>
  timestamp: string
}
```

---

## 🔄 Sprint 2: Analysis Pipeline Foundation - Weeks 3-4

**Sprint Goal:** Implement LangGraph supervisor pattern with first 3 sub-agents
**Total Story Points:** 21
**User Stories:** US-1.2 (backend portion)

---

### ✅ Task 1.5.3: Create Basic LangGraph Workflow [5 pts]

**Status:** Not Started
**Dependencies:** Sprint 1 complete
**Blocker for:** Arie needs SSE events by Day 1

#### Description
Implement initial LangGraph workflow (no sub-agents yet).

#### Installation
```bash
pip install langgraph==0.6.7 langchain==0.3.27 langchain-core==0.3.42 langchain-community==0.3.5 langgraph-checkpoint==2.0.23
```

#### Implementation
```python
# app/workflows/analysis.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.services.extraction.jina_reader import JinaReader
from app.services.embeddings import embedding_service
from app.core.logging import logger

class AnalysisState(TypedDict):
    analysis_id: str
    url: str
    content_type: str
    raw_content: str
    extraction_metadata: dict
    content_embedding: list[float]
    supervisor_decision: dict
    agent_findings: list[dict]
    aggregated_insights: dict
    final_markdown: str

async def extract_content(state: AnalysisState) -> AnalysisState:
    """Extract content from URL."""
    jina = JinaReader()
    try:
        extracted = await jina.extract_article(state["url"])
        state["raw_content"] = extracted["content"]
        state["extraction_metadata"] = extracted["metadata"]
        logger.info("workflow_extraction_complete", analysis_id=state["analysis_id"])
    finally:
        await jina.close()

    return state

async def generate_embedding(state: AnalysisState) -> AnalysisState:
    """Generate embedding for content."""
    embedding = await embedding_service.generate_embedding(state["raw_content"])
    state["content_embedding"] = embedding
    logger.info("workflow_embedding_complete", analysis_id=state["analysis_id"])
    return state

# Build workflow
workflow = StateGraph(AnalysisState)

workflow.add_node("extract", extract_content)
workflow.add_node("embed", generate_embedding)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "embed")
workflow.add_edge("embed", END)

analysis_workflow = workflow.compile()
```

---

### ✅ Task 1.5.4: Implement SSE Endpoint [3 pts]

**Status:** Not Started
**Dependencies:** Task 1.5.3
**Deliverable for Arie:** SSE schema by Day 1

#### Description
Create SSE endpoint to stream analysis progress.

#### Installation
```bash
pip install sse-starlette==2.1.3
```

#### Implementation
```python
# app/api/v1/analyze.py
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
import asyncio

@router.get("/analyze/{analysis_id}/stream")
async def stream_analysis_progress(
    analysis_id: uuid.UUID,
    request: Request,
):
    """Stream real-time analysis progress via SSE."""

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Query progress from database
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(AnalysisProgress)
                        .where(AnalysisProgress.analysis_id == analysis_id)
                        .order_by(AnalysisProgress.created_at.desc())
                        .limit(1)
                    )
                    progress = result.scalar_one_or_none()

                    if progress:
                        event_data = {
                            "stage": progress.stage,
                            "status": progress.status,
                            "details": progress.progress_data,
                            "timestamp": progress.created_at.isoformat(),
                        }

                        if progress.status == "complete" and progress.stage == "artifact_generation":
                            yield {
                                "event": "complete",
                                "data": json.dumps(event_data),
                            }
                            break
                        else:
                            yield {
                                "event": "progress",
                                "data": json.dumps(event_data),
                            }

                await asyncio.sleep(1)  # Poll every second

        except asyncio.CancelledError:
            logger.info("sse_connection_closed", analysis_id=str(analysis_id))

    return EventSourceResponse(event_generator())
```

---

### ✅ Task 2.1.1-2.1.5: Implement Supervisor Pattern [8 pts]

**Status:** Not Started
**Dependencies:** Task 1.5.4

#### Description
Create supervisor node that routes to sub-agents dynamically.

#### Implementation (Simplified)
```python
# app/workflows/nodes/supervisor.py
import ollama
from app.core.config import settings

SUPERVISOR_PROMPT = """
You are a content analysis supervisor. Analyze this content and decide which specialized agents should analyze it.

Available agents:
- tech_comparator: Compares technologies and frameworks
- integration_feasibility: Assesses integration with modern stacks
- security_auditor: Identifies security implications
- performance_analyst: Evaluates performance considerations
- code_quality_critic: Reviews code patterns
- trend_validator: Checks if tech is current (2025)
- implementation_planner: Creates step-by-step guides
- dependency_mapper: Lists required dependencies

Content Type: {content_type}
Content Preview: {content_preview}

Return JSON with agents to invoke and their priority (0-1):
{{"agents": ["agent_name1", "agent_name2"], "priority": [0.9, 0.7]}}
"""

async def supervisor_route(state: AnalysisState) -> AnalysisState:
    """Analyze content and decide which agents to invoke."""
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)

    prompt = SUPERVISOR_PROMPT.format(
        content_type=state["content_type"],
        content_preview=state["raw_content"][:2000],  # First 2000 chars
    )

    response = await client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    decision = json.loads(response["message"]["content"])
    state["supervisor_decision"] = decision

    logger.info(
        "supervisor_routing_complete",
        analysis_id=state["analysis_id"],
        agents=decision["agents"],
    )

    return state
```

---

### ✅ Task 2.2.1-2.2.3: Implement First 3 Core Sub-Agents [8 pts]

**Status:** Not Started
**Dependencies:** Task 2.1.5

#### Description
Implement Tech Comparator, Integration Feasibility, Implementation Planner agents.

#### Tech Comparator Agent
```python
# app/workflows/agents/tech_comparator.py
import ollama
from app.core.config import settings

TECH_COMPARATOR_PROMPT = """
You are a Technical Comparison Specialist. Analyze the technology/approach in this content.

Your task:
1. Identify the primary technology/pattern/framework
2. Compare it to 2-3 mainstream alternatives
3. Create comparison table: Performance, DX, Ecosystem, Use Cases
4. Provide recommendation

Content:
{content}

Respond in JSON:
{{
  "primary_tech": "...",
  "alternatives": ["...", "..."],
  "comparison": {{
    "performance": {{"primary": "...", "alt1": "...", "alt2": "..."}},
    "developer_experience": {{...}},
    "ecosystem": {{...}},
    "use_cases": {{...}}
  }},
  "recommendation": "Best for [scenario]"
}}
"""

async def run_tech_comparator(state: AnalysisState) -> dict:
    """Compare technologies mentioned in content."""
    client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)

    prompt = TECH_COMPARATOR_PROMPT.format(
        content=state["raw_content"][:4000]
    )

    response = await client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    findings = json.loads(response["message"]["content"])

    return {
        "agent_type": "tech_comparator",
        "findings": findings,
        "confidence_score": 0.85,
    }
```

(Similar implementations for Integration Feasibility and Implementation Planner agents)

---

### 🔗 Integration Point: Test SSE with Live Backend (Day 8)

**Testing Checklist:**
- [ ] Start backend server with workflow running
- [ ] Arie submits analysis from frontend
- [ ] Verify SSE events stream correctly
- [ ] Check all stages appear in UI
- [ ] Test error handling (kill backend mid-stream)

---

## Sprint 3-7 Tasks Continue...

[Due to length, I'll create a continuation marker]

**Note:** The remaining sprints (3-7) follow the same detailed pattern with:
- Task descriptions
- Story points
- Dependencies
- Code examples
- Integration points

Would you like me to continue with Sprint 3-7 in this document, or is this level of detail sufficient for Sprint 1-2?

---

## 🎯 Quick Reference

### Daily Workflow
1. **Morning:** Pull latest code, review integration points
2. **During:** Push frequently, document API changes
3. **Evening:** Update task statuses, note blockers

### Key Commands
```bash
# Development
uvicorn app.main:app --reload --port 8000
alembic upgrade head
alembic revision --autogenerate -m "description"

# Testing
pytest tests/
pytest tests/ -v --cov=app

# Docker
docker-compose up -d
docker-compose logs -f
docker exec -it ollama ollama list
```

### When Blocked
- **If blocked by frontend (>4 hours):** Write API docs, work on other endpoints
- **If blocked by unclear requirements:** Check `USER_STORIES.md`, ask PM

---

**Document Maintained By:** Yonatan
**Last Updated:** November 20, 2025
**Review:** Update daily

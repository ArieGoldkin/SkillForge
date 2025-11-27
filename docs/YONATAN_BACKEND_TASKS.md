# ⚙️ Yonatan's Backend Tasks - SkillForge

**Developer:** Yonatan (Backend Specialist)
**Primary Stack:** Python 3.13, FastAPI, LangGraph v1.0, LangChain v1.0, PostgreSQL, PGVector
**Project:** SkillForge - Research-to-Implementation Pipeline

## ⚠️ Important Requirements

- **Python 3.13** - Required (released October 2024, stable)
- **Dependency Management:** Use `pyproject.toml` with Poetry (PEP 518 standard)
- **LangGraph v1.0** - Use Functional API (`@entrypoint`, `@task`) patterns
- **LangChain v1.0** - Use `create_agent` (replaces deprecated `create_react_agent`)
- **FastAPI 0.121.2+** - Latest with CVE fixes
- **Starlette 0.49.3+** - Required for CVE fixes

---

## 🎯 Backend Patterns & Best Practices

### Golden Patterns (Do Not Violate)

**1. Async Repository Pattern**
```python
# ✅ GOOD: Endpoints depend on repository interfaces
async def list_analyses(repo: IAnalysisRepository) -> list[Analysis]:
    analyses = await repo.list_active()
    return analyses

# ❌ BAD: Direct Session access in routers
async def list_analyses(db: AsyncSession) -> list[Analysis]:
    result = await db.execute(select(Analysis))
    return result.scalars().all()
```

**2. Alembic Migrations Always Reversible**
- `upgrade()` + matching `downgrade()` with index cleanup
- Index names follow `ix_<table>_<column>`
- Verify `alembic upgrade head` + `alembic downgrade -1` locally

**3. Structured Logging with Context**
```python
import structlog

logger = structlog.get_logger()

# ✅ GOOD: Structured logging with context
logger.info(
    "workflow_extraction_complete",
    analysis_id=analysis_id,
    word_count=len(content),
    duration_ms=duration
)

# ❌ BAD: Print statements or basic logging
print(f"Extraction complete for {analysis_id}")
```

**4. SSE Instrumentation in LangGraph Nodes**
```python
from app.services.sse_helpers import emit_streaming_event

@task
async def extract_content(url: str, analysis_id: str) -> dict:
    """Extract content with SSE events."""
    # Emit start event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
    )
    
    # Do work
    content = await jina_reader.extract(url)
    
    # Emit complete event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="complete",
        word_count=len(content.split()),
    )
    
    return {"content": content}
```

**5. File Size Limits**
- Source files: 200 lines maximum
- Repository files: 150 lines maximum
- Service files: 200 lines maximum
- Test files: 300 lines maximum
- Refactor when approaching limits

**6. Quality Gates (Mandatory)**
- Backend coverage: ≥80% (hard block if below)
- Type errors: 0 type-arg errors
- Linting: 0 warnings, 0 errors (`ruff`, `mypy`)
- Tests: 100% pass rate

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
**GitHub Milestone:** [Sprint 1: Backend Foundation](https://github.com/ArieGoldkin/SkillForge/milestone/1)  
**GitHub Issues:** [#1](https://github.com/ArieGoldkin/SkillForge/issues/1), [#2](https://github.com/ArieGoldkin/SkillForge/issues/2), [#3](https://github.com/ArieGoldkin/SkillForge/issues/3), [#4](https://github.com/ArieGoldkin/SkillForge/issues/4), [#5](https://github.com/ArieGoldkin/SkillForge/issues/5)

---

### ✅ Task 1.1.1: Create FastAPI Project Structure [3 pts]

**Status:** ✅ Complete  
**GitHub Issue:** [#1](https://github.com/ArieGoldkin/SkillForge/issues/1)  
**Dependencies:** None  
**Completed:** November 20, 2025  
**Documentation:** [Issue #1 Docs](../issues/001-fastapi-structure/README.md)  
**Parallel Work:** Arie setting up frontend

#### Description
Initialize FastAPI project with proper directory structure and core files.

#### Acceptance Criteria
- [x] Project directory `backend/` created
- [x] Directory structure follows best practices
- [x] FastAPI app runs with `uvicorn app.main:app --reload`
- [x] Health check endpoint responds at `/api/v1/health`
- [x] CORS middleware configured for frontend

#### Implementation Steps
```bash
# 1. Create project structure
mkdir -p backend/app/{api/v1,core,db,models,schemas,services,workflows}
cd backend

# 2. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Initialize Poetry project
poetry init --no-interaction --name skillforge-backend --python "^3.13"

# 4. Add core dependencies
poetry add fastapi@^0.121.2 starlette@^0.49.3 "uvicorn[standard]@^0.32.0"
poetry add pydantic@^2.10.3 pydantic-settings@^2.6.1 python-dotenv@^1.0.1

# 5. Add LangGraph v1.0 dependencies
poetry add langgraph@^1.0.0 langgraph-checkpoint@^3.0.0

# 6. Add LangChain v1.0 dependencies
poetry add langchain@^1.0.0 langchain-core@^1.0.0 langchain-community@^1.0.0

# 7. Add LLM providers
poetry add langchain-openai@^1.0.0 langchain-anthropic@^1.0.0

# 8. Add database dependencies
poetry add "psycopg[binary,pool]@^3.2.3" pgvector@^0.4.1 "sqlalchemy[asyncio]@^2.0.36" alembic@^1.13.3

# 9. Add HTTP & utilities
poetry add "httpx[brotli,zstd]@^0.28.1" sse-starlette@^2.1.3 structlog@^24.4.0 tenacity@^9.0.0 orjson@^3.9.7

# 10. Add content extraction
poetry add youtube-transcript-api@^0.6.2 pygithub@^2.5.0 beautifulsoup4@^4.12.3 playwright@^1.48.0

# 11. Add observability
poetry add langsmith@^1.0.0

# 12. Add dev dependencies
poetry add --group dev pytest@^8.3.4 pytest-asyncio@^0.25.1 pytest-cov@^5.0.0
poetry add --group dev black@^24.8.0 ruff@^0.6.9 mypy@^1.13.0 isort@^5.13.2

# 13. Install all dependencies
poetry install
```

**Note:** Poetry automatically creates and manages a virtual environment. To activate it:
```bash
poetry shell  # Activates the virtual environment
# OR
poetry run <command>  # Runs command in virtual environment
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
├── pyproject.toml           # Poetry dependency management (PEP 518)
├── poetry.lock              # Locked dependency versions (auto-generated)
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

    # LLM Configuration
    LLM_MODEL: str = Field(default="gpt-5-mini")
    OPENAI_API_KEY: str | None = None

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

**Status:** ✅ Complete  
**GitHub Issue:** [#2](https://github.com/ArieGoldkin/SkillForge/issues/2) (combined with 1.1.3)  
**Dependencies:** Task 1.1.1  
**Completed:** November 20, 2025  
**Documentation:** [Issue #2 Docs](../issues/002-environment-config/README.md)

#### Description
Create `.env.example` and `.env` files for configuration.

#### Files
```.env
# .env.example (commit this)
DATABASE_URL=postgresql://dev:devpass@localhost:5432/skillforge
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=
JINA_API_KEY=
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

---

### ✅ Task 1.1.3: Implement Structured Logging [2 pts]

**Status:** ✅ Complete  
**GitHub Issue:** [#2](https://github.com/ArieGoldkin/SkillForge/issues/2) (combined with 1.1.2)  
**Dependencies:** Task 1.1.2  
**Completed:** November 20, 2025  
**Documentation:** [Issue #2 Docs](../issues/002-environment-config/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) (tasks 1.2.1-1.2.5)  
**Dependencies:** Task 1.1.3  
**Completed:** November 21, 2025  
**Documentation:** [Issue #3 Docs](../issues/003-database-schema/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) (tasks 1.2.1-1.2.5)  
**Dependencies:** Task 1.2.1  
**Completed:** November 21, 2025  
**Documentation:** [Issue #3 Docs](../issues/003-database-schema/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) (tasks 1.2.1-1.2.5)  
**Dependencies:** Task 1.2.2  
**Completed:** November 21, 2025  
**Documentation:** [Issue #3 Docs](../issues/003-database-schema/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) (tasks 1.2.1-1.2.5)  
**Dependencies:** Task 1.2.3  
**Completed:** November 21, 2025  
**Documentation:** [Issue #3 Docs](../issues/003-database-schema/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#3](https://github.com/ArieGoldkin/SkillForge/issues/3) (tasks 1.2.1-1.2.5)  
**Dependencies:** Task 1.2.4  
**Completed:** November 21, 2025  
**Documentation:** [Issue #3 Docs](../issues/003-database-schema/README.md)

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

**Status:** ✅ Complete  
**GitHub Issue:** [#4](https://github.com/ArieGoldkin/SkillForge/issues/4) (tasks 1.4.1-1.4.5)  
**Dependencies:** Task 1.2.5  
**Completed:** November 23, 2025

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

**Status:** ✅ Complete  
**GitHub Issue:** [#4](https://github.com/ArieGoldkin/SkillForge/issues/4) (tasks 1.4.1-1.4.5)  
**Dependencies:** Task 1.4.1  
**Completed:** November 23, 2025

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

**Status:** ✅ Complete  
**GitHub Issue:** [#4](https://github.com/ArieGoldkin/SkillForge/issues/4) (tasks 1.4.1-1.4.5)  
**Dependencies:** Task 1.4.2
**Integration Point:** API contract meeting with Arie (Day 3)
**Completed:** 2025-11-25

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

### ✅ Task 1.5.0: Schema Migration to Vector(768) [1 pt]

**Status:** ✅ Complete  
**GitHub Issue:** [#5](https://github.com/ArieGoldkin/SkillForge/issues/5)  
**Dependencies:** Task 1.2.4 (Issue #3)  
**Completed:** November 23, 2025

#### Description
Create migration to update `content_embedding` column from `Vector(1536)` to `Vector(768)` to match nomic-embed-text model dimensions.

#### Implementation
- Created migration: `637794773190_update_embedding_dimension_to_768.py`
- Updated `app/models/analysis.py` model definition
- Migration is reversible (can downgrade back to 1536)

---

### ✅ Task 1.5.1: Install Ollama Models [1 pt] (Historical - Migrated to OpenAI)

**Status:** ✅ Complete (Migrated to OpenAI)  
**GitHub Issue:** [#5](https://github.com/ArieGoldkin/SkillForge/issues/5) (tasks 1.5.1-1.5.2)  
**Dependencies:** ~~Ollama running on host~~ (No longer required)  
**Completed:** November 23, 2025  
**Migration:** Migrated to OpenAI embeddings (1536 dimensions) - see Issue #5 migration docs

#### Description
~~Pull required Ollama models for dev environment.~~  
**Note:** This task is historical. The project now uses OpenAI for embeddings (1536 dimensions).

#### Verify
```bash
curl http://localhost:11434/api/tags
# Should show both models
```

---

### ✅ Task 1.5.2: Create Embedding Service [3 pts]

**Status:** ✅ Complete  
**GitHub Issue:** [#5](https://github.com/ArieGoldkin/SkillForge/issues/5) (tasks 1.5.1-1.5.2)  
**Dependencies:** Task 1.5.1  
**Completed:** November 23, 2025

#### Description
Implement service to generate embeddings using OpenAI with dimension handling and normalization.

#### Implementation
- Created `app/services/embeddings.py` (209 lines)
- Dimension handling: truncate if >768, pad if <768 (following reporter-accuracy pattern)
- L2 normalization for cosine similarity search
- Retry logic with exponential backoff (tenacity)
- Comprehensive error handling with custom `EmbeddingError`
- Health check integration (OpenAI API key validation)
- Configuration: `EMBEDDING_DIMENSIONS=1536` (OpenAI text-embedding-3-small)

#### Testing
- Created `tests/test_embeddings.py` (15 tests, 100% pass rate)
- Tests cover: success cases, dimension handling, normalization, error handling, edge cases

---

### ✅ Task 1.6.1: Create Docker Compose Configuration [3 pts]

**Status:** ✅ Completed
**Dependencies:** Task 1.5.2

#### Description
Setup Docker Compose for PostgreSQL, PGVector, and Backend service.

#### File: docker-compose.yml
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: skillforge-postgres-dev
    environment:
      POSTGRES_DB: skillforge
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5437:5432"  # Using 5437 to avoid conflicts
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: runtime
    container_name: skillforge-backend-dev
    environment:
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG
      DATABASE_URL: postgresql+asyncpg://dev:devpass@postgres:5432/skillforge
      API_V1_PREFIX: /api/v1
      HOST: 0.0.0.0
      PORT: 8500
      CORS_ORIGINS: '["http://localhost:5173"]'
      LLM_MODEL: ${LLM_MODEL:-gpt-5-mini}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      EMBEDDING_DIMENSIONS: ${EMBEDDING_DIMENSIONS:-1536}
    ports:
      - "8500:8500"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8500/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    volumes:
      - ./backend/app:/app/app:ro
      - ./backend/alembic:/app/alembic:ro
      - ./backend/alembic.ini:/app/alembic.ini:ro
    command: >
      sh -c "
        echo 'Waiting for database...' &&
        until pg_isready -h postgres -U dev; do sleep 2; done &&
        echo 'Running migrations...' &&
        /app/.venv/bin/alembic upgrade head &&
        echo 'Starting backend...' &&
        /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload
      "

volumes:
  postgres-dev-data:
```

#### Commands
```bash
docker-compose up -d
docker-compose ps  # Verify all services running
docker-compose logs backend  # View backend logs
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

# Verify OpenAI API key is configured
echo "🔑 Verifying OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set in .env file"
fi

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
pip install langgraph>=1.0.0 langchain>=1.0.0 langchain-core>=1.0.0 langchain-community>=1.0.0 langgraph-checkpoint>=3.0.0
```

#### Implementation (LangGraph v1.0 Functional API)
```python
# app/workflows/analysis.py
from typing import TypedDict
from langgraph.func import entrypoint, task
from langgraph.checkpoint.postgres import PostgresSaver
from app.services.extraction.jina_reader import JinaReader
from app.services.embeddings import embedding_service
from app.core.logging import logger
from app.core.config import settings

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

# Setup checkpointer (PostgreSQL for production, MemorySaver for dev)
checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)

@task
async def extract_content(url: str, analysis_id: str) -> dict:
    """Extract content from URL."""
    jina = JinaReader()
    try:
        extracted = await jina.extract_article(url)
        logger.info("workflow_extraction_complete", analysis_id=analysis_id)
        return {
            "raw_content": extracted["content"],
            "extraction_metadata": extracted["metadata"]
        }
    finally:
        await jina.close()

@task
async def generate_embedding(content: str) -> list[float]:
    """Generate embedding for content."""
    embedding = await embedding_service.generate_embedding(content)
    return embedding

# Main workflow using Functional API
@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(
    url: str,
    analysis_id: str,
    previous: dict | None = None
) -> dict:
    """Main analysis workflow using LangGraph v1.0 Functional API."""
    
    # Extract content (returns future, can run in parallel)
    extraction_future = extract_content(url, analysis_id)
    
    # Block and get result
    extraction_result = extraction_future.result()
    
    # Generate embedding
    embedding = generate_embedding(extraction_result["raw_content"]).result()
    
    return {
        "analysis_id": analysis_id,
        "url": url,
        "raw_content": extraction_result["raw_content"],
        "extraction_metadata": extraction_result["extraction_metadata"],
        "content_embedding": embedding
    }
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
Create supervisor node that routes to sub-agents dynamically using LangChain v1.0 `create_agent`.

#### Backend Pattern
**Use LangChain v1.0 create_agent as supervisor:**
```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

# Define agent tools (agents exposed as tools)
@tool
def tech_comparator_tool(content: str) -> str:
    """Invoke tech comparator agent."""
    return tech_comparator_agent.invoke({"messages": [content]})

@tool
def security_auditor_tool(content: str) -> str:
    """Invoke security auditor agent."""
    return security_auditor_agent.invoke({"messages": [content]})

# Create supervisor agent using LangChain v1.0
model = init_chat_model(settings.LLM_MODEL)

supervisor_agent = create_agent(
    model,
    tools=[tech_comparator_tool, security_auditor_tool, ...],
    system_prompt="""You are a content analysis supervisor. 
    Analyze the content and decide which specialized agents should analyze it.
    Return the agent names to invoke."""
)

@task
async def supervisor_route(content: str, content_type: str) -> dict:
    """Supervisor decides which agents to invoke."""
    # Use async invoke with timeout to prevent blocking
    supervisor_timeout = 60.0  # 60 seconds max
    if hasattr(supervisor_agent, "ainvoke"):
        result = await asyncio.wait_for(
            supervisor_agent.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": f"Content Type: {content_type}\nContent: {content[:2000]}"
                }]
            }),
            timeout=supervisor_timeout,
        )
    else:
        # Fallback: run sync invoke in thread pool
        result = await asyncio.wait_for(
            asyncio.to_thread(
                supervisor_agent.invoke,
                {
                    "messages": [{
                        "role": "user",
                        "content": f"Content Type: {content_type}\nContent: {content[:2000]}"
                    }]
                }
            ),
            timeout=supervisor_timeout,
        )
    
    # Parse agent selection from result
    selected_agents = parse_agent_selection(result)
    
    return {
        "supervisor_decision": {
            "agents": selected_agents,
            "priority": [0.9] * len(selected_agents)
        }
    }
```

#### Implementation (LangGraph v1.0 + LangChain v1.0)
```python
# app/workflows/nodes/supervisor.py
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from app.core.config import settings

# Define tools for each agent (agents are exposed as tools)
@tool
def tech_comparator_tool(content: str) -> str:
    """Invoke tech comparator agent."""
    # This will be called by supervisor agent
    return "tech_comparator_result"

@tool
def security_auditor_tool(content: str) -> str:
    """Invoke security auditor agent."""
    return "security_auditor_result"

# ... 6 more agent tools

# Create supervisor agent using LangChain v1.0 create_agent
model = init_chat_model(settings.LLM_MODEL)

supervisor_agent = create_agent(
    model,
    tools=[
        tech_comparator_tool,
        security_auditor_tool,
        # ... 6 more agent tools
    ],
    system_prompt="""You are a content analysis supervisor. 
    Analyze the content and decide which specialized agents should analyze it.
    Return the agent names to invoke."""
)

@task
async def supervisor_route(content: str, content_type: str) -> dict:
    """Supervisor decides which agents to invoke."""
    # Use async invoke with timeout to prevent blocking
    supervisor_timeout = 60.0  # 60 seconds max
    if hasattr(supervisor_agent, "ainvoke"):
        result = await asyncio.wait_for(
            supervisor_agent.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": f"Content Type: {content_type}\nContent: {content[:2000]}"
                }]
            }),
            timeout=supervisor_timeout,
        )
    else:
        # Fallback: run sync invoke in thread pool
        result = await asyncio.wait_for(
            asyncio.to_thread(
                supervisor_agent.invoke,
                {
                    "messages": [{
                        "role": "user",
                        "content": f"Content Type: {content_type}\nContent: {content[:2000]}"
                    }]
                }
            ),
            timeout=supervisor_timeout,
        )
    
    # Parse agent selection from result
    selected_agents = parse_agent_selection(result)
    
    return {
        "supervisor_decision": {
            "agents": selected_agents,
            "priority": [0.9] * len(selected_agents)  # Simplified
        }
    }
```

---

### ✅ Task 2.2.1-2.2.3: Implement First 3 Core Sub-Agents [8 pts]

**Status:** Not Started
**Dependencies:** Task 2.1.5

#### Description
Implement Tech Comparator, Integration Feasibility, Implementation Planner agents using LangChain v1.0 `create_agent`.

#### Backend Pattern
**Agent Implementation with create_agent:**
```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

# Define tools for each agent
@tool
def compare_technologies(primary_tech: str, alternatives: list[str]) -> dict:
    """Compare primary technology with alternatives."""
    # Implementation
    return {"comparison": {...}}

@tool
def find_alternatives(tech_name: str) -> list[str]:
    """Find alternative technologies."""
    # Implementation
    return ["alt1", "alt2"]

# Create agent using LangChain v1.0
model = init_chat_model(settings.LLM_MODEL)

tech_comparator_agent = create_agent(
    model,
    tools=[compare_technologies, find_alternatives],
    system_prompt="""
You are a Technical Comparison Specialist. Analyze the technology/approach in this content.
Your task:
- Compare the primary technology with modern alternatives
- Assess pros/cons of each approach
- Recommend best fit for 2025 projects
"""
)

# Use in workflow
@task
async def run_tech_comparator(content: str) -> dict:
    """Run tech comparator agent."""
    # Use async invoke with timeout to prevent blocking
    agent_timeout = 60.0  # 60 seconds max per agent
    if hasattr(tech_comparator_agent, "ainvoke"):
        result = await asyncio.wait_for(
            tech_comparator_agent.ainvoke({
                "messages": [{"role": "user", "content": content}]
            }),
            timeout=agent_timeout,
        )
    else:
        # Fallback: run sync invoke in thread pool
        result = await asyncio.wait_for(
            asyncio.to_thread(
                tech_comparator_agent.invoke,
                {"messages": [{"role": "user", "content": content}]}
            ),
            timeout=agent_timeout,
        )
    return parse_agent_result(result)
```

**SSE Instrumentation in Agent Nodes:**
```python
from app.services.sse_helpers import emit_streaming_event

@task
async def run_tech_comparator(content: str, analysis_id: str) -> dict:
    """Run tech comparator with SSE events."""
    # Emit start event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="tech_comparison",
        status="running",
        agent="tech_comparator",
    )
    
    # Run agent (async with timeout to prevent blocking)
    agent_timeout = 60.0  # 60 seconds max
    if hasattr(tech_comparator_agent, "ainvoke"):
        result = await asyncio.wait_for(
            tech_comparator_agent.ainvoke({"messages": [content]}),
            timeout=agent_timeout,
        )
    else:
        result = await asyncio.wait_for(
            asyncio.to_thread(tech_comparator_agent.invoke, {"messages": [content]}),
            timeout=agent_timeout,
        )
    
    # Emit complete event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="tech_comparison",
        status="complete",
        agent="tech_comparator",
    )
    
    return result
```

#### Tech Comparator Agent (LangChain v1.0 create_agent)
```python
# app/workflows/agents/tech_comparator.py
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from app.core.config import settings

# Define tools for tech comparison
@tool
def compare_technologies(primary_tech: str, alternatives: list[str]) -> dict:
    """Compare primary technology with alternatives."""
    # Implementation
    return {"comparison": {...}}

@tool
def find_alternatives(tech_name: str) -> list[str]:
    """Find alternative technologies."""
    # Implementation
    return ["alt1", "alt2"]

# Create agent using LangChain v1.0
model = init_chat_model(settings.LLM_MODEL)

tech_comparator_agent = create_agent(
    model,
    tools=[compare_technologies, find_alternatives],
    system_prompt="""
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
    from langchain.chat_models import init_chat_model
    from langchain.agents import create_agent
    
    model = init_chat_model(settings.LLM_MODEL)
    agent = create_agent(model, tools=[...])

    prompt = TECH_COMPARATOR_PROMPT.format(
        content=state["raw_content"][:4000]
    )

    response = await agent.ainvoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    findings = json.loads(response["messages"][-1].content)

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

### Backend Patterns Cheat Sheet

**1. FastAPI Endpoint Pattern:**
```python
from fastapi import Depends, APIRouter
from app.db.repositories.analysis import get_analysis_repository, IAnalysisRepository

@router.post("/analyze")
async def create_analysis(
    request: AnalyzeRequest,
    repo: IAnalysisRepository = Depends(get_analysis_repository)
) -> AnalyzeResponse:
    analysis = await repo.create(url=request.url)
    return AnalyzeResponse.from_orm(analysis)
```

**2. LangGraph v1.0 Functional API:**
```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

@task
def extract_content(url: str) -> str:
    return content

@entrypoint(checkpointer=checkpointer)
def workflow(url: str) -> dict:
    content = extract_content(url).result()
    return {"content": content}
```

**3. LangChain v1.0 create_agent:**
```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-mini")
agent = create_agent(model, tools=[tool1, tool2])
```

**4. SSE Instrumentation:**
```python
from app.services.sse_helpers import emit_streaming_event

await emit_streaming_event(
    "progress",
    analysis_id=analysis_id,
    stage="extraction",
    status="running",
)
```

**5. Structured Logging:**
```python
import structlog
logger = structlog.get_logger()

logger.info(
    "workflow_stage_complete",
    analysis_id=analysis_id,
    stage="extraction",
    duration_ms=1234
)
```

### Quality Gates Commands

```bash
# Backend quality checks
cd backend
poetry run ruff check . && ruff format .
poetry run mypy app
poetry run pytest tests/ --cov=app --cov-fail-under=80

# Pre-commit (automatic)
git commit  # Runs hooks automatically

# Pre-push (automatic)
git push  # Runs full test suite
```

### Common Commands

```bash
# Start backend
cd backend
poetry run uvicorn app.main:app --reload

# Run migrations
poetry run alembic upgrade head

# Run tests
poetry run pytest tests/ -v

# Check types
poetry run mypy app
```

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
# Verify OpenAI API key is configured in .env file
```

### When Blocked
- **If blocked by frontend (>4 hours):** Write API docs, work on other endpoints
- **If blocked by unclear requirements:** Check `USER_STORIES.md`, ask PM

---

---

## 📊 Next Steps Summary

### Immediate Next Steps (Week 1)

**For Yonatan (Backend):**
1. **Day 1-2:** Setup project structure with Poetry + pyproject.toml
   - Start with [Issue #1](https://github.com/ArieGoldkin/SkillForge/issues/1) - Task 1.1.1
2. **Day 3:** API contract meeting with Arie (define `/api/v1/analyze` schema)
3. **Day 4-5:** Implement database schema + migrations
   - Continue with [Issue #2](https://github.com/ArieGoldkin/SkillForge/issues/2) - Tasks 1.1.2-1.1.3
   - Then [Issue #3](https://github.com/ArieGoldkin/SkillForge/issues/3) - Tasks 1.2.1-1.2.5
4. **Day 6-7:** Implement content extraction (Jina AI)
   - [Issue #4](https://github.com/ArieGoldkin/SkillForge/issues/4) - Tasks 1.4.1-1.4.5
5. **Day 8-10:** Implement embedding service + basic LangGraph workflow
   - [Issue #5](https://github.com/ArieGoldkin/SkillForge/issues/5) - Tasks 1.5.1-1.5.2

**GitHub Milestone:** [Sprint 1: Backend Foundation](https://github.com/ArieGoldkin/SkillForge/milestone/1)

**For Arie (Frontend):**
1. **Day 1-2:** Setup React 19 + Vite project
2. **Day 3:** API contract meeting with Yonatan
3. **Day 4-7:** Create mock API layer + URL input form
4. **Day 8-10:** Build component library + routing

**For Both:**
1. **Day 3:** Integration meeting - Lock API contract
2. **Day 10:** First end-to-end test (frontend → backend connection)

### Sprint 2 Next Steps (Week 3-4)

**For Yonatan:**
1. **Day 1:** Provide SSE event schema to Arie (BLOCKER)
2. **Day 2-5:** Implement LangGraph v1.0 Functional API workflow
3. **Day 6-7:** Implement supervisor pattern with create_agent
4. **Day 8:** Integration test with Arie (SSE connection)
5. **Day 9-10:** Implement first 3 sub-agents

**For Arie:**
1. **Day 1:** Receive SSE schema from Yonatan
2. **Day 2-5:** Build SSE client hook + progress UI
3. **Day 6-7:** Create Analysis view page
4. **Day 8:** Integration test with Yonatan (SSE connection)
5. **Day 9-10:** Refine UI based on real events

**For Both:**
1. **Day 1:** SSE schema handoff (Yonatan → Arie)
2. **Day 8:** Live SSE testing session

---

**Document Maintained By:** Yonatan
**Last Updated:** November 20, 2025
**Review:** Update daily

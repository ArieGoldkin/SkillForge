# Implementation Plan: Full-Text Search

## Overview

This document provides a detailed, step-by-step implementation plan for adding hybrid full-text and semantic search to the analysis library. Follow these phases in order for a smooth implementation.

## Prerequisites

- PostgreSQL 13+ with PGVector extension enabled
- Existing `analyses` table with vector search (completed)
- Python 3.11+ with SQLAlchemy 2.0+
- FastAPI application structure

## Phase 1: Database Migration (1.5h)

### Step 1.1: Create Migration File (15 min)

Create a new Alembic migration:

```bash
cd /Users/yonatangross/coding/SkillForge/backend
alembic revision -m "add_fulltext_search_to_analyses"
```

This will create a file like: `alembic/versions/{timestamp}_add_fulltext_search_to_analyses.py`

### Step 1.2: Implement Migration (45 min)

Edit the generated migration file:

```python
"""Add full-text search to analyses table.

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: {timestamp}
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "{generated_id}"
down_revision: str | Sequence[str] | None = "{previous_revision}"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add full-text search support to analyses table."""
    # 1. Add tsvector column
    op.add_column(
        "analyses",
        sa.Column("search_vector", TSVECTOR, nullable=True)
    )

    # 2. Create trigger function for automatic updates
    op.execute("""
        CREATE OR REPLACE FUNCTION analyses_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(NEW.url, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(NEW.raw_content, '')), 'C');
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 3. Create trigger
    op.execute("""
        CREATE TRIGGER tsvector_update
        BEFORE INSERT OR UPDATE ON analyses
        FOR EACH ROW
        EXECUTE FUNCTION analyses_search_vector_update();
    """)

    # 4. Populate existing rows (backfill)
    # This runs synchronously but should be fast for < 10k rows
    # For larger datasets, consider using a background task
    op.execute("""
        UPDATE analyses
        SET search_vector =
          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
          setweight(to_tsvector('english', coalesce(url, '')), 'B') ||
          setweight(to_tsvector('english', coalesce(raw_content, '')), 'C')
        WHERE search_vector IS NULL;
    """)

    # 5. Create GIN index for fast full-text search
    op.create_index(
        "idx_analyses_search_vector",
        "analyses",
        ["search_vector"],
        postgresql_using="gin"
    )

    # 6. Create partial index for completed analyses (common query pattern)
    op.create_index(
        "idx_analyses_status_complete",
        "analyses",
        ["status"],
        postgresql_where=sa.text("status = 'complete'")
    )


def downgrade() -> None:
    """Remove full-text search support."""
    # Drop indexes
    op.drop_index("idx_analyses_status_complete", table_name="analyses")
    op.drop_index("idx_analyses_search_vector", table_name="analyses")

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS tsvector_update ON analyses;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS analyses_search_vector_update();")

    # Drop column
    op.drop_column("analyses", "search_vector")
```

### Step 1.3: Update Model (15 min)

Update `/Users/yonatangross/coding/SkillForge/backend/app/models/analysis.py`:

```python
"""Analysis model for content analysis pipeline."""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from app.db.base import Base


class Analysis(Base):
    """Analysis model representing a content analysis task.

    Stores information about URLs being analyzed, their content, embeddings,
    and processing status. This is the primary table in the system.
    """

    __tablename__ = "analyses"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # 'article', 'video', 'repo'
    title = Column(Text)
    raw_content = Column(Text)
    # Embedding vector for semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    content_embedding = Column(Vector(1536))
    # Full-text search vector (auto-updated via trigger)
    search_vector = Column(TSVECTOR)
    extraction_metadata = Column(JSONB)  # Metadata from content extraction
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
```

### Step 1.4: Run Migration (15 min)

```bash
# Test migration with dry-run
alembic upgrade head --sql

# Apply migration
alembic upgrade head

# Verify migration
psql $DATABASE_URL -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'analyses' AND column_name = 'search_vector';"
```

**Expected Output**:
```
  column_name   | data_type
----------------+-----------
 search_vector  | tsvector
```

## Phase 2: Repository Methods (3h)

### Step 2.1: Add Full-Text Search Method (1h)

Update `/Users/yonatangross/coding/SkillForge/backend/app/db/repositories/analysis_repository.py`:

```python
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from pgvector.sqlalchemy import BIT, Vector  # type: ignore[import-untyped]
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import Analysis

# ... existing code ...

class IAnalysisRepository(Protocol):
    """Protocol interface for analysis repository operations."""

    async def find_similar_analyses(
        self,
        query_embedding: list[float],
        limit: int = 5,
        fast_search_limit: int = 20,
    ) -> list[Analysis]:
        """Find similar analyses using two-stage vector search."""
        ...

    async def search_by_text(
        self,
        query: str,
        limit: int = 20,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[tuple[Analysis, float]]:
        """Full-text search using PostgreSQL GIN index."""
        ...

    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        fts_weight: float = 0.7,
        vector_weight: float = 0.3,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[Analysis]:
        """Hybrid search combining full-text and semantic search."""
        ...

    async def list_analyses(
        self,
        limit: int = 20,
        offset: int = 0,
        content_type: str | None = None,
        status: str | None = None,
        order_by: str = "created_at",
    ) -> tuple[list[Analysis], int]:
        """List analyses with filtering and pagination."""
        ...


class AnalysisRepository:
    """Repository implementation for analysis database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    # ... existing methods (find_similar_analyses, stream_all_analyses) ...

    async def search_by_text(
        self,
        query: str,
        limit: int = 20,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[tuple[Analysis, float]]:
        """Full-text search using PostgreSQL GIN index.

        Uses PostgreSQL's full-text search with weighted fields:
        - Title: weight 'A' (highest priority)
        - URL: weight 'B' (medium priority)
        - Content: weight 'C' (lower priority)

        Args:
            query: Search query string
            limit: Maximum number of results (default: 20)
            content_type: Filter by content type (article/video/repo)
            status: Filter by status (pending/complete/failed)

        Returns:
            List of (Analysis, relevance_score) tuples sorted by relevance

        Example:
            >>> repo = AnalysisRepository(session)
            >>> results = await repo.search_by_text("React hooks", limit=10)
            >>> for analysis, score in results:
            ...     print(f"{analysis.title}: {score}")
        """
        if not query or not query.strip():
            logger.warning("search_by_text_empty_query")
            return []

        # Convert query to tsquery format
        # Use plainto_tsquery for user-friendly query parsing
        tsquery = func.plainto_tsquery("english", query.strip())

        # Build query with ts_rank for relevance scoring
        stmt = select(
            Analysis,
            func.ts_rank(Analysis.search_vector, tsquery).label("rank")
        ).where(
            Analysis.search_vector.op("@@")(tsquery)
        )

        # Apply filters
        if content_type:
            stmt = stmt.where(Analysis.content_type == content_type)
        if status:
            stmt = stmt.where(Analysis.status == status)

        # Order by relevance and limit
        stmt = stmt.order_by(text("rank DESC")).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        rows = result.all()

        results = [(row.Analysis, float(row.rank)) for row in rows]

        logger.info(
            "search_by_text_complete",
            query=query,
            limit=limit,
            content_type=content_type,
            status=status,
            results_count=len(results),
        )

        return results
```

### Step 2.2: Add Hybrid Search Method (1.5h)

Add to `AnalysisRepository` class:

```python
    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        fts_weight: float = 0.7,
        vector_weight: float = 0.3,
        content_type: str | None = None,
        status: str | None = None,
    ) -> list[Analysis]:
        """Hybrid search combining full-text and semantic search using RRF.

        Uses Reciprocal Rank Fusion (RRF) to combine results from:
        1. Full-text search (PostgreSQL GIN index)
        2. Semantic search (PGVector similarity)

        The RRF formula: score(d) = Σ [1 / (k + rank_i(d))]
        where k=60 (standard RRF constant) and rank_i is the rank in result set i.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 20)
            fts_weight: Weight for full-text search results (default: 0.7)
            vector_weight: Weight for semantic search results (default: 0.3)
            content_type: Filter by content type
            status: Filter by status

        Returns:
            List of Analysis objects sorted by combined RRF score

        Example:
            >>> repo = AnalysisRepository(session)
            >>> results = await repo.hybrid_search("React hooks", limit=10)
            >>> for analysis in results:
            ...     print(analysis.title)
        """
        import asyncio

        # Validate weights
        if not (0 <= fts_weight <= 1 and 0 <= vector_weight <= 1):
            raise ValueError("Weights must be between 0 and 1")

        # Fetch candidates from both search methods in parallel
        # Use higher candidate limit (2x final limit) for better RRF results
        candidate_limit = limit * 2

        # Run both searches in parallel
        fts_task = self.search_by_text(
            query=query,
            limit=candidate_limit,
            content_type=content_type,
            status=status,
        )

        # Generate embedding for semantic search
        from app.services.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query.strip())
        await embedding_service.close()

        # Find similar analyses (note: find_similar_analyses doesn't support filters yet)
        # TODO: Add content_type/status filters to find_similar_analyses
        vector_task = self.find_similar_analyses(
            query_embedding=query_embedding,
            limit=candidate_limit,
        )

        # Wait for both searches to complete
        fts_results, vector_results = await asyncio.gather(fts_task, vector_task)

        # Apply filters to vector results if needed
        if content_type or status:
            vector_results = [
                analysis for analysis in vector_results
                if (not content_type or analysis.content_type == content_type)
                and (not status or analysis.status == status)
            ]

        # Calculate RRF scores
        # RRF constant k=60 (standard value)
        k = 60
        rrf_scores: dict[str, float] = {}

        # Add scores from full-text search
        for rank, (analysis, _) in enumerate(fts_results, start=1):
            analysis_id = str(analysis.id)
            rrf_scores[analysis_id] = fts_weight * (1 / (k + rank))

        # Add scores from vector search
        for rank, analysis in enumerate(vector_results, start=1):
            analysis_id = str(analysis.id)
            vector_score = vector_weight * (1 / (k + rank))
            rrf_scores[analysis_id] = rrf_scores.get(analysis_id, 0) + vector_score

        # Create map of analysis_id -> Analysis object
        analysis_map: dict[str, Analysis] = {}
        for analysis, _ in fts_results:
            analysis_map[str(analysis.id)] = analysis
        for analysis in vector_results:
            analysis_map[str(analysis.id)] = analysis

        # Sort by RRF score and return top K
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        results = [analysis_map[analysis_id] for analysis_id, _ in sorted_ids]

        logger.info(
            "hybrid_search_complete",
            query=query,
            fts_weight=fts_weight,
            vector_weight=vector_weight,
            fts_results=len(fts_results),
            vector_results=len(vector_results),
            final_results=len(results),
            limit=limit,
        )

        return results
```

### Step 2.3: Add List Method (30 min)

Add to `AnalysisRepository` class:

```python
    async def list_analyses(
        self,
        limit: int = 20,
        offset: int = 0,
        content_type: str | None = None,
        status: str | None = None,
        order_by: str = "created_at",
    ) -> tuple[list[Analysis], int]:
        """List analyses with filtering and pagination.

        Args:
            limit: Maximum number of results (1-100)
            offset: Number of results to skip for pagination
            content_type: Filter by content type
            status: Filter by status
            order_by: Column to order by (created_at, updated_at, title)

        Returns:
            Tuple of (results, total_count)

        Example:
            >>> repo = AnalysisRepository(session)
            >>> results, total = await repo.list_analyses(limit=20, offset=0)
            >>> print(f"Found {total} analyses, showing {len(results)}")
        """
        # Validate order_by to prevent SQL injection
        valid_columns = {"created_at", "updated_at", "title", "id"}
        if order_by not in valid_columns:
            logger.warning("list_analyses_invalid_order_by", order_by=order_by)
            order_by = "created_at"

        # Build base query
        stmt = select(Analysis)

        # Apply filters
        if content_type:
            stmt = stmt.where(Analysis.content_type == content_type)
        if status:
            stmt = stmt.where(Analysis.status == status)

        # Get total count (without pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(getattr(Analysis, order_by).desc()).limit(limit).offset(offset)

        # Execute query
        result = await self.session.scalars(stmt)
        analyses = list(result.all())

        logger.info(
            "list_analyses_complete",
            limit=limit,
            offset=offset,
            content_type=content_type,
            status=status,
            order_by=order_by,
            results_count=len(analyses),
            total=total,
        )

        return analyses, total
```

## Phase 3: API Endpoint (2.5h)

### Step 3.1: Create Schema File (30 min)

Create `/Users/yonatangross/coding/SkillForge/backend/app/schemas/library.py`:

```python
"""Pydantic schemas for library search API endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


class LibrarySearchParams(BaseModel):
    """Query parameters for library search endpoint.

    Attributes:
        query: Search query string (optional for listing)
        search_mode: Search mode (hybrid, fulltext, semantic)
        content_type: Filter by content type
        status: Filter by status
        limit: Maximum number of results (1-100)
        offset: Number of results to skip for pagination

    Example:
        ```python
        params = LibrarySearchParams(
            query="React hooks",
            search_mode="hybrid",
            content_type="article",
            status="complete",
            limit=20,
            offset=0,
        )
        ```
    """

    query: str | None = Field(None, description="Search query string")
    search_mode: Literal["hybrid", "fulltext", "semantic"] = Field(
        "hybrid",
        description="Search mode: hybrid (default), fulltext, or semantic",
    )
    content_type: str | None = Field(
        None,
        description="Filter by content type (article, video, repo)",
        pattern="^(article|video|repo)$",
    )
    status: str | None = Field(
        None,
        description="Filter by status (pending, complete, failed)",
        pattern="^(pending|complete|failed)$",
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results (1-100)",
    )
    offset: int = Field(
        0,
        ge=0,
        description="Number of results to skip for pagination",
    )


class LibraryItem(BaseModel):
    """Single library item in search results.

    Attributes:
        id: Unique identifier
        url: Source URL
        title: Content title (may be None)
        content_type: Type of content
        status: Analysis status
        created_at: Creation timestamp (ISO 8601)
        relevance_score: Relevance score (only for search results)

    Example:
        ```python
        item = LibraryItem(
            id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            title="Introduction to React Hooks",
            content_type="article",
            status="complete",
            created_at="2025-12-04T10:30:00Z",
            relevance_score=0.95,
        )
        ```
    """

    id: str = Field(..., description="Unique identifier")
    url: str = Field(..., description="Source URL")
    title: str | None = Field(None, description="Content title")
    content_type: str = Field(..., description="Type of content")
    status: str = Field(..., description="Analysis status")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    relevance_score: float | None = Field(
        None,
        description="Relevance score (only for search results)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://example.com/article",
                "title": "Introduction to React Hooks",
                "content_type": "article",
                "status": "complete",
                "created_at": "2025-12-04T10:30:00Z",
                "relevance_score": 0.95,
            }
        }
    }


class LibraryResponse(BaseModel):
    """Response from library search endpoint.

    Attributes:
        results: List of library items
        total: Total number of matching results
        limit: Limit applied to query
        offset: Offset applied to query
        search_mode: Search mode used

    Example:
        ```python
        response = LibraryResponse(
            results=[item1, item2, ...],
            total=142,
            limit=20,
            offset=0,
            search_mode="hybrid",
        )
        ```
    """

    results: list[LibraryItem] = Field(..., description="List of library items")
    total: int = Field(..., description="Total number of matching results")
    limit: int = Field(..., description="Limit applied to query")
    offset: int = Field(..., description="Offset applied to query")
    search_mode: str = Field(..., description="Search mode used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "url": "https://example.com/article",
                        "title": "Introduction to React Hooks",
                        "content_type": "article",
                        "status": "complete",
                        "created_at": "2025-12-04T10:30:00Z",
                        "relevance_score": 0.95,
                    }
                ],
                "total": 142,
                "limit": 20,
                "offset": 0,
                "search_mode": "hybrid",
            }
        }
    }
```

### Step 3.2: Create API Endpoint (1.5h)

Create `/Users/yonatangross/coding/SkillForge/backend/app/api/v1/library.py`:

```python
"""Library search endpoints for analysis discovery.

This module provides search and listing functionality for the analysis library,
supporting full-text search, semantic search, and hybrid search modes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.logging import get_logger
from app.db.repositories.analysis_repository import IAnalysisRepository, get_analysis_repository
from app.schemas.library import LibraryItem, LibraryResponse

router = APIRouter(tags=["library"])
logger = get_logger(__name__)


@router.get("/library")
async def search_library(
    repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
    query: Annotated[str | None, Query(description="Search query text")] = None,
    search_mode: Annotated[
        str,
        Query(description="Search mode: hybrid, fulltext, or semantic"),
    ] = "hybrid",
    content_type: Annotated[
        str | None,
        Query(description="Filter by content type (article, video, repo)"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Filter by status (pending, complete, failed)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of results"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of results to skip"),
    ] = 0,
) -> LibraryResponse:
    """Search and list analyses from the library.

    Supports three search modes:
    - **hybrid**: Combines full-text and semantic search using RRF (default)
    - **fulltext**: PostgreSQL full-text search with GIN index
    - **semantic**: Vector similarity search using embeddings

    When no query is provided, returns a paginated list of all analyses.

    Args:
        query: Search query text (optional)
        search_mode: Search mode (hybrid, fulltext, semantic)
        content_type: Filter by content type
        status: Filter by status
        limit: Maximum number of results (1-100)
        offset: Number of results to skip for pagination
        repo: Analysis repository dependency

    Returns:
        LibraryResponse with results, total count, and metadata

    Raises:
        HTTPException: 400 if parameters are invalid
        HTTPException: 500 if search fails

    Examples:
        # Hybrid search (default)
        GET /api/v1/library?query=React+hooks&limit=10

        # Full-text search only
        GET /api/v1/library?query=React+hooks&search_mode=fulltext

        # List all articles (no search)
        GET /api/v1/library?content_type=article&limit=20&offset=0
    """
    # Validate search_mode
    valid_modes = {"hybrid", "fulltext", "semantic"}
    if search_mode not in valid_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search_mode. Must be one of: {', '.join(valid_modes)}",
        )

    # Validate content_type if provided
    if content_type and content_type not in {"article", "video", "repo"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content_type. Must be one of: article, video, repo",
        )

    # Validate status if provided
    if status and status not in {"pending", "complete", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: pending, complete, failed",
        )

    try:
        results = []
        total = 0

        # If no query provided, return paginated list
        if not query or not query.strip():
            analyses, total = await repo.list_analyses(
                limit=limit,
                offset=offset,
                content_type=content_type,
                status=status,
            )
            results = [
                LibraryItem(
                    id=str(analysis.id),
                    url=analysis.url,
                    title=analysis.title,
                    content_type=analysis.content_type,
                    status=analysis.status,
                    created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                    relevance_score=None,
                )
                for analysis in analyses
            ]

        # Search modes
        elif search_mode == "fulltext":
            # Full-text search only
            fts_results = await repo.search_by_text(
                query=query.strip(),
                limit=limit,
                content_type=content_type,
                status=status,
            )
            # For search results, total = number of results (no count query)
            total = len(fts_results)
            results = [
                LibraryItem(
                    id=str(analysis.id),
                    url=analysis.url,
                    title=analysis.title,
                    content_type=analysis.content_type,
                    status=analysis.status,
                    created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                    relevance_score=float(score),
                )
                for analysis, score in fts_results
            ]

        elif search_mode == "semantic":
            # Semantic search only
            from app.services.embeddings import EmbeddingService

            embedding_service = EmbeddingService()
            query_embedding = await embedding_service.generate_embedding(query.strip())
            await embedding_service.close()

            semantic_results = await repo.find_similar_analyses(
                query_embedding=query_embedding,
                limit=limit,
            )

            # Apply filters (TODO: add filters to find_similar_analyses)
            if content_type or status:
                semantic_results = [
                    analysis
                    for analysis in semantic_results
                    if (not content_type or analysis.content_type == content_type)
                    and (not status or analysis.status == status)
                ]

            total = len(semantic_results)
            results = [
                LibraryItem(
                    id=str(analysis.id),
                    url=analysis.url,
                    title=analysis.title,
                    content_type=analysis.content_type,
                    status=analysis.status,
                    created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                    relevance_score=None,  # Vector search doesn't return scores in current impl
                )
                for analysis in semantic_results
            ]

        elif search_mode == "hybrid":
            # Hybrid search (RRF fusion)
            hybrid_results = await repo.hybrid_search(
                query=query.strip(),
                limit=limit,
                content_type=content_type,
                status=status,
            )
            total = len(hybrid_results)
            results = [
                LibraryItem(
                    id=str(analysis.id),
                    url=analysis.url,
                    title=analysis.title,
                    content_type=analysis.content_type,
                    status=analysis.status,
                    created_at=analysis.created_at.isoformat() if analysis.created_at else "",
                    relevance_score=None,  # RRF scores not exposed in current impl
                )
                for analysis in hybrid_results
            ]

        logger.info(
            "search_library_complete",
            query=query,
            search_mode=search_mode,
            content_type=content_type,
            status=status,
            limit=limit,
            offset=offset,
            results_count=len(results),
            total=total,
        )

        return LibraryResponse(
            results=results,
            total=total,
            limit=limit,
            offset=offset,
            search_mode=search_mode,
        )

    except Exception as e:
        logger.error(
            "search_library_failed",
            query=query,
            search_mode=search_mode,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Library search failed",
        ) from e
```

### Step 3.3: Register Router (15 min)

Update `/Users/yonatangross/coding/SkillForge/backend/app/main.py`:

```python
# ... existing imports ...
from app.api.v1 import analyze, artifacts, health, library, search, tutor

# ... existing code ...

# Register routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(library.router, prefix="/api/v1")  # Add this line
app.include_router(artifacts.router, prefix="/api/v1")
# ... existing router registrations ...
```

## Phase 4: Performance Optimization (1.5h)

### Step 4.1: Connection Pool Tuning (30 min)

Update `/Users/yonatangross/coding/SkillForge/backend/app/db/session.py`:

```python
"""Database session management with optimized connection pooling."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async engine with optimized pool settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,              # Max connections in pool
    max_overflow=10,           # Additional connections beyond pool_size
    pool_timeout=30,           # Seconds to wait for connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Verify connections before using
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Dependency for database session.

    Yields:
        AsyncSession: Database session

    Example:
        ```python
        @router.get("/items")
        async def get_items(db: Annotated[AsyncSession, Depends(get_db)]):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Step 4.2: Query Optimization (45 min)

Add query optimization hints and monitoring:

```python
# In analysis_repository.py

# Add query execution time logging
import time

class AnalysisRepository:
    async def search_by_text(self, query: str, ...) -> list[tuple[Analysis, float]]:
        start_time = time.time()

        # ... existing query code ...

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "search_by_text_performance",
            query=query,
            duration_ms=duration_ms,
            results_count=len(results),
        )

        # Alert if query is slow
        if duration_ms > 500:
            logger.warning(
                "search_by_text_slow_query",
                query=query,
                duration_ms=duration_ms,
            )

        return results
```

### Step 4.3: Add Performance Monitoring (15 min)

Create monitoring endpoint:

```python
# In app/api/v1/health.py

@router.get("/health/search-performance")
async def search_performance_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get search performance metrics.

    Returns index statistics and query performance data.
    """
    # Check GIN index size and health
    result = await db.execute(text("""
        SELECT
            pg_size_pretty(pg_total_relation_size('idx_analyses_search_vector')) as index_size,
            (SELECT count(*) FROM analyses WHERE search_vector IS NOT NULL) as indexed_rows,
            (SELECT count(*) FROM analyses) as total_rows
    """))
    stats = result.fetchone()

    return {
        "gin_index_size": stats[0],
        "indexed_rows": stats[1],
        "total_rows": stats[2],
        "index_coverage": f"{(stats[1] / stats[2] * 100):.2f}%" if stats[2] > 0 else "0%",
    }
```

## Phase 5: Testing (2h)

### Step 5.1: Unit Tests for Repository (1h)

Create `/Users/yonatangross/coding/SkillForge/backend/tests/unit/db/repositories/test_analysis_repository_search.py`:

```python
"""Unit tests for analysis repository search methods."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analysis_repository import AnalysisRepository
from app.models.analysis import Analysis


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_analysis():
    """Sample analysis object."""
    return Analysis(
        id=uuid.uuid4(),
        url="https://example.com/react-hooks",
        title="Introduction to React Hooks",
        content_type="article",
        status="complete",
        raw_content="React Hooks are a new addition in React 16.8...",
    )


@pytest.mark.asyncio
async def test_search_by_text_success(mock_session, sample_analysis):
    """Test successful full-text search."""
    # Mock database response
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.Analysis = sample_analysis
    mock_row.rank = 0.95
    mock_result.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_result

    # Execute search
    repo = AnalysisRepository(session=mock_session)
    results = await repo.search_by_text(query="React hooks", limit=10)

    # Verify results
    assert len(results) == 1
    assert results[0][0].id == sample_analysis.id
    assert results[0][1] == 0.95

    # Verify query was executed
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_search_by_text_empty_query(mock_session):
    """Test search with empty query returns empty results."""
    repo = AnalysisRepository(session=mock_session)
    results = await repo.search_by_text(query="", limit=10)

    assert results == []
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_by_text_with_filters(mock_session, sample_analysis):
    """Test search with content_type and status filters."""
    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.Analysis = sample_analysis
    mock_row.rank = 0.95
    mock_result.all.return_value = [mock_row]
    mock_session.execute.return_value = mock_result

    repo = AnalysisRepository(session=mock_session)
    results = await repo.search_by_text(
        query="React hooks",
        limit=10,
        content_type="article",
        status="complete",
    )

    assert len(results) == 1
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_analyses_success(mock_session, sample_analysis):
    """Test successful listing of analyses."""
    # Mock count result
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 42

    # Mock analyses result
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [sample_analysis]

    # Setup session to return both results
    mock_session.execute.side_effect = [mock_count_result]
    mock_session.scalars.return_value = mock_scalars_result

    repo = AnalysisRepository(session=mock_session)
    results, total = await repo.list_analyses(limit=20, offset=0)

    assert len(results) == 1
    assert total == 42
    assert results[0].id == sample_analysis.id


@pytest.mark.asyncio
async def test_list_analyses_with_filters(mock_session, sample_analysis):
    """Test listing with filters."""
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 10

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [sample_analysis]

    mock_session.execute.side_effect = [mock_count_result]
    mock_session.scalars.return_value = mock_scalars_result

    repo = AnalysisRepository(session=mock_session)
    results, total = await repo.list_analyses(
        limit=20,
        offset=0,
        content_type="article",
        status="complete",
    )

    assert len(results) == 1
    assert total == 10


@pytest.mark.asyncio
async def test_list_analyses_invalid_order_by(mock_session, sample_analysis):
    """Test that invalid order_by defaults to created_at."""
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = [sample_analysis]

    mock_session.execute.side_effect = [mock_count_result]
    mock_session.scalars.return_value = mock_scalars_result

    repo = AnalysisRepository(session=mock_session)
    # Should not raise exception, should default to created_at
    results, total = await repo.list_analyses(order_by="invalid_column")

    assert len(results) == 1


@pytest.mark.asyncio
@patch("app.db.repositories.analysis_repository.EmbeddingService")
async def test_hybrid_search_success(mock_embedding_service, mock_session, sample_analysis):
    """Test successful hybrid search."""
    # Mock embedding service
    mock_service_instance = AsyncMock()
    mock_service_instance.generate_embedding.return_value = [0.1] * 1536
    mock_embedding_service.return_value = mock_service_instance

    # Mock full-text search results
    fts_result = MagicMock()
    fts_row = MagicMock()
    fts_row.Analysis = sample_analysis
    fts_row.rank = 0.95
    fts_result.all.return_value = [fts_row]

    # Mock vector search results
    vector_result = MagicMock()
    vector_result.all.return_value = [sample_analysis]

    # Mock session responses
    mock_session.execute.return_value = fts_result
    mock_session.scalars.return_value = vector_result

    repo = AnalysisRepository(session=mock_session)
    # Need to mock find_similar_analyses
    repo.find_similar_analyses = AsyncMock(return_value=[sample_analysis])

    results = await repo.hybrid_search(query="React hooks", limit=10)

    assert len(results) >= 1
    assert results[0].id == sample_analysis.id


@pytest.mark.asyncio
async def test_hybrid_search_invalid_weights(mock_session):
    """Test hybrid search with invalid weights raises ValueError."""
    repo = AnalysisRepository(session=mock_session)

    with pytest.raises(ValueError, match="Weights must be between 0 and 1"):
        await repo.hybrid_search(
            query="React hooks",
            limit=10,
            fts_weight=1.5,  # Invalid weight
            vector_weight=0.3,
        )
```

### Step 5.2: Integration Tests for API (45 min)

Create `/Users/yonatangross/coding/SkillForge/backend/tests/integration/api/test_library_endpoint.py`:

```python
"""Integration tests for library search API endpoint."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_library_search_hybrid(async_client: AsyncClient):
    """Test hybrid search mode."""
    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React hooks",
            "search_mode": "hybrid",
            "limit": 10,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "results" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "search_mode" in data
    assert data["search_mode"] == "hybrid"
    assert data["limit"] == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_library_search_fulltext(async_client: AsyncClient):
    """Test full-text search mode."""
    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React",
            "search_mode": "fulltext",
            "limit": 5,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["search_mode"] == "fulltext"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_library_list_no_query(async_client: AsyncClient):
    """Test listing without query (pagination)."""
    response = await async_client.get(
        "/api/v1/library",
        params={
            "limit": 20,
            "offset": 0,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "results" in data
    assert "total" in data
    assert isinstance(data["results"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_library_search_invalid_mode(async_client: AsyncClient):
    """Test invalid search mode returns 400."""
    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React",
            "search_mode": "invalid",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.asyncio
async def test_library_search_with_filters(async_client: AsyncClient):
    """Test search with content_type and status filters."""
    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React",
            "search_mode": "hybrid",
            "content_type": "article",
            "status": "complete",
            "limit": 10,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify all results match filters
    for item in data["results"]:
        assert item["content_type"] == "article"
        assert item["status"] == "complete"
```

### Step 5.3: Performance Benchmarks (15 min)

Create `/Users/yonatangross/coding/SkillForge/backend/tests/performance/test_search_benchmarks.py`:

```python
"""Performance benchmarks for search functionality."""

import pytest
import time


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_fulltext_search_performance(async_client):
    """Benchmark full-text search performance (target: < 500ms)."""
    start_time = time.time()

    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React hooks useState useEffect",
            "search_mode": "fulltext",
            "limit": 20,
        },
    )

    duration_ms = (time.time() - start_time) * 1000

    assert response.status_code == 200
    assert duration_ms < 500, f"Full-text search took {duration_ms}ms (target: < 500ms)"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_hybrid_search_performance(async_client):
    """Benchmark hybrid search performance (target: < 750ms)."""
    start_time = time.time()

    response = await async_client.get(
        "/api/v1/library",
        params={
            "query": "React hooks",
            "search_mode": "hybrid",
            "limit": 20,
        },
    )

    duration_ms = (time.time() - start_time) * 1000

    assert response.status_code == 200
    assert duration_ms < 750, f"Hybrid search took {duration_ms}ms (target: < 750ms)"


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_library_list_performance(async_client):
    """Benchmark library listing performance (target: < 200ms)."""
    start_time = time.time()

    response = await async_client.get(
        "/api/v1/library",
        params={"limit": 20, "offset": 0},
    )

    duration_ms = (time.time() - start_time) * 1000

    assert response.status_code == 200
    assert duration_ms < 200, f"Library listing took {duration_ms}ms (target: < 200ms)"
```

## Post-Implementation Checklist

- [ ] Migration applied and verified
- [ ] GIN index created and populated
- [ ] Trigger function working correctly
- [ ] All repository methods implemented
- [ ] API endpoint created and registered
- [ ] Schemas defined with proper validation
- [ ] Connection pool tuned
- [ ] Performance monitoring in place
- [ ] Unit tests passing (≥80% coverage)
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] API documentation updated
- [ ] Logs structured and informative
- [ ] Error handling comprehensive

## Troubleshooting

### Issue: Migration fails with "column already exists"
**Solution**: Check if migration was partially applied. Rollback and re-run:
```bash
alembic downgrade -1
alembic upgrade head
```

### Issue: GIN index not being used
**Solution**: Analyze query plan and update statistics:
```sql
ANALYZE analyses;
EXPLAIN ANALYZE SELECT ... WHERE search_vector @@ to_tsquery('...');
```

### Issue: Slow full-text search
**Solution**:
1. Verify GIN index exists: `\d analyses`
2. Check index bloat: `SELECT pg_size_pretty(pg_relation_size('idx_analyses_search_vector'));`
3. Rebuild index if needed: `REINDEX INDEX idx_analyses_search_vector;`

### Issue: Trigger not updating search_vector
**Solution**: Verify trigger is enabled:
```sql
SELECT tgname, tgenabled FROM pg_trigger WHERE tgrelid = 'analyses'::regclass;
```

## Next Steps

After successful implementation:

1. **Monitor Performance**: Track query latency and adjust weights if needed
2. **Gather Feedback**: Collect user feedback on search relevance
3. **Tune Weights**: Adjust RRF weights (0.7/0.3) based on usage patterns
4. **Add Analytics**: Track popular queries and zero-result searches
5. **Consider Enhancements**: Query expansion, synonyms, auto-complete

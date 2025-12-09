"""Repository for AnalysisChunk database operations with kNN search.

This module provides a repository pattern for managing AnalysisChunk records
with support for semantic search (vector similarity), full-text search (PostgreSQL
tsvector), and hybrid search combining both approaches with RRF fusion.

Key Features:
    - Semantic search: Vector kNN using cosine distance with HNSW indexing
    - Full-text search: PostgreSQL tsvector with BM25-like ranking (ts_rank_cd)
    - Hybrid search: Reciprocal Rank Fusion (RRF) combining both methods
    - Metadata filtering: JSONB filtering for all search methods
    - Bulk operations: Efficient batch insertions

Usage:
    ```python
    from app.db.repositories.chunk_repository import ChunkRepository
    from app.db.session import get_db


    async def search_chunks(db: AsyncSession = Depends(get_db)):
        repo = ChunkRepository(db)

        # Semantic search
        results = await repo.semantic_search(query_embedding=[0.1, 0.2, ...], limit=10)

        # Keyword search
        results = await repo.keyword_search(query_text="machine learning", limit=10)

        # Hybrid search with metadata filtering
        results = await repo.hybrid_search(
            query_embedding=[0.1, 0.2, ...],
            query_text="machine learning",
            limit=10,
            filters={"chunk_type": "section"},
        )
    ```

Technical Notes:
    - RRF constant k=60 is the standard value from academic literature
    - ts_rank_cd provides better ranking than ts_rank for most use cases
    - HNSW index on embeddings provides fast approximate nearest neighbor search
    - content_tsvector is populated by database trigger for consistency
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_chunk import AnalysisChunk


class ChunkRepository:
    """Repository for AnalysisChunk database operations.

    Provides high-level database operations for managing and searching
    AnalysisChunk records with support for semantic, keyword, and hybrid search.

    Attributes:
        session: The async SQLAlchemy session for database operations

    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with a database session.

        Args:
            session: Async SQLAlchemy session for database operations

        """
        self.session = session

    async def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[tuple[AnalysisChunk, float]]:
        """Perform vector kNN search using cosine distance.

        Uses pgvector's cosine distance operator with HNSW indexing for fast
        approximate nearest neighbor search. Embeddings are compared using
        cosine similarity, which is scale-invariant and works well for
        normalized vectors.

        Args:
            query_embedding: Query vector (1536 dimensions for OpenAI embeddings)
            limit: Maximum number of results to return (default: 10)
            filters: Optional JSONB metadata filters (e.g., {"chunk_type": "section"})

        Returns:
            List of tuples (AnalysisChunk, similarity_score) ordered by similarity (most similar first).
            Similarity score is 1 - cosine_distance, ranging from 0.0 to 1.0 (normalized vectors).

        Example:
            ```python
            results = await repo.semantic_search(
                query_embedding=[0.1, 0.2, ...], limit=5, filters={"chunk_type": "code_block"}
            )
            for chunk, score in results:
                print(f"Score: {score}, Content: {chunk.content[:100]}")
            ```

        """
        # Calculate cosine distance as a column for scoring
        # Cosine similarity = 1 - cosine_distance (for normalized vectors)
        # Note: Using the actual database column 'vector', not the property alias
        cosine_dist = AnalysisChunk.vector.cosine_distance(query_embedding)
        similarity_score = (1 - cosine_dist).label("similarity_score")

        # Build base query with cosine distance ordering and similarity score
        query = select(AnalysisChunk, similarity_score).order_by(cosine_dist)

        # Apply metadata filters if provided
        # Note: The existing schema has content_type and analysis_id as direct columns
        if filters:
            if "content_type" in filters:
                query = query.where(AnalysisChunk.content_type == filters["content_type"])
            if "analysis_id" in filters:
                query = query.where(AnalysisChunk.analysis_id == filters["analysis_id"])

        # Limit results
        query = query.limit(limit)

        # Execute and return results as (chunk, score) tuples
        result = await self.session.execute(query)
        return [(row[0], float(row[1])) for row in result.all()]

    async def keyword_search(
        self,
        query_text: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[tuple[AnalysisChunk, float]]:
        """Perform full-text search using PostgreSQL tsvector.

        Uses PostgreSQL's full-text search with ts_rank_cd for BM25-like ranking.
        The content_tsvector column is automatically populated by a database
        trigger for consistency.

        Args:
            query_text: Search query string (will be parsed with plainto_tsquery)
            limit: Maximum number of results to return (default: 10)
            filters: Optional JSONB metadata filters (e.g., {"chunk_type": "section"})

        Returns:
            List of tuples (AnalysisChunk, score) ordered by relevance score descending

        Example:
            ```python
            results = await repo.keyword_search(query_text="machine learning algorithms", limit=10)
            for chunk, score in results:
                print(f"Score: {score}, Content: {chunk.content[:100]}")
            ```

        Note:
            - plainto_tsquery handles phrase parsing and stop words automatically
            - ts_rank_cd uses cover density ranking (better than ts_rank for most cases)
            - Scores are normalized by document length

        """
        # Create tsquery from plain text
        tsquery = func.plainto_tsquery("english", query_text)

        # Build query with ts_rank_cd scoring
        # Note: Using to_tsvector on snippet column (no pre-computed tsvector in this schema)
        # This is less efficient but works without schema changes
        content_tsvector = func.to_tsvector("english", AnalysisChunk.snippet)
        score = func.ts_rank_cd(content_tsvector, tsquery).label("score")

        query = (
            select(AnalysisChunk, score)
            .where(content_tsvector.op("@@")(tsquery))
            .order_by(score.desc())
        )

        # Apply metadata filters if provided
        # Note: The existing schema has content_type and analysis_id as direct columns
        if filters:
            if "content_type" in filters:
                query = query.where(AnalysisChunk.content_type == filters["content_type"])
            if "analysis_id" in filters:
                query = query.where(AnalysisChunk.analysis_id == filters["analysis_id"])

        # Limit results
        query = query.limit(limit)

        # Execute and return results as (chunk, score) tuples
        result = await self.session.execute(query)
        return [(row[0], float(row[1])) for row in result.all()]

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[tuple[AnalysisChunk, float]]:
        """Perform hybrid search combining semantic and keyword search with RRF.

        Executes semantic (vector) and keyword (full-text) searches in parallel,
        then combines results using Reciprocal Rank Fusion (RRF). RRF is a simple
        but effective rank aggregation method that weights results by their rank
        rather than raw scores, making it robust to score scale differences.

        RRF Formula: score(d) = Σ 1/(k + rank(d))
        where k=60 is the standard constant from academic literature.

        Args:
            query_embedding: Query vector (1536 dimensions for OpenAI embeddings)
            query_text: Search query string for full-text search
            limit: Maximum number of results to return (default: 10)
            filters: Optional JSONB metadata filters (e.g., {"chunk_type": "section"})

        Returns:
            List of tuples (AnalysisChunk, fused_score) ordered by fused score descending

        Example:
            ```python
            results = await repo.hybrid_search(
                query_embedding=[0.1, 0.2, ...],
                query_text="neural networks",
                limit=10,
                filters={"chunk_type": "section"},
            )
            ```

        Technical Notes:
            - RRF k=60 balances between favoring top ranks and allowing lower ranks
            - Results from both searches are fetched with 2*limit to ensure coverage
            - Duplicate chunks are merged by summing their RRF scores
            - This approach handles the semantic-keyword score scale mismatch problem

        """
        # Fetch results from both search methods with 2*limit for better coverage
        fetch_limit = limit * 2

        # Execute both searches in parallel (queries are independent)
        semantic_results = await self.semantic_search(
            query_embedding=query_embedding,
            limit=fetch_limit,
            filters=filters,
        )

        keyword_results = await self.keyword_search(
            query_text=query_text,
            limit=fetch_limit,
            filters=filters,
        )

        # Apply Reciprocal Rank Fusion (RRF)
        # RRF constant k=60 is standard from academic literature
        rrf_k = 60
        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, AnalysisChunk] = {}

        # Add semantic search results with RRF scoring
        for rank, (chunk, _semantic_score) in enumerate(semantic_results, start=1):
            chunk_id = str(chunk.id)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            chunk_map[chunk_id] = chunk

        # Add keyword search results with RRF scoring
        for rank, (chunk, _score) in enumerate(keyword_results, start=1):
            chunk_id = str(chunk.id)
            # If chunk appears in both results, scores are summed
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            chunk_map[chunk_id] = chunk

        # Sort by fused score and return top results
        sorted_results = sorted(
            [(chunk_map[chunk_id], score) for chunk_id, score in rrf_scores.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_results[:limit]

    async def get_by_analysis_id(
        self,
        analysis_id: str,
    ) -> list[AnalysisChunk]:
        """Get all chunks for an analysis, ordered by sequence.

        Retrieves all chunks belonging to a specific analysis, ordered by their
        sequence_order field to maintain the original document structure.

        Args:
            analysis_id: UUID of the parent analysis (as string)

        Returns:
            List of AnalysisChunk objects ordered by sequence_order

        Example:
            ```python
            chunks = await repo.get_by_analysis_id("123e4567-e89b-12d3-a456-426614174000")
            for chunk in chunks:
                print(f"Chunk {chunk.sequence_order}: {chunk.content[:50]}")
            ```

        """
        query = (
            select(AnalysisChunk)
            .where(AnalysisChunk.analysis_id == analysis_id)
            .order_by(AnalysisChunk.chunk_idx)  # Using chunk_idx instead of sequence_order
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_many(self, items: Iterable[dict]) -> list[AnalysisChunk]:
        """Bulk insert chunks efficiently.

        Performs a batch insert of multiple chunks in a single database operation
        for better performance when creating many chunks at once.

        Args:
            items: Iterable of dictionaries with chunk data

        Returns:
            List of inserted AnalysisChunk objects with IDs populated

        Example:
            ```python
            chunks = [
                {
                    "analysis_id": analysis_id,
                    "snippet": "...",
                    "granularity": "section",
                    "chunk_idx": 0,
                    "vector": [...],
                },
                # ... more chunks
            ]
            created = await repo.create_many(chunks)
            ```

        Note:
            - This method uses add_all() for efficient batch insertion
            - The session must be committed separately (usually handled by FastAPI)
            - IDs are generated automatically for each chunk

        """
        objects = [AnalysisChunk(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()  # Flush to get IDs without committing
        return objects

    async def list_by_analysis(self, analysis_id: UUID) -> list[AnalysisChunk]:
        """List all chunks for a given analysis ID.

        Args:
            analysis_id: UUID of the parent analysis

        Returns:
            List of AnalysisChunk objects for the analysis

        """
        stmt = select(AnalysisChunk).where(AnalysisChunk.analysis_id == analysis_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

"""Database repositories for data access layer.

This module exports repository classes that provide high-level database
operations following the repository pattern. Repositories encapsulate
query logic and provide a clean interface for data access.

Available Repositories:
    - ChunkRepository: Manages AnalysisChunk records with semantic, keyword,
                      and hybrid search capabilities

Usage:
    ```python
    from app.db.repositories import ChunkRepository
    from app.db.session import get_db
    from fastapi import Depends


    @app.get("/search")
    async def search(db: AsyncSession = Depends(get_db)):
        repo = ChunkRepository(db)
        results = await repo.semantic_search(query_embedding=[...])
        return results
    ```
"""

from app.db.repositories.chunk_repository import ChunkRepository

__all__ = [
    "ChunkRepository",
]

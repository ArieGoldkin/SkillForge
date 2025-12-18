import pytest
from sqlalchemy import text

from app.db.base import Base
from app.db.models.analysis_chunk import AnalysisChunk
from app.db.repositories.chunk_repository import ChunkRepository
from app.db.session import AsyncSessionLocal, engine
from app.shared.services.search.coarse_to_fine import retrieve_coarse_to_fine


@pytest.mark.asyncio
async def test_coarse_to_fine_db_backed():
    analysis_id = "00000000-0000-0000-0000-000000000001"

    async with AsyncSessionLocal() as session:
        # Ensure tables exist for test database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Clean existing fixtures
        await session.execute(text("DELETE FROM analysis_chunks"))
        await session.execute(text("DELETE FROM analyses"))
        await session.commit()

        # Seed analysis row for FK
        await session.execute(
            text(
                "INSERT INTO analyses (id, url, content_type, status, created_at, updated_at) "
                "VALUES (:id, 'http://example.com', 'article', 'pending', now(), now())"
            ),
            {"id": analysis_id},
        )
        await session.commit()

        coarse = AnalysisChunk(
            analysis_id=analysis_id,
            granularity="coarse",
            path=["root"],
            section_title="Root",
            chunk_idx=0,
            chunk_total=1,
            content_type=None,
            language=None,
            hash="h1",
            model="m",
            model_version="v",
            snippet="coarse",
            vector=[0.1] * 1536,
        )
        fine = AnalysisChunk(
            analysis_id=analysis_id,
            granularity="fine",
            path=["root"],
            section_title="Root",
            chunk_idx=0,
            chunk_total=1,
            content_type=None,
            language=None,
            hash="h2",
            model="m",
            model_version="v",
            snippet="fine",
            vector=[0.1] * 1536,
        )
        session.add_all([coarse, fine])
        await session.commit()

        repo = ChunkRepository(session)
        results = await retrieve_coarse_to_fine(repo, top_k_coarse=1, top_k_fine=1)

        assert len(results) == 1
        hit = results[0]
        assert hit["granularity"] == "fine"
        assert hit["path"] == ["root"]
        assert hit["snippet"] == "fine"

    await engine.dispose()

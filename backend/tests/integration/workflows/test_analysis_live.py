"""Live-ish integration test using real embeddings and extraction.

Requires:
- RUN_LIVE_RAG=1
- DATABASE_URL
- OPENAI_API_KEY
- JINA_API_KEY

Notes:
- To keep cost low, we patch supervisor/agent fan-out and artifact generation.
- Embeddings and extraction are real; agents and artifact LLM are skipped.

"""

import asyncio
import os
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models.analysis import Analysis
from app.db.models.analysis_chunk import AnalysisChunk
from app.db.session import AsyncSessionLocal, engine
from app.domains.analysis.workflows.analysis import analysis_workflow


@pytest.fixture
def requires_live_env():
    settings = get_settings()
    if not os.environ.get("RUN_LIVE_RAG"):
        pytest.skip("RUN_LIVE_RAG not set")
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    if not os.environ.get("JINA_API_KEY"):
        pytest.skip("JINA_API_KEY not set")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external_live
@pytest.mark.timeout(180)
async def test_analysis_workflow_live_embeddings_and_extraction(requires_live_env) -> None:
    test_url = "https://react.dev"
    analysis_id = str(uuid4())

    # Pre-create analysis row
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Patch supervisor to avoid agent LLM calls; patch artifact generation to avoid LLM cost
    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Live test: skipping agents for cost control",
            "confidence": 0.1,
        }
    }

    async def _fake_generate_artifact(_state):
        return {"artifact_id": analysis_id}

    try:
        with (
            patch(
                "app.workflows.graph_builder.supervisor_route",
                new_callable=AsyncMock,
                return_value=mock_supervisor_result,
            ),
            patch(
                "app.workflows.tasks.generate_artifact.generate_artifact",
                new=_fake_generate_artifact,
            ),
        ):
            workflow_config = {
                "configurable": {"thread_id": analysis_id},
                "run_name": f"test_live_analysis_{analysis_id}",
                "tags": ["test", "integration", "workflow", "live"],
                "metadata": {
                    "analysis_id": analysis_id,
                    "url": test_url,
                    "test_type": "live_embeddings_extraction",
                },
            }
            result = await asyncio.wait_for(
                analysis_workflow.ainvoke(
                    {
                        "url": test_url,
                        "analysis_id": analysis_id,
                        "skill_level": "intermediate",
                    },
                    config=workflow_config,
                ),
                timeout=150.0,
            )

        # Basic assertions on returned state
        assert result["analysis_id"] == analysis_id
        assert result["url"] == test_url
        assert "raw_content" in result
        assert result.get("content_embedding") is not None

        # Verify chunks persisted
        async with AsyncSessionLocal() as session:
            analysis_row = await session.get(Analysis, UUID(analysis_id))
            assert analysis_row is not None

            chunks = await session.execute(
                select(AnalysisChunk).where(AnalysisChunk.analysis_id == UUID(analysis_id))
            )
            chunk_count = len(chunks.scalars().all())
            assert chunk_count > 0
    finally:
        await engine.dispose()

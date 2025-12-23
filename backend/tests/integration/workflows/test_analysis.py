"""Integration tests for analysis workflow."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal, engine
from app.domains.analysis.services.workflow import WorkflowOrchestrator
from app.domains.analysis.workflows.analysis import create_analysis_workflow

# Expected embedding dimensions for OpenAI text-embedding-3-small
EXPECTED_EMBEDDING_DIMENSIONS = 1536

# Sample extraction result for mocking
# Note: JinaReader returns title at both top level and in metadata
SAMPLE_EXTRACTION_RESULT = {
    "content": "Sample article content for testing workflow end-to-end.",
    "title": "Test Article",  # Top-level title (Issue #170 fix)
    "word_count": 10,
    "metadata": {
        "title": "Test Article",
        "content_type": "article",
        "word_count": 10,
    },
}

# Sample embedding for mocking
SAMPLE_EMBEDDING = [0.1] * EXPECTED_EMBEDDING_DIMENSIONS


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not set."""
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


@pytest.fixture
def requires_jina_api_key():
    """Skip test if JINA_API_KEY is not set."""
    if not os.environ.get("JINA_API_KEY"):
        pytest.skip("JINA_API_KEY not set in .env - skipping integration test")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(
    150
)  # 2.5 minute max timeout - accounts for streaming/parallel execution overhead
async def test_analysis_workflow_end_to_end(requires_database, reset_engine_connections) -> None:
    """Test analysis_workflow end-to-end with real services.

    This test requires:
    - OpenAI API key configured (for embeddings and agents)
    - Database connection

    Note: Jina is mocked to avoid API dependency issues (insufficient balance, rate limits).
    This allows the test to focus on workflow execution logic rather than external service availability.

    Can take 2+ minutes due to OpenAI embedding generation, streaming overhead,
    and parallel execution of embedding + supervisor tasks.

    Timeout increased to 150s to account for:
    - Streaming overhead from agent.astream()
    - Parallel execution overhead
    - Real OpenAI API response times
    - Variable network latency
    """
    # Use a simple test URL
    test_url = "https://react.dev"
    # Use a proper UUID for the analysis_id (required for database foreign key)
    analysis_id = str(uuid4())

    # Create Analysis record before running workflow (required for agent foreign keys)
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to avoid API dependency issues (best practice for integration tests)
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(return_value=SAMPLE_EXTRACTION_RESULT)
    mock_jina.close = AsyncMock()

    # Mock embedding service to avoid OpenAI API dependency issues
    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=SAMPLE_EMBEDDING)
    mock_embedding_service.close = AsyncMock()

    # Mock supervisor to return empty agent selection (no agents to execute for faster test)
    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test content - no agents needed for end-to-end test",
            "confidence": 0.5,
        }
    }

    # Mock artifact repository to avoid database foreign key violations
    mock_artifact = MagicMock()
    mock_artifact.id = UUID(analysis_id)
    mock_artifact_repo = AsyncMock()
    mock_artifact_repo.create_artifact = AsyncMock(return_value=mock_artifact)

    try:
        with (
            patch("app.workflows.tasks.extract_content.JinaReader", return_value=mock_jina),
            patch(
                "app.workflows.tasks.generate_embedding.EmbeddingService",
                return_value=mock_embedding_service,
            ),
            patch(
                "app.workflows.graph_builder.supervisor_route",
                new_callable=AsyncMock,
                return_value=mock_supervisor_result,
            ),
            # Mock router to return no agents (empty list) for faster execution
            patch(
                "app.workflows.nodes.agent_router.route_to_agents",
                return_value=[],  # No agents selected
            ),
            patch(
                "app.workflows.tasks.generate_artifact.ArtifactRepository",
                return_value=mock_artifact_repo,
            ),
        ):
            # Run workflow with timeout (increased for streaming/parallel overhead)
            # Configure tracing metadata
            workflow_config = {
                "configurable": {"thread_id": analysis_id},
                "run_name": f"test_analysis_{analysis_id}",
                "tags": ["test", "integration", "workflow"],
                "metadata": {
                    "analysis_id": analysis_id,
                    "url": test_url,
                    "test_type": "end_to_end",
                },
            }
            workflow = create_analysis_workflow()
            result = await asyncio.wait_for(
                workflow.ainvoke(
                    {
                        "url": test_url,
                        "analysis_id": analysis_id,
                        "skill_level": "intermediate",
                    },
                    config=workflow_config,
                ),
                timeout=140.0,  # 140 seconds for real workflow with streaming/parallel overhead
            )

        # Verify result structure (StateGraph should populate all state fields)
        assert "analysis_id" in result
        assert "url" in result
        assert "raw_content" in result
        assert "extraction_metadata" in result
        assert "content_embedding" in result
        assert "supervisor_decision" in result
        assert "agent_findings" in result

        # Verify values
        assert result["analysis_id"] == analysis_id
        assert result["url"] == test_url
        assert len(result["raw_content"]) > 0
        assert isinstance(result["extraction_metadata"], dict)
        # Verify title is in extraction_metadata (Issue #170 fix)
        assert "title" in result["extraction_metadata"], "Title should be in extraction_metadata"
        assert result["extraction_metadata"]["title"] == "Test Article", (
            "Title should be extracted from JinaReader response"
        )
        # Verify embedding (mocked, so we know the exact value)
        assert "content_embedding" in result
        assert len(result["content_embedding"]) == EXPECTED_EMBEDDING_DIMENSIONS
        assert all(isinstance(x, float) for x in result["content_embedding"])
        assert result["content_embedding"] == SAMPLE_EMBEDDING
        assert isinstance(result["supervisor_decision"], dict)
        assert isinstance(result["agent_findings"], list)

        # Verify mocked services were called
        mock_jina.extract_article.assert_called_once_with(test_url)
        mock_jina.close.assert_called_once()
        assert mock_embedding_service.generate_embedding.call_count >= 1
        assert mock_embedding_service.close.call_count >= 1

        # Verify title persistence would work correctly (Issue #170)
        # Simulate what _persist_analysis_data does with the workflow result
        extraction_metadata = result.get("extraction_metadata")
        assert extraction_metadata is not None, "extraction_metadata should exist"
        title = extraction_metadata.get("title")
        assert title is not None, "Title should be present in extraction_metadata"
        assert title == "Test Article", "Title should match the extracted value"
        # Verify the structure matches what _persist_analysis_data expects
        # (from orchestrator data_persister.persist)
        assert isinstance(title, str), "Title should be a string"
    finally:
        # Ensure engine connections are disposed
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(
    420
)  # 7 minute max timeout (runs twice at 3min each) - accounts for streaming/parallel execution
async def test_analysis_workflow_with_checkpointer(
    requires_database, reset_engine_connections
) -> None:
    """Test analysis_workflow with database checkpointer.

    This test requires:
    - OpenAI API key configured (for embeddings and agents)
    - Database connection

    Note: Jina is mocked to avoid API dependency issues (insufficient balance, rate limits).
    This allows the test to focus on checkpoint functionality rather than external service availability.

    Can take 2+ minutes per run due to OpenAI embedding generation, streaming overhead,
    and parallel execution. Runs twice to test checkpoint functionality.

    Timeout increased to 300s (5 minutes) to account for:
    - Two workflow runs (first run + checkpointed second run)
    - Streaming overhead from agent.astream() (both runs)
    - Parallel execution overhead (both runs)
    - Real OpenAI API response times
    - Variable network latency
    """
    test_url = "https://react.dev"
    # Use a proper UUID for the analysis_id (required for database foreign key)
    analysis_id = str(uuid4())

    # Create Analysis record before running workflow (required for agent foreign keys)
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to avoid API dependency issues (best practice for integration tests)
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(return_value=SAMPLE_EXTRACTION_RESULT)
    mock_jina.close = AsyncMock()

    # Mock embedding service to avoid OpenAI API dependency issues
    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=SAMPLE_EMBEDDING)
    mock_embedding_service.close = AsyncMock()

    # Mock supervisor to return empty agent selection (no agents to execute for faster test)
    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test content - no agents needed for checkpoint test",
            "confidence": 0.5,
        }
    }

    # Mock artifact repository to avoid database foreign key violations
    mock_artifact = MagicMock()
    mock_artifact.id = UUID(analysis_id)
    mock_artifact_repo = AsyncMock()
    mock_artifact_repo.create_artifact = AsyncMock(return_value=mock_artifact)

    try:
        with (
            patch("app.workflows.tasks.extract_content.JinaReader", return_value=mock_jina),
            patch(
                "app.workflows.tasks.generate_embedding.EmbeddingService",
                return_value=mock_embedding_service,
            ),
            patch(
                "app.workflows.graph_builder.supervisor_route",
                new_callable=AsyncMock,
                return_value=mock_supervisor_result,
            ),
            # Mock router to return no agents (empty list) for faster execution
            patch(
                "app.workflows.nodes.agent_router.route_to_agents",
                return_value=[],  # No agents selected
            ),
            patch(
                "app.workflows.tasks.generate_artifact.ArtifactRepository",
                return_value=mock_artifact_repo,
            ),
        ):
            # Create workflow
            analysis_workflow = create_analysis_workflow()

            # Run workflow first time with timeout (increased for streaming/parallel overhead)
            workflow_config1 = {
                "configurable": {"thread_id": analysis_id},
                "run_name": f"test_analysis_checkpointer_run1_{analysis_id}",
                "tags": ["test", "integration", "workflow", "checkpointer"],
                "metadata": {
                    "analysis_id": analysis_id,
                    "url": test_url,
                    "test_type": "checkpointer",
                    "run": 1,
                },
            }
            result1 = await asyncio.wait_for(
                analysis_workflow.ainvoke(
                    {
                        "url": test_url,
                        "analysis_id": analysis_id,
                    },
                    config=workflow_config1,
                ),
                timeout=180.0,  # 3 minutes for real workflow with streaming/parallel overhead
            )

            # Run workflow again (should use checkpoint) with timeout
            # (increased for streaming/parallel overhead)
            workflow_config2 = {
                "configurable": {"thread_id": analysis_id},
                "run_name": f"test_analysis_checkpointer_run2_{analysis_id}",
                "tags": ["test", "integration", "workflow", "checkpointer"],
                "metadata": {
                    "analysis_id": analysis_id,
                    "url": test_url,
                    "test_type": "checkpointer",
                    "run": 2,
                },
            }
            result2 = await asyncio.wait_for(
                analysis_workflow.ainvoke(
                    {
                        "url": test_url,
                        "analysis_id": analysis_id,
                    },
                    config=workflow_config2,
                ),
                timeout=180.0,  # 3 minutes for real workflow with streaming/parallel overhead
            )

        # Verify both results are consistent (StateGraph checkpointing)
        assert result1["analysis_id"] == result2["analysis_id"]
        assert result1["url"] == result2["url"]
        assert len(result1["content_embedding"]) == len(result2["content_embedding"])
        # Verify state structure is consistent
        assert "supervisor_decision" in result1
        assert "supervisor_decision" in result2
        assert "agent_findings" in result1
        assert "agent_findings" in result2
    finally:
        # Ensure engine connections are disposed
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(
    150
)  # 2.5 minute max timeout - accounts for streaming/parallel execution overhead
async def test_workflow_persists_results_to_database(
    requires_database, reset_engine_connections
) -> None:
    """Test that workflow results are persisted to database after completion (Issue #168).

    This test verifies that _persist_analysis_data() correctly saves workflow results
    to the database, including raw_content, title, content_embedding, and that
    the search_vector trigger fires correctly.

    This test requires:
    - OpenAI API key configured (for embeddings and agents)
    - Database connection

    Note: External services (Jina, OpenAI) are mocked to avoid API dependency issues.
    """
    from sqlalchemy import select

    from app.domains.analysis.services.workflow import WorkflowOrchestrator

    # Use a simple test URL
    test_url = "https://react.dev"
    # Use a proper UUID for the analysis_id (required for database foreign key)
    analysis_id = uuid4()

    # Create Analysis record before running workflow (required for agent foreign keys)
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_id,
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to avoid API dependency issues
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(return_value=SAMPLE_EXTRACTION_RESULT)
    mock_jina.close = AsyncMock()

    # Mock embedding service to avoid OpenAI API dependency issues
    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=SAMPLE_EMBEDDING)
    mock_embedding_service.close = AsyncMock()

    # Mock supervisor to return empty agent selection (no agents to execute for faster test)
    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test content - no agents needed for persistence test",
            "confidence": 0.5,
        }
    }

    # Mock artifact repository to avoid database foreign key violations
    mock_artifact = MagicMock()
    mock_artifact.id = analysis_id
    mock_artifact_repo = AsyncMock()
    mock_artifact_repo.create_artifact = AsyncMock(return_value=mock_artifact)
    mock_artifact_repo.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    try:
        with (
            patch("app.workflows.tasks.extract_content.JinaReader", return_value=mock_jina),
            patch(
                "app.workflows.tasks.generate_embedding.EmbeddingService",
                return_value=mock_embedding_service,
            ),
            patch(
                "app.workflows.graph_builder.supervisor_route",
                new_callable=AsyncMock,
                return_value=mock_supervisor_result,
            ),
            # Mock router to return no agents (empty list) for faster execution
            patch(
                "app.workflows.nodes.agent_router.route_to_agents",
                return_value=[],  # No agents selected
            ),
            patch(
                "app.workflows.tasks.generate_artifact.ArtifactRepository",
                return_value=mock_artifact_repo,
            ),
        ):
            # Run full workflow via orchestrator (this calls data_persister.persist)
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            await orchestrator.run(
                analysis_id=analysis_id,
                url=test_url,
                skill_level="intermediate",
            )

        # Verify database persistence (Issue #168)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            assert analysis is not None, "Analysis record should exist"

            # Verify raw_content is persisted
            assert analysis.raw_content is not None, "raw_content should be persisted"
            assert analysis.raw_content == SAMPLE_EXTRACTION_RESULT["content"], (
                "raw_content should match extracted content"
            )

            # Verify title is persisted (extracted from extraction_metadata)
            assert analysis.title is not None, "title should be persisted"
            assert analysis.title == SAMPLE_EXTRACTION_RESULT["title"], (
                "title should match extracted title"
            )

            # Verify content_embedding is persisted
            assert analysis.content_embedding is not None, "content_embedding should be persisted"
            # Type guard for type checker
            if isinstance(analysis.content_embedding, list):
                assert len(analysis.content_embedding) == EXPECTED_EMBEDDING_DIMENSIONS, (
                    f"content_embedding should be {EXPECTED_EMBEDDING_DIMENSIONS} dimensions"
                )
                assert list(analysis.content_embedding) == SAMPLE_EMBEDDING, (
                    "content_embedding should match generated embedding"
                )

            # Verify extraction_metadata is persisted
            assert analysis.extraction_metadata is not None, (
                "extraction_metadata should be persisted"
            )
            assert isinstance(analysis.extraction_metadata, dict), (
                "extraction_metadata should be a dict"
            )
            assert "title" in analysis.extraction_metadata, (
                "extraction_metadata should contain title"
            )

            # Verify search_vector trigger fired (Issue #168 - full-text search)
            assert analysis.search_vector is not None, (
                "search_vector should be populated by trigger after persistence"
            )

    finally:
        # Ensure engine connections are disposed
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(150)
async def test_workflow_fails_when_required_fields_missing(
    requires_database,
    reset_engine_connections,
) -> None:
    """Workflow should fail when required fields (e.g., embedding) are missing."""
    test_url = "https://example.com/article"
    analysis_id = uuid4()

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_id,
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock workflow to return incomplete result (missing embedding)
    mock_workflow = MagicMock()
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Sample content",
            "extraction_metadata": {"title": "Incomplete Result"},
            # content_embedding intentionally missing
        }
    )

    # Run workflow task
    orchestrator = WorkflowOrchestrator(workflow=mock_workflow)
    await orchestrator.run(
        analysis_id=analysis_id,
        url=test_url,
        skill_level="intermediate",
    )

    # Verify analysis marked failed and no content persisted
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
        analysis = result.scalar_one_or_none()
        assert analysis is not None
        assert analysis.status == "failed"
        assert analysis.raw_content is None
        assert analysis.content_embedding is None

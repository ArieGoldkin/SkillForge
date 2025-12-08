"""Integration tests for library API endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.analysis import Analysis


@pytest.fixture
async def test_client(reset_engine_connections):
    """Create async test client using ASGITransport pattern."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for tests."""
    mock_service = AsyncMock()
    mock_service.generate_embedding.return_value = [0.1] * 1536
    mock_service.close = AsyncMock()
    return mock_service


class TestLibraryEndpointSearchMode:
    """Tests for library endpoint in search mode (with query parameter)."""

    @pytest.mark.asyncio
    async def test_hybrid_search_success(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test hybrid search mode returns results."""
        # Create test data
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/postgresql-guide",
            title="PostgreSQL Full-Text Search Guide",
            content_type="article",
            raw_content="PostgreSQL provides powerful full-text search capabilities using tsvector and tsquery.",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Mock embedding service
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Execute request
            response = await test_client.get(
                "/api/v1/library",
                params={
                    "query": "postgresql search",
                    "search_mode": "hybrid",
                    "limit": 20,
                    "offset": 0,
                },
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 20
        assert data["offset"] == 0
        assert isinstance(data["items"], list)
        assert data["items"][0]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_fulltext_search_success(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test fulltext search mode returns results."""
        # Create test data with searchable content
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/typescript-guide",
            title="TypeScript Guide",
            content_type="article",
            raw_content="TypeScript is a typed superset of JavaScript that compiles to plain JavaScript.",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Execute request
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "typescript javascript",
                "search_mode": "fulltext",
                "limit": 10,
                "offset": 0,
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["limit"] == 10
        assert data["items"][0]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_semantic_search_success(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test semantic search mode returns results."""
        # Create test data
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/react-hooks",
            title="React Hooks Guide",
            content_type="article",
            raw_content="React hooks allow you to use state and lifecycle features in functional components.",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Mock embedding service
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Execute request
            response = await test_client.get(
                "/api/v1/library",
                params={
                    "query": "react functional components",
                    "search_mode": "semantic",
                    "limit": 20,
                },
            )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_400(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test search with empty query string returns 400 error."""
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "",  # Empty string
                "search_mode": "hybrid",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "empty string" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_search_whitespace_query_returns_400(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test search with whitespace-only query returns 400 error."""
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "   ",  # Whitespace only
                "search_mode": "fulltext",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_search_pagination(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test search with pagination parameters."""
        # Create multiple test records
        for i in range(5):
            analysis = Analysis(
                id=uuid4(),
                url=f"https://example.com/article-{i}",
                title=f"Article {i}",
                content_type="article",
                raw_content=f"This is article number {i} about programming.",
                status="complete",
                created_at=datetime.now(UTC),
            )
            db_session.add(analysis)
        await db_session.commit()

        # Request page 2 with limit 2
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "programming",
                "search_mode": "fulltext",
                "limit": 2,
                "offset": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 2
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test search with no matching results."""
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "nonexistent-query-xyz-123",
                "search_mode": "fulltext",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_search_embedding_failure_fallback(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test hybrid search falls back to fulltext when embedding fails."""
        # Create test data
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/fallback-test",
            title="Fallback Test Article",
            content_type="article",
            raw_content="This tests the fallback behavior when embeddings fail.",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Mock embedding service to raise error
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.side_effect = Exception("Embedding API error")
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Execute request - should fallback to fulltext
            response = await test_client.get(
                "/api/v1/library",
                params={
                    "query": "fallback behavior",
                    "search_mode": "hybrid",
                },
            )

        # Should still succeed with fulltext fallback
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_search_semantic_embedding_failure_returns_500(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test semantic-only search returns 500 when embedding fails."""
        # Mock embedding service to raise error
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.side_effect = Exception("Embedding API error")
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Execute request
            response = await test_client.get(
                "/api/v1/library",
                params={
                    "query": "test query",
                    "search_mode": "semantic",
                },
            )

        # Should return 500 for semantic-only failure
        assert response.status_code == 500


class TestLibraryEndpointListingMode:
    """Tests for library endpoint in listing mode (without query parameter)."""

    @pytest.mark.asyncio
    async def test_list_all_analyses(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing all analyses without filters."""
        # Create test data
        for i in range(3):
            analysis = Analysis(
                id=uuid4(),
                url=f"https://example.com/content-{i}",
                title=f"Content {i}",
                content_type="article" if i % 2 == 0 else "video",
                status="complete",
                created_at=datetime.now(UTC),
            )
            db_session.add(analysis)
        await db_session.commit()

        # Execute request without query
        response = await test_client.get(
            "/api/v1/library",
            params={
                "limit": 20,
                "offset": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_with_content_type_filter(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing with content_type filter."""
        # Create test data with different content types
        article = Analysis(
            id=uuid4(),
            url="https://example.com/article",
            title="Article",
            content_type="article",
            status="complete",
            created_at=datetime.now(UTC),
        )
        video = Analysis(
            id=uuid4(),
            url="https://example.com/video",
            title="Video",
            content_type="video",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(article)
        db_session.add(video)
        await db_session.commit()

        # Filter by article
        response = await test_client.get(
            "/api/v1/library",
            params={"content_type": "article"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned items should be articles
        for item in data["items"]:
            assert item["content_type"] == "article"

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing with status filter."""
        # Create test data with different statuses
        complete = Analysis(
            id=uuid4(),
            url="https://example.com/complete",
            title="Complete",
            content_type="article",
            status="complete",
            created_at=datetime.now(UTC),
        )
        pending = Analysis(
            id=uuid4(),
            url="https://example.com/pending",
            title="Pending",
            content_type="article",
            status="pending",
            created_at=datetime.now(UTC),
        )
        db_session.add(complete)
        db_session.add(pending)
        await db_session.commit()

        # Filter by complete
        response = await test_client.get(
            "/api/v1/library",
            params={"status": "complete"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should have at least the complete analysis
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_with_multiple_filters(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing with both content_type and status filters."""
        # Create test data
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/filtered",
            title="Filtered Content",
            content_type="video",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Apply both filters
        response = await test_client.get(
            "/api/v1/library",
            params={
                "content_type": "video",
                "status": "complete",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All items should match both filters
        for item in data["items"]:
            assert item["content_type"] == "video"

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing with pagination."""
        # Create multiple records
        for i in range(10):
            analysis = Analysis(
                id=uuid4(),
                url=f"https://example.com/item-{i}",
                title=f"Item {i}",
                content_type="article",
                status="complete",
                created_at=datetime.now(UTC),
            )
            db_session.add(analysis)
        await db_session.commit()

        # Request page 2
        response = await test_client.get(
            "/api/v1/library",
            params={
                "limit": 5,
                "offset": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 5
        assert len(data["items"]) <= 5

    @pytest.mark.asyncio
    async def test_list_empty_results(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing with no matching results."""
        response = await test_client.get(
            "/api/v1/library",
            params={
                "content_type": "nonexistent_type",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_no_snippet_or_rank(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test listing mode returns no snippet or rank (only search mode has these)."""
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/test",
            title="Test",
            content_type="article",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        response = await test_client.get("/api/v1/library")

        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            assert item["snippet"] is None
            assert item["rank"] == 0.0


class TestLibraryEndpointValidation:
    """Tests for library endpoint validation and error cases."""

    @pytest.mark.asyncio
    async def test_invalid_limit_too_small(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test limit must be at least 1."""
        response = await test_client.get(
            "/api/v1/library",
            params={"limit": 0},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_limit_too_large(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test limit cannot exceed 100."""
        response = await test_client.get(
            "/api/v1/library",
            params={"limit": 101},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_offset_negative(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test offset cannot be negative."""
        response = await test_client.get(
            "/api/v1/library",
            params={"offset": -1},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_search_mode(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test invalid search_mode value."""
        response = await test_client.get(
            "/api/v1/library",
            params={
                "query": "test",
                "search_mode": "invalid_mode",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_default_search_mode_is_hybrid(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Test default search_mode is hybrid when not specified."""
        # Create test data
        analysis = Analysis(
            id=uuid4(),
            url="https://example.com/default-mode",
            title="Default Mode Test",
            content_type="article",
            raw_content="Testing default search mode behavior.",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        # Mock embedding service
        with patch("app.api.v1.library.EmbeddingService") as mock_embedding_cls:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = [0.1] * 1536
            mock_service.close = AsyncMock()
            mock_embedding_cls.return_value = mock_service

            # Execute request without search_mode parameter
            response = await test_client.get(
                "/api/v1/library",
                params={"query": "test"},
            )

        # Should succeed (hybrid is default)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_default_pagination_values(
        self, test_client, requires_database, reset_engine_connections
    ):
        """Test default pagination values (limit=20, offset=0)."""
        response = await test_client.get("/api/v1/library")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20
        assert data["offset"] == 0


class TestLibraryDeleteEndpoint:
    """Tests for deleting analyses via the library API."""

    @pytest.mark.asyncio
    async def test_delete_analysis_removes_record(
        self, test_client, requires_database, reset_engine_connections, db_session
    ):
        """Ensure DELETE removes analysis and cascading relations."""
        analysis_id = uuid4()
        analysis = Analysis(
            id=analysis_id,
            url="https://example.com/to-delete",
            title="To Delete",
            content_type="article",
            status="complete",
            created_at=datetime.now(UTC),
        )
        db_session.add(analysis)
        await db_session.commit()

        response = await test_client.delete(f"/api/v1/analyses/{analysis_id}")
        assert response.status_code == 204

        remaining = await db_session.get(Analysis, analysis_id)
        assert remaining is None

"""Unit tests for agent router with proactive memory injection.

Tests the async agent routing function that uses LangGraph's Send API
and injects proactive memory context for agents with inject_memory=True.

Reference: Issue #266 - Wire Proactive Recall into Agent Router
"""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.types import Send

from app.shared.services.memory.agent_memory_service import MemorySnippet
from app.domains.analysis.workflows.nodes.agent_router import (
    _fetch_agent_memory,
    _get_content_summary,
    route_to_agents,
)
from app.domains.analysis.workflows.state import AnalysisState, ContentRef

@pytest.mark.unit


@pytest.fixture
def sample_state() -> AnalysisState:
    """Create a sample AnalysisState for testing."""
    return AnalysisState(
        analysis_id="test-analysis-123",
        url="https://example.com/article",
        content_type="article",
        skill_level="intermediate",
        content_ref=ContentRef(
            uri="analysis://test-analysis-123/content",
            summary="Article about React hooks and performance optimization",
            size_bytes=5000,
            content_type="text/markdown",
            available_sections=["summary", "full", "code_blocks"],
        ),
        supervisor_decision={
            "agents": ["tech_comparator", "security_auditor", "code_quality_critic"],
            "reasoning": "Tech content needs comparison and security analysis",
        },
    )


@pytest.fixture
def sample_state_no_content() -> AnalysisState:
    """Create a sample AnalysisState without content."""
    return AnalysisState(
        analysis_id="test-analysis-456",
        url="https://example.com/article",
        content_type="article",
        supervisor_decision={
            "agents": ["tech_comparator"],
            "reasoning": "Test",
        },
    )


class TestGetContentSummary:
    """Test _get_content_summary helper function."""

    def test_extracts_from_content_ref(self, sample_state: AnalysisState) -> None:
        """Test extraction from content_ref.summary."""
        summary = _get_content_summary(sample_state)
        assert summary == "Article about React hooks and performance optimization"

    def test_falls_back_to_raw_content(self) -> None:
        """Test fallback to raw_content when content_ref missing."""
        state = AnalysisState(
            analysis_id="test-123",
            raw_content="This is a long article about testing. " * 50,
        )
        summary = _get_content_summary(state)
        assert len(summary) == 500
        assert "This is a long article about testing" in summary

    def test_returns_empty_when_no_content(self, sample_state_no_content: AnalysisState) -> None:
        """Test returns empty string when no content available."""
        summary = _get_content_summary(sample_state_no_content)
        assert summary == ""


class TestFetchAgentMemory:
    """Test _fetch_agent_memory helper function."""

    @pytest.mark.asyncio
    async def test_fetches_and_formats_memory(self) -> None:
        """Test successful memory fetch and formatting."""
        # Mock snippets
        mock_snippets = [
            MemorySnippet(
                content="SQL injection patterns in ORM queries",
                memory_type="vulnerability_pattern",
                relevance=0.85,
                source_id="prev-analysis-1",
            ),
        ]

        # Mock the session and fetch function
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.domains.analysis.workflows.nodes.agent_router.get_session_factory") as mock_session_factory,
            patch(
                "app.domains.analysis.workflows.nodes.agent_router.fetch_proactive_context",
                new_callable=AsyncMock,
            ) as mock_fetch,
        ):
            # Setup mocks
            mock_session_factory.return_value.return_value = mock_session
            mock_fetch.return_value = mock_snippets

            # Test
            result = await _fetch_agent_memory(
                agent_type="security_auditor",
                content_summary="React hooks performance",
            )

            # Verify
            assert result != ""
            assert "Relevant Context from Past Analyses" in result
            assert "vulnerability_pattern" in result
            mock_fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_value_error(self) -> None:
        """Test graceful handling of ValueError (missing API key)."""
        with patch("app.domains.analysis.workflows.nodes.agent_router.get_session_factory") as mock_session_factory:
            # Setup mock to raise ValueError
            mock_session_factory.side_effect = ValueError("OPENAI_API_KEY not set")

            # Should not raise, should return empty string
            result = await _fetch_agent_memory(
                agent_type="security_auditor",
                content_summary="React hooks",
            )

            assert result == ""

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_database_error(self) -> None:
        """Test graceful handling of database errors."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(side_effect=RuntimeError("Database connection failed"))

        with patch("app.domains.analysis.workflows.nodes.agent_router.get_session_factory") as mock_session_factory:
            mock_session_factory.return_value.return_value = mock_session

            # Should not raise, should return empty string
            result = await _fetch_agent_memory(
                agent_type="security_auditor",
                content_summary="React hooks",
            )

            assert result == ""


class TestRouteToAgents:
    """Test route_to_agents main function."""

    @pytest.mark.asyncio
    async def test_returns_send_objects(self, sample_state: AnalysisState) -> None:
        """Test that route_to_agents returns Send objects."""
        sends = await route_to_agents(sample_state)

        assert isinstance(sends, list)
        assert len(sends) == 3  # tech_comparator, security_auditor, code_quality_critic
        assert all(isinstance(send, Send) for send in sends)

    @pytest.mark.asyncio
    async def test_injects_memory_for_inject_memory_true(self, sample_state: AnalysisState) -> None:
        """Test memory injection for agents with inject_memory=True."""
        # Mock memory fetch to return some content
        with patch(
            "app.domains.analysis.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = "## Relevant Context\n\nSome prior memory..."

            sends = await route_to_agents(sample_state)

            # Find the security_auditor send (inject_memory=True)
            security_send = next(s for s in sends if s.node == "security_auditor")
            assert "prior_memory" in security_send.arg

            # Find the tech_comparator send (inject_memory=True)
            tech_send = next(s for s in sends if s.node == "tech_comparator")
            assert "prior_memory" in tech_send.arg

            # Verify memory fetch was called
            assert mock_fetch.await_count >= 2  # At least for security_auditor and tech_comparator

    @pytest.mark.asyncio
    async def test_no_memory_injection_when_disabled(self, sample_state: AnalysisState) -> None:
        """Test no memory injection for agents with inject_memory=False."""
        with patch(
            "app.domains.analysis.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = "## Relevant Context\n\nSome prior memory..."

            sends = await route_to_agents(sample_state)

            # Find the code_quality_critic send (inject_memory=False)
            critic_send = next(s for s in sends if s.node == "code_quality_critic")

            # Should NOT have prior_memory
            assert "prior_memory" not in critic_send.arg

    @pytest.mark.asyncio
    async def test_no_memory_injection_when_no_content(
        self, sample_state_no_content: AnalysisState
    ) -> None:
        """Test no memory injection when content_summary is empty."""
        with patch(
            "app.domains.analysis.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            sends = await route_to_agents(sample_state_no_content)

            # Should not call memory fetch when no content
            mock_fetch.assert_not_awaited()

            # Should still create send object
            assert len(sends) == 1

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_memory_error(self, sample_state: AnalysisState) -> None:
        """Test routing continues when memory fetch fails."""
        with patch(
            "app.domains.analysis.workflows.nodes.agent_router._fetch_agent_memory",
            new_callable=AsyncMock,
        ) as mock_fetch:
            # Simulate memory fetch returning empty string (error case)
            mock_fetch.return_value = ""

            sends = await route_to_agents(sample_state)

            # Should still create send objects
            assert len(sends) == 3

            # Agents should still be routed (without prior_memory)
            security_send = next(s for s in sends if s.node == "security_auditor")
            assert "analysis_id" in security_send.arg  # Other fields still present

    @pytest.mark.asyncio
    async def test_empty_agent_list(self) -> None:
        """Test handling of empty agent list."""
        state = AnalysisState(
            analysis_id="test-123",
            supervisor_decision={"agents": []},
        )

        sends = await route_to_agents(state)

        # Should return Send to aggregate when no agents selected
        assert len(sends) == 1
        assert sends[0].node == "aggregate"

    @pytest.mark.asyncio
    async def test_unknown_agent_skipped(self) -> None:
        """Test that unknown agents are skipped gracefully."""
        state = AnalysisState(
            analysis_id="test-123",
            supervisor_decision={
                "agents": ["tech_comparator", "unknown_agent", "security_auditor"]
            },
        )

        sends = await route_to_agents(state)

        # Should only route to known agents
        assert len(sends) == 2
        node_names = [s.node for s in sends]
        assert "tech_comparator" in node_names
        assert "security_auditor" in node_names
        assert "unknown_agent" not in node_names

    @pytest.mark.asyncio
    async def test_scoped_state_structure(self, sample_state: AnalysisState) -> None:
        """Test that scoped state contains expected minimal fields."""
        sends = await route_to_agents(sample_state)

        # Check first send's scoped state
        scoped_state = sends[0].arg

        # Should have minimal required fields
        assert "analysis_id" in scoped_state
        assert "content_ref" in scoped_state
        assert "content_type" in scoped_state

        # Should NOT have large fields
        assert "raw_content" not in scoped_state
        assert "extraction_metadata" not in scoped_state
        assert "agent_findings" not in scoped_state

"""Unit tests for Tier 3 Research agent nodes.

Tests for the 4 Tier 3 research agents that run in Deep Dive mode:
- deep_researcher_node: Extended web research with synthesized findings
- community_pulse_node: Sentiment analysis from community sources
- knowledge_curator_node: Knowledge graph connections to user's library
- learning_path_advisor_node: Personalized learning paths

Issue #501: Tier 3 Research Agents implementation.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample state for testing Tier 3 agents."""
    return {
        "analysis_id": str(uuid4()),
        "url": "https://example.com/langgraph-tutorial",
        "content_type": "article",
        "skill_level": "intermediate",
        "raw_content": "LangGraph is a framework for building stateful multi-agent workflows.",
        "extraction_metadata": {},
        "content_embedding": [0.1] * 1536,
        "supervisor_decision": {},
        "agent_findings": [],
        "aggregated_insights": {},
        "artifact_id": None,
    }


# ============================================================================
# DeepResearcherNode Tests
# ============================================================================


class TestDeepResearcherNode:
    """Tests for deep_researcher_node."""

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.nodes.agents.deep_researcher_node.has_content_available")
    async def test_deep_researcher_node_no_content(
        self,
        mock_has_content: MagicMock,
        sample_state: AnalysisState,
    ) -> None:
        """Test deep_researcher_node handles missing content gracefully."""
        from app.domains.analysis.workflows.nodes.agents.deep_researcher_node import (
            deep_researcher_node,
        )

        mock_has_content.return_value = False

        result = await deep_researcher_node(sample_state)

        # Should return agent_findings key (possibly empty on no content)
        assert "agent_findings" in result
        mock_has_content.assert_called_once()


# ============================================================================
# CommunityPulseNode Tests
# ============================================================================


class TestCommunityPulseNode:
    """Tests for community_pulse_node."""

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.nodes.agents.community_pulse_node.has_content_available")
    async def test_community_pulse_node_no_content(
        self,
        mock_has_content: MagicMock,
        sample_state: AnalysisState,
    ) -> None:
        """Test community_pulse_node handles missing content gracefully."""
        from app.domains.analysis.workflows.nodes.agents.community_pulse_node import (
            community_pulse_node,
        )

        mock_has_content.return_value = False

        result = await community_pulse_node(sample_state)

        assert "agent_findings" in result
        mock_has_content.assert_called_once()


# ============================================================================
# KnowledgeCuratorNode Tests
# ============================================================================


class TestKnowledgeCuratorNode:
    """Tests for knowledge_curator_node."""

    @pytest.mark.asyncio
    @patch(
        "app.domains.analysis.workflows.nodes.agents.knowledge_curator_node.has_content_available"
    )
    async def test_knowledge_curator_node_no_content(
        self,
        mock_has_content: MagicMock,
        sample_state: AnalysisState,
    ) -> None:
        """Test knowledge_curator_node handles missing content gracefully."""
        from app.domains.analysis.workflows.nodes.agents.knowledge_curator_node import (
            knowledge_curator_node,
        )

        mock_has_content.return_value = False

        result = await knowledge_curator_node(sample_state)

        assert "agent_findings" in result
        mock_has_content.assert_called_once()


# ============================================================================
# LearningPathAdvisorNode Tests
# ============================================================================


class TestLearningPathAdvisorNode:
    """Tests for learning_path_advisor_node."""

    @pytest.mark.asyncio
    @patch(
        "app.domains.analysis.workflows.nodes.agents.learning_path_advisor_node.has_content_available"
    )
    async def test_learning_path_advisor_node_no_content(
        self,
        mock_has_content: MagicMock,
        sample_state: AnalysisState,
    ) -> None:
        """Test learning_path_advisor_node handles missing content gracefully."""
        from app.domains.analysis.workflows.nodes.agents.learning_path_advisor_node import (
            learning_path_advisor_node,
        )

        mock_has_content.return_value = False

        result = await learning_path_advisor_node(sample_state)

        assert "agent_findings" in result
        mock_has_content.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================


class TestTier3AgentNodeImports:
    """Test that all Tier 3 agent nodes can be imported."""

    def test_import_deep_researcher_node(self) -> None:
        """Test deep_researcher_node can be imported."""
        from app.domains.analysis.workflows.nodes.agents.deep_researcher_node import (
            deep_researcher_node,
        )

        assert callable(deep_researcher_node)

    def test_import_community_pulse_node(self) -> None:
        """Test community_pulse_node can be imported."""
        from app.domains.analysis.workflows.nodes.agents.community_pulse_node import (
            community_pulse_node,
        )

        assert callable(community_pulse_node)

    def test_import_knowledge_curator_node(self) -> None:
        """Test knowledge_curator_node can be imported."""
        from app.domains.analysis.workflows.nodes.agents.knowledge_curator_node import (
            knowledge_curator_node,
        )

        assert callable(knowledge_curator_node)

    def test_import_learning_path_advisor_node(self) -> None:
        """Test learning_path_advisor_node can be imported."""
        from app.domains.analysis.workflows.nodes.agents.learning_path_advisor_node import (
            learning_path_advisor_node,
        )

        assert callable(learning_path_advisor_node)


class TestTier3AgentNodeExports:
    """Test Tier 3 nodes are exported from package __init__."""

    def test_nodes_in_package(self) -> None:
        """Test Tier 3 nodes are exported from agents __init__."""
        from app.domains.analysis.workflows.nodes import agents

        assert hasattr(agents, "deep_researcher_node")
        assert hasattr(agents, "community_pulse_node")
        assert hasattr(agents, "knowledge_curator_node")
        assert hasattr(agents, "learning_path_advisor_node")

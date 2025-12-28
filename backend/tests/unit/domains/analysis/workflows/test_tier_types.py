"""Unit tests for tier_types module (Issue #588).

Tests tier assignment constants, helper functions, and TierSummary type.
"""

import pytest

from app.domains.analysis.workflows.tier_types import (
    TIER_1_AGENTS,
    TIER_2_AGENTS,
    TIER_3_AGENTS,
    TIER_ASSIGNMENTS,
    TierSummary,
    get_agent_tier,
    get_agents_for_tier,
)


@pytest.mark.unit
class TestTierConstants:
    """Test tier assignment constants."""

    def test_tier1_agents_list(self):
        """Test Tier 1 contains foundational analysis agents."""
        expected = {"key_insights", "pros_cons", "audience_fit", "actionable"}
        assert set(TIER_1_AGENTS) == expected
        assert len(TIER_1_AGENTS) == 4

    def test_tier2_agents_list(self):
        """Test Tier 2 contains technical deep-dive agents."""
        expected = {
            "tech_comparator",
            "security_auditor",
            "impl_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
        }
        assert set(TIER_2_AGENTS) == expected
        assert len(TIER_2_AGENTS) == 8

    def test_tier3_agents_list(self):
        """Test Tier 3 contains strategic context agents."""
        expected = {
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        }
        assert set(TIER_3_AGENTS) == expected
        assert len(TIER_3_AGENTS) == 4

    def test_all_16_agents_assigned(self):
        """Test TIER_ASSIGNMENTS has all 16 agents assigned."""
        # Total agent count
        assert len(TIER_ASSIGNMENTS) == 16

        # All agents from tier lists are in assignments
        all_tier_agents = set(TIER_1_AGENTS + TIER_2_AGENTS + TIER_3_AGENTS)
        assert set(TIER_ASSIGNMENTS.keys()) == all_tier_agents

    def test_tier_assignments_values(self):
        """Test TIER_ASSIGNMENTS maps agents to correct tier numbers."""
        # Tier 1 agents map to 1
        for agent in TIER_1_AGENTS:
            assert TIER_ASSIGNMENTS[agent] == 1

        # Tier 2 agents map to 2
        for agent in TIER_2_AGENTS:
            assert TIER_ASSIGNMENTS[agent] == 2

        # Tier 3 agents map to 3
        for agent in TIER_3_AGENTS:
            assert TIER_ASSIGNMENTS[agent] == 3

    def test_no_duplicate_agents(self):
        """Test no agent appears in multiple tiers."""
        tier1_set = set(TIER_1_AGENTS)
        tier2_set = set(TIER_2_AGENTS)
        tier3_set = set(TIER_3_AGENTS)

        assert tier1_set.isdisjoint(tier2_set)
        assert tier1_set.isdisjoint(tier3_set)
        assert tier2_set.isdisjoint(tier3_set)


@pytest.mark.unit
class TestGetAgentTier:
    """Test get_agent_tier() helper function."""

    def test_tier1_agents(self):
        """Test get_agent_tier() returns 1 for Tier 1 agents."""
        assert get_agent_tier("key_insights") == 1
        assert get_agent_tier("pros_cons") == 1
        assert get_agent_tier("audience_fit") == 1
        assert get_agent_tier("actionable") == 1

    def test_tier2_agents(self):
        """Test get_agent_tier() returns 2 for Tier 2 agents."""
        assert get_agent_tier("tech_comparator") == 2
        assert get_agent_tier("security_auditor") == 2
        assert get_agent_tier("impl_planner") == 2
        assert get_agent_tier("performance_analyst") == 2
        assert get_agent_tier("code_quality_critic") == 2
        assert get_agent_tier("trend_validator") == 2
        assert get_agent_tier("dependency_mapper") == 2
        assert get_agent_tier("integration_feasibility") == 2

    def test_tier3_agents(self):
        """Test get_agent_tier() returns 3 for Tier 3 agents."""
        assert get_agent_tier("deep_researcher") == 3
        assert get_agent_tier("community_pulse") == 3
        assert get_agent_tier("knowledge_curator") == 3
        assert get_agent_tier("learning_path_advisor") == 3

    def test_unknown_agent(self):
        """Test get_agent_tier() returns None for unknown agents."""
        assert get_agent_tier("unknown_agent") is None
        assert get_agent_tier("nonexistent") is None
        assert get_agent_tier("") is None

    def test_case_sensitive(self):
        """Test get_agent_tier() is case-sensitive."""
        # Correct case
        assert get_agent_tier("key_insights") == 1

        # Wrong case - should not match
        assert get_agent_tier("KEY_INSIGHTS") is None
        assert get_agent_tier("Key_Insights") is None


@pytest.mark.unit
class TestGetAgentsForTier:
    """Test get_agents_for_tier() helper function."""

    def test_get_tier1_agents(self):
        """Test get_agents_for_tier(1) returns Tier 1 agents."""
        agents = get_agents_for_tier(1)
        assert set(agents) == set(TIER_1_AGENTS)
        assert len(agents) == 4

    def test_get_tier2_agents(self):
        """Test get_agents_for_tier(2) returns Tier 2 agents."""
        agents = get_agents_for_tier(2)
        assert set(agents) == set(TIER_2_AGENTS)
        assert len(agents) == 8

    def test_get_tier3_agents(self):
        """Test get_agents_for_tier(3) returns Tier 3 agents."""
        agents = get_agents_for_tier(3)
        assert set(agents) == set(TIER_3_AGENTS)
        assert len(agents) == 4

    def test_invalid_tier_returns_empty(self):
        """Test get_agents_for_tier() returns empty list for invalid tiers."""
        assert get_agents_for_tier(0) == []
        assert get_agents_for_tier(4) == []
        assert get_agents_for_tier(-1) == []
        assert get_agents_for_tier(999) == []

    def test_returned_list_is_reference(self):
        """Test returned list is a reference to the actual constant.

        Note: This is intentional - the function returns the actual list,
        not a copy. Callers should not modify the returned list.
        """
        agents = get_agents_for_tier(1)

        # Should return the same object (reference equality)
        assert agents is TIER_1_AGENTS

        # Modifying the returned list WILL affect the constant
        # (This is the current behavior - not ideal but documented)
        original_length = len(agents)
        agents.append("fake_agent")
        assert len(TIER_1_AGENTS) == original_length + 1

        # Clean up the modification
        TIER_1_AGENTS.remove("fake_agent")


@pytest.mark.unit
class TestTierSummary:
    """Test TierSummary TypedDict structure."""

    def test_create_valid_tier_summary(self):
        """Test creating a valid TierSummary with all fields."""
        summary: TierSummary = {
            "key_findings": [
                "Content focuses on RAG with LangGraph",
                "Requires intermediate Python knowledge",
                "Includes production-ready patterns",
            ],
            "risks_identified": [
                "Vector database complexity",
                "Embedding model selection critical",
            ],
            "recommendations": [
                "Start with simple retrieval patterns",
                "Use semantic caching to reduce costs",
            ],
            "agent_sources": ["key_insights", "audience_fit", "actionable"],
            "token_estimate": 650,
        }

        # Verify all fields are accessible
        assert len(summary["key_findings"]) == 3
        assert len(summary["risks_identified"]) == 2
        assert len(summary["recommendations"]) == 2
        assert len(summary["agent_sources"]) == 3
        assert summary["token_estimate"] == 650

    def test_create_minimal_tier_summary(self):
        """Test creating TierSummary with minimal fields."""
        summary: TierSummary = {
            "key_findings": ["Single finding"],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": ["test_agent"],
            "token_estimate": 100,
        }

        assert len(summary["key_findings"]) == 1
        assert summary["risks_identified"] == []
        assert summary["recommendations"] == []
        assert summary["token_estimate"] == 100

    def test_tier_summary_empty_lists(self):
        """Test TierSummary handles empty lists correctly."""
        summary: TierSummary = {
            "key_findings": [],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": [],
            "token_estimate": 0,
        }

        assert all(isinstance(v, list) for k, v in summary.items() if k != "token_estimate")
        assert summary["token_estimate"] == 0

    def test_tier_summary_type_annotations(self):
        """Test TierSummary field types match expectations."""
        summary: TierSummary = {
            "key_findings": ["finding1", "finding2"],
            "risks_identified": ["risk1"],
            "recommendations": ["rec1", "rec2"],
            "agent_sources": ["agent1"],
            "token_estimate": 500,
        }

        # Verify types
        assert isinstance(summary["key_findings"], list)
        assert all(isinstance(item, str) for item in summary["key_findings"])
        assert isinstance(summary["risks_identified"], list)
        assert all(isinstance(item, str) for item in summary["risks_identified"])
        assert isinstance(summary["recommendations"], list)
        assert all(isinstance(item, str) for item in summary["recommendations"])
        assert isinstance(summary["agent_sources"], list)
        assert all(isinstance(item, str) for item in summary["agent_sources"])
        assert isinstance(summary["token_estimate"], int)

    def test_tier_summary_practical_example(self):
        """Test TierSummary with realistic production data."""
        summary: TierSummary = {
            "key_findings": [
                "Tutorial covers RAG architecture patterns with LangGraph state machines",
                "Target audience: intermediate Python developers with basic ML knowledge",
                "Includes 5 runnable code examples with production deployment notes",
            ],
            "risks_identified": [
                "Vector database setup complexity may block quick adoption",
                "Embedding costs can escalate without semantic caching",
            ],
            "recommendations": [
                "Implement tiered approach: start with in-memory FAISS before PGVector",
                "Use semantic cache to reduce embedding API costs by 70-90%",
                "Review security section before production deployment",
            ],
            "agent_sources": [
                "key_insights",
                "audience_fit",
                "actionable",
                "pros_cons",
            ],
            "token_estimate": 780,
        }

        # Verify realistic data structure
        assert 3 <= len(summary["key_findings"]) <= 5
        assert len(summary["risks_identified"]) >= 1
        assert len(summary["recommendations"]) >= 1
        assert 400 <= summary["token_estimate"] <= 800  # Target range
        assert "key_insights" in summary["agent_sources"]

"""Unit tests for tier_summary_builder module (Issue #588).

Tests tier summary building and formatting for Sequential Tier Learning.
"""

from typing import TYPE_CHECKING

import pytest

from app.domains.analysis.workflows.tasks.aggregation.tier_summary_builder import (
    MAX_FINDINGS_PER_AGENT,
    MAX_ITEM_LENGTH,
    MAX_RECOMMENDATIONS_PER_AGENT,
    MAX_RISKS_PER_AGENT,
    MAX_TIER_SUMMARY_TOKENS,
    _estimate_tokens,
    _extract_from_findings_dict,
    _extract_from_list,
    _extract_key_insights,
    _extract_recommendations,
    _extract_risks,
    _truncate_to_budget,
    build_tier_summary,
    format_tier_context,
)

if TYPE_CHECKING:
    from app.domains.analysis.workflows.tier_types import TierSummary
    from app.shared.types.workflow_types import AgentFinding


@pytest.mark.unit
class TestEstimateTokens:
    """Test _estimate_tokens() helper function."""

    def test_estimate_short_text(self):
        """Test token estimation for short text."""
        text = "Hello world"
        tokens = _estimate_tokens(text)
        # "Hello world" = 11 chars / 4 = 2.75 -> 2 tokens
        assert tokens == 2

    def test_estimate_long_text(self):
        """Test token estimation for long text."""
        text = "A" * 100
        tokens = _estimate_tokens(text)
        # 100 chars / 4 = 25 tokens
        assert tokens == 25

    def test_estimate_empty_text(self):
        """Test token estimation for empty text."""
        assert _estimate_tokens("") == 0

    def test_estimate_realistic_text(self):
        """Test token estimation with realistic content."""
        text = (
            "This is a realistic example of technical content that might appear in agent findings."
        )
        tokens = _estimate_tokens(text)
        # ~86 chars / 4 = ~21 tokens
        assert 20 <= tokens <= 22


@pytest.mark.unit
class TestExtractFromList:
    """Test _extract_from_list() helper function."""

    def test_extract_string_items(self):
        """Test extracting string items from list."""
        items = ["item1", "item2", "item3", "item4"]
        result = _extract_from_list(items, max_items=2)
        assert result == ["item1", "item2"]

    def test_extract_dict_items(self):
        """Test extracting first string value from dict items."""
        items = [
            {"key": "value1", "other": "ignored"},
            {"key": "value2"},
        ]
        result = _extract_from_list(items, max_items=2)
        assert result == ["value1", "value2"]

    def test_extract_truncates_long_strings(self):
        """Test extraction truncates strings to MAX_ITEM_LENGTH."""
        long_string = "x" * 300
        items = [long_string]
        result = _extract_from_list(items, max_items=1)
        assert len(result[0]) == MAX_ITEM_LENGTH

    def test_extract_respects_max_items(self):
        """Test extraction respects max_items limit."""
        items = [f"item{i}" for i in range(10)]
        result = _extract_from_list(items, max_items=3)
        assert len(result) == 3

    def test_extract_empty_list(self):
        """Test extraction from empty list."""
        result = _extract_from_list([], max_items=5)
        assert result == []

    def test_extract_mixed_types(self):
        """Test extraction handles mixed types gracefully."""
        items = ["string", {"key": "dict_value"}, 123, None]
        result = _extract_from_list(items, max_items=4)
        # Should extract string and dict, skip others
        assert "string" in result
        assert "dict_value" in result
        assert len(result) == 2


@pytest.mark.unit
class TestExtractFromFindingsDict:
    """Test _extract_from_findings_dict() helper function."""

    def test_extract_from_list_value(self):
        """Test extracting from dict with list value."""
        findings = {
            "key_points": ["Finding 1", "Finding 2"],
            "other": "ignored",
        }
        result = _extract_from_findings_dict(findings, ["key_points"], max_items=2)
        assert result == ["Finding 1", "Finding 2"]

    def test_extract_from_string_value(self):
        """Test extracting from dict with string value."""
        findings = {"summary": "This is a summary"}
        result = _extract_from_findings_dict(findings, ["summary"], max_items=1)
        assert result == ["This is a summary"]

    def test_extract_prioritizes_search_keys(self):
        """Test extraction tries search keys in order."""
        findings = {
            "low_priority": ["Should not extract"],
            "insights": ["Should extract this"],
        }
        result = _extract_from_findings_dict(findings, ["insights", "low_priority"], max_items=1)
        assert result == ["Should extract this"]

    def test_extract_missing_key_returns_empty(self):
        """Test extraction returns empty list when keys not found."""
        findings = {"other": "value"}
        result = _extract_from_findings_dict(findings, ["missing_key"], max_items=5)
        assert result == []

    def test_extract_truncates_long_strings(self):
        """Test extraction truncates long string values."""
        long_string = "x" * 300
        findings = {"summary": long_string}
        result = _extract_from_findings_dict(findings, ["summary"], max_items=1)
        assert len(result[0]) == MAX_ITEM_LENGTH


@pytest.mark.unit
class TestExtractKeyInsights:
    """Test _extract_key_insights() function."""

    def test_extract_from_key_points(self):
        """Test extraction from 'key_points' field."""
        finding: AgentFinding = {
            "agent_type": "key_insights",
            "findings": {
                "key_points": [
                    "RAG tutorial with production patterns",
                    "Intermediate Python required",
                ],
            },
        }
        insights = _extract_key_insights(finding)
        assert len(insights) == 2
        assert "RAG tutorial" in insights[0]

    def test_extract_from_insights_field(self):
        """Test extraction from 'insights' field."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "insights": ["Insight 1", "Insight 2", "Insight 3"],
            },
        }
        insights = _extract_key_insights(finding)
        assert len(insights) <= MAX_FINDINGS_PER_AGENT
        assert "Insight 1" in insights

    def test_extract_respects_max_findings(self):
        """Test extraction respects MAX_FINDINGS_PER_AGENT limit."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "key_points": [f"Finding {i}" for i in range(10)],
            },
        }
        insights = _extract_key_insights(finding)
        assert len(insights) == MAX_FINDINGS_PER_AGENT

    def test_extract_fallback_to_top_level_fields(self):
        """Test fallback extraction from top-level findings fields."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "technologies": "FastAPI, PostgreSQL",
                "patterns": ["Pattern 1", "Pattern 2"],
                "metadata": {"count": 5},
            },
        }
        insights = _extract_key_insights(finding)
        assert len(insights) > 0
        # Should describe findings even without standard insight keys
        assert any("technologies:" in i for i in insights)

    def test_extract_empty_findings(self):
        """Test extraction from empty findings."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {},
        }
        insights = _extract_key_insights(finding)
        assert insights == []

    def test_extract_missing_findings_key(self):
        """Test extraction when 'findings' key is missing."""
        finding: AgentFinding = {
            "agent_type": "test",
        }
        insights = _extract_key_insights(finding)
        assert insights == []

    def test_extract_various_insight_keys(self):
        """Test extraction tries multiple common insight keys."""
        test_cases = [
            {"main_findings": ["Finding"]},
            {"summary": "Summary text"},
            {"overview": "Overview text"},
            {"main_topics": ["Topic 1"]},
            {"highlights": ["Highlight"]},
        ]

        for findings_data in test_cases:
            finding: AgentFinding = {
                "agent_type": "test",
                "findings": findings_data,
            }
            insights = _extract_key_insights(finding)
            assert len(insights) > 0


@pytest.mark.unit
class TestExtractRisks:
    """Test _extract_risks() function."""

    def test_extract_from_risks_field(self):
        """Test extraction from 'risks' field."""
        finding: AgentFinding = {
            "agent_type": "security_auditor",
            "findings": {
                "risks": ["SQL injection vulnerability", "Weak authentication"],
            },
        }
        risks = _extract_risks(finding)
        assert len(risks) <= MAX_RISKS_PER_AGENT
        assert "SQL injection" in risks[0]

    def test_extract_from_security_risks(self):
        """Test extraction from 'security_risks' field."""
        finding: AgentFinding = {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": ["XSS vulnerability", "CSRF missing"],
            },
        }
        risks = _extract_risks(finding)
        assert "XSS" in risks[0]

    def test_extract_from_warnings(self):
        """Test extraction from 'warnings' field."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "warnings": ["Deprecated API", "Performance concern"],
            },
        }
        risks = _extract_risks(finding)
        assert len(risks) > 0

    def test_extract_respects_max_risks(self):
        """Test extraction respects MAX_RISKS_PER_AGENT limit."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "risks": [f"Risk {i}" for i in range(10)],
            },
        }
        risks = _extract_risks(finding)
        assert len(risks) == MAX_RISKS_PER_AGENT

    def test_extract_empty_findings(self):
        """Test extraction from empty findings."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {},
        }
        risks = _extract_risks(finding)
        assert risks == []

    def test_extract_various_risk_keys(self):
        """Test extraction tries multiple common risk keys."""
        test_cases = [
            {"vulnerabilities": ["Vuln 1"]},
            {"concerns": ["Concern 1"]},
            {"issues": ["Issue 1"]},
            {"problems": ["Problem 1"]},
            {"threats": ["Threat 1"]},
            {"weaknesses": ["Weakness 1"]},
        ]

        for findings_data in test_cases:
            finding: AgentFinding = {
                "agent_type": "test",
                "findings": findings_data,
            }
            risks = _extract_risks(finding)
            assert len(risks) > 0


@pytest.mark.unit
class TestExtractRecommendations:
    """Test _extract_recommendations() function."""

    def test_extract_from_recommendations_field(self):
        """Test extraction from 'recommendations' field."""
        finding: AgentFinding = {
            "agent_type": "impl_planner",
            "findings": {
                "recommendations": ["Use async/await", "Add caching layer"],
            },
        }
        recs = _extract_recommendations(finding)
        assert len(recs) <= MAX_RECOMMENDATIONS_PER_AGENT
        assert "async/await" in recs[0]

    def test_extract_from_suggestions(self):
        """Test extraction from 'suggestions' field."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "suggestions": ["Suggestion 1", "Suggestion 2"],
            },
        }
        recs = _extract_recommendations(finding)
        assert "Suggestion 1" in recs

    def test_extract_from_best_practices(self):
        """Test extraction from 'best_practices' field."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "best_practices": ["Type hints", "Error handling"],
            },
        }
        recs = _extract_recommendations(finding)
        assert len(recs) > 0

    def test_extract_respects_max_recommendations(self):
        """Test extraction respects MAX_RECOMMENDATIONS_PER_AGENT limit."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {
                "recommendations": [f"Rec {i}" for i in range(10)],
            },
        }
        recs = _extract_recommendations(finding)
        assert len(recs) == MAX_RECOMMENDATIONS_PER_AGENT

    def test_extract_empty_findings(self):
        """Test extraction from empty findings."""
        finding: AgentFinding = {
            "agent_type": "test",
            "findings": {},
        }
        recs = _extract_recommendations(finding)
        assert recs == []

    def test_extract_various_recommendation_keys(self):
        """Test extraction tries multiple common recommendation keys."""
        test_cases = [
            {"action_items": ["Action 1"]},
            {"next_steps": ["Step 1"]},
            {"improvements": ["Improvement 1"]},
            {"advice": ["Advice 1"]},
            {"tips": ["Tip 1"]},
        ]

        for findings_data in test_cases:
            finding: AgentFinding = {
                "agent_type": "test",
                "findings": findings_data,
            }
            recs = _extract_recommendations(finding)
            assert len(recs) > 0


@pytest.mark.unit
class TestTruncateToBudget:
    """Test _truncate_to_budget() helper function."""

    def test_truncate_under_budget(self):
        """Test truncation when items fit within budget."""
        items = ["Short item", "Another short item"]
        result = _truncate_to_budget(items, char_budget=100)
        assert result == items

    def test_truncate_over_budget(self):
        """Test truncation when items exceed budget."""
        items = ["First finding", "Second finding", "Third finding"]
        result = _truncate_to_budget(items, char_budget=30)
        # Should include some items but stay under budget
        total_chars = len(" ".join(result))
        assert total_chars <= 30

    def test_truncate_last_item(self):
        """Test truncation adds ellipsis to last item if needed."""
        items = ["First", "Second", "This is a very long third item that will be truncated"]
        result = _truncate_to_budget(items, char_budget=40)
        # Last item should be truncated with "..."
        if len(result) > 2:
            assert result[-1].endswith("...")

    def test_truncate_empty_list(self):
        """Test truncation of empty list."""
        result = _truncate_to_budget([], char_budget=100)
        assert result == []

    def test_truncate_respects_min_meaningful_length(self):
        """Test truncation only adds item if meaningful text fits."""
        items = ["First", "Second", "Third"]
        # Very tight budget - may skip last item if not meaningful
        result = _truncate_to_budget(items, char_budget=15)
        assert len(" ".join(result)) <= 15

    def test_truncate_single_long_item(self):
        """Test truncation of single item exceeding budget."""
        items = ["This is a very long item that exceeds the character budget significantly"]
        result = _truncate_to_budget(items, char_budget=30)
        assert len(result) == 1
        assert len(result[0]) <= 30
        assert result[0].endswith("...")


@pytest.mark.unit
class TestBuildTierSummary:
    """Test build_tier_summary() main function."""

    def test_build_summary_with_valid_findings(self):
        """Test building summary with valid agent findings."""
        findings: list[AgentFinding] = [
            {
                "agent_type": "key_insights",
                "findings": {
                    "key_points": ["RAG tutorial", "LangGraph patterns"],
                },
            },
            {
                "agent_type": "security_auditor",
                "findings": {
                    "risks": ["SQL injection risk"],
                },
            },
            {
                "agent_type": "impl_planner",
                "findings": {
                    "recommendations": ["Use async patterns"],
                },
            },
        ]

        summary = build_tier_summary(findings, tier=1)

        assert isinstance(summary, dict)
        assert "key_findings" in summary
        assert "risks_identified" in summary
        assert "recommendations" in summary
        assert "agent_sources" in summary
        assert "token_estimate" in summary

        assert len(summary["agent_sources"]) == 3
        assert "key_insights" in summary["agent_sources"]
        assert len(summary["key_findings"]) > 0
        assert len(summary["risks_identified"]) > 0
        assert len(summary["recommendations"]) > 0

    def test_build_summary_empty_findings(self):
        """Test building summary with empty findings list."""
        summary = build_tier_summary([], tier=1)

        assert summary["key_findings"] == []
        assert summary["risks_identified"] == []
        assert summary["recommendations"] == []
        assert summary["agent_sources"] == []
        assert summary["token_estimate"] == 0

    def test_build_summary_respects_token_budget(self):
        """Test summary respects max_tokens budget."""
        # Create findings that would exceed budget
        findings: list[AgentFinding] = [
            {
                "agent_type": f"agent_{i}",
                "findings": {
                    "key_points": [
                        "This is a very long finding that contains a lot of detailed information "
                        * 10
                        for _ in range(5)
                    ],
                },
            }
            for i in range(10)
        ]

        summary = build_tier_summary(findings, tier=1, max_tokens=500)

        # Should compress to fit budget
        assert summary["token_estimate"] <= 500

    def test_build_summary_default_max_tokens(self):
        """Test summary uses default MAX_TIER_SUMMARY_TOKENS."""
        findings: list[AgentFinding] = [
            {
                "agent_type": "test",
                "findings": {"key_points": ["Finding"]},
            }
        ]

        summary = build_tier_summary(findings, tier=1)

        # Should use default of 800 tokens
        assert summary["token_estimate"] <= MAX_TIER_SUMMARY_TOKENS

    def test_build_summary_with_none_findings(self):
        """Test building summary handles None in findings list."""
        findings = [
            None,  # type: ignore
            {
                "agent_type": "test",
                "findings": {"key_points": ["Valid finding"]},
            },
            None,  # type: ignore
        ]

        summary = build_tier_summary(findings, tier=1)

        # Should skip None entries
        assert len(summary["agent_sources"]) == 1
        assert summary["agent_sources"][0] == "test"

    def test_build_summary_realistic_tier1_example(self):
        """Test building Tier 1 summary with realistic data."""
        findings: list[AgentFinding] = [
            {
                "agent_type": "key_insights",
                "findings": {
                    "main_topics": ["RAG", "LangGraph", "Vector databases"],
                    "key_points": [
                        "Comprehensive tutorial on RAG architecture",
                        "Uses LangGraph for state management",
                        "Includes production deployment patterns",
                    ],
                },
            },
            {
                "agent_type": "audience_fit",
                "findings": {
                    "insights": [
                        "Target audience: intermediate Python developers",
                        "Requires basic understanding of ML concepts",
                    ],
                },
            },
            {
                "agent_type": "actionable",
                "findings": {
                    "recommendations": [
                        "Start with simple retrieval patterns",
                        "Implement semantic caching early",
                    ],
                },
            },
        ]

        summary = build_tier_summary(findings, tier=1, max_tokens=800)

        # Token estimate depends on actual extraction
        assert summary["token_estimate"] <= 800
        assert len(summary["key_findings"]) >= 3
        assert len(summary["agent_sources"]) == 3
        # Verify specific content was extracted
        assert any(
            "RAG" in finding or "LangGraph" in finding for finding in summary["key_findings"]
        )


@pytest.mark.unit
class TestFormatTierContext:
    """Test format_tier_context() function."""

    def test_format_with_tier1_only(self):
        """Test formatting with only Tier 1 summary."""
        tier1: TierSummary = {
            "key_findings": ["RAG tutorial", "Intermediate level"],
            "risks_identified": ["Complex vector DB setup"],
            "recommendations": ["Start with simple patterns"],
            "agent_sources": ["key_insights"],
            "token_estimate": 500,
        }

        context = format_tier_context(tier1_summary=tier1)

        assert "Previous Analysis Context" in context
        assert "Foundational Analysis (Tier 1)" in context
        assert "RAG tutorial" in context
        assert "Complex vector DB setup" in context
        assert "Start with simple patterns" in context
        assert "Build upon these insights" in context

    def test_format_with_tier2_only(self):
        """Test formatting with only Tier 2 summary."""
        tier2: TierSummary = {
            "key_findings": ["FastAPI performance analysis"],
            "risks_identified": ["N+1 query pattern detected"],
            "recommendations": ["Add database indexing"],
            "agent_sources": ["performance_analyst"],
            "token_estimate": 600,
        }

        context = format_tier_context(tier2_summary=tier2)

        assert "Previous Analysis Context" in context
        assert "Technical Analysis (Tier 2)" in context
        assert "FastAPI performance" in context
        assert "N+1 query" in context
        assert "database indexing" in context

    def test_format_with_both_tiers(self):
        """Test formatting with both Tier 1 and Tier 2 summaries."""
        tier1: TierSummary = {
            "key_findings": ["Tier 1 finding"],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": ["key_insights"],
            "token_estimate": 300,
        }

        tier2: TierSummary = {
            "key_findings": ["Tier 2 finding"],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": ["tech_comparator"],
            "token_estimate": 400,
        }

        context = format_tier_context(tier1_summary=tier1, tier2_summary=tier2)

        assert "Foundational Analysis (Tier 1)" in context
        assert "Technical Analysis (Tier 2)" in context
        assert "Tier 1 finding" in context
        assert "Tier 2 finding" in context

    def test_format_with_no_summaries(self):
        """Test formatting with no summaries returns empty string."""
        context = format_tier_context()
        assert context == ""

        context = format_tier_context(tier1_summary=None, tier2_summary=None)
        assert context == ""

    def test_format_empty_fields(self):
        """Test formatting handles empty fields gracefully."""
        tier1: TierSummary = {
            "key_findings": [],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": ["test"],
            "token_estimate": 0,
        }

        context = format_tier_context(tier1_summary=tier1)

        # Should still have header and note
        assert "Previous Analysis Context" in context
        assert "Build upon these insights" in context
        # But no bullet lists
        assert "**Key Insights:**" not in context
        assert "**Risks Identified:**" not in context

    def test_format_markdown_structure(self):
        """Test formatted context uses proper markdown structure."""
        tier1: TierSummary = {
            "key_findings": ["Finding 1", "Finding 2"],
            "risks_identified": ["Risk 1"],
            "recommendations": ["Rec 1", "Rec 2"],
            "agent_sources": ["test"],
            "token_estimate": 400,
        }

        context = format_tier_context(tier1_summary=tier1)

        # Check markdown headers
        assert "## Previous Analysis Context" in context
        assert "### Foundational Analysis (Tier 1)" in context

        # Check markdown bold formatting
        assert "**Key Insights:**" in context
        assert "**Risks Identified:**" in context
        assert "**Recommendations:**" in context

        # Check bullet points
        assert "- Finding 1" in context
        assert "- Finding 2" in context
        assert "- Risk 1" in context
        assert "- Rec 1" in context

    def test_format_realistic_full_example(self):
        """Test formatting with realistic full Tier 1 and Tier 2 data."""
        tier1: TierSummary = {
            "key_findings": [
                "Tutorial covers RAG architecture with LangGraph",
                "Target audience: intermediate Python developers",
                "Includes 5 production-ready code examples",
            ],
            "risks_identified": [
                "Vector database setup complexity may block adoption",
                "Embedding costs can escalate without caching",
            ],
            "recommendations": [
                "Start with in-memory FAISS before PGVector",
                "Implement semantic caching for cost reduction",
            ],
            "agent_sources": ["key_insights", "audience_fit", "actionable"],
            "token_estimate": 650,
        }

        tier2: TierSummary = {
            "key_findings": [
                "FastAPI provides async benefits over Flask",
                "PostgreSQL HNSW indexing enables fast similarity search",
            ],
            "risks_identified": [
                "HNSW index rebuild can take hours for large datasets",
            ],
            "recommendations": [
                "Use progressive index building for large datasets",
                "Consider read replicas for production scale",
            ],
            "agent_sources": [
                "tech_comparator",
                "performance_analyst",
                "impl_planner",
            ],
            "token_estimate": 700,
        }

        context = format_tier_context(tier1_summary=tier1, tier2_summary=tier2)

        # Verify complete structure
        assert context.count("##") >= 1  # At least one main header
        assert context.count("###") >= 2  # At least two tier headers
        assert context.count("**") >= 6  # Multiple bold sections
        assert context.count("- ") >= 7  # Most bullet points

        # Verify specific content
        assert "RAG architecture" in context
        assert "Vector database setup" in context
        assert "FastAPI provides async" in context
        assert "HNSW index rebuild" in context

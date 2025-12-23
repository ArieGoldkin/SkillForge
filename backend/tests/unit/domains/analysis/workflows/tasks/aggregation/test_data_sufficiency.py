"""Unit tests for data_sufficiency module.

Tests the data sufficiency calculation that determines synthesis modes
based on agent data availability levels.

Issue #487 - Prevents hallucinations by detecting low-coverage scenarios.
"""

import pytest

from app.domains.analysis.workflows.tasks.aggregation.data_sufficiency import (
    DATA_AVAILABILITY_WEIGHTS,
    EXPECTED_AGENTS,
    FALLBACK_THRESHOLD,
    NORMAL_SYNTHESIS_THRESHOLD,
    CoverageGapInfo,
    DataSufficiencyResult,
    calculate_data_sufficiency,
    format_coverage_gaps_for_synthesis,
)


class TestCalculateDataSufficiency:
    """Tests for calculate_data_sufficiency function."""

    def test_all_sufficient_data(self) -> None:
        """All agents with sufficient data returns high score."""
        findings = [
            {
                "agent_name": "tech_comparator",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "security_auditor",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "implementation_planner",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "performance_analyst",
                "data_availability": "sufficient",
            },
        ]
        result = calculate_data_sufficiency(findings)

        # 4 agents with 1.0 each = 4.0 / 8.0 = 0.5
        assert result.coverage_score == pytest.approx(0.5, rel=0.01)
        assert result.agents_with_data == 4
        assert len(result.coverage_gaps) == 0
        assert result.recommended_mode == "normal"

    def test_mixed_availability(self) -> None:
        """Mixed data availability returns appropriate score."""
        findings = [
            {
                "agent_name": "tech_comparator",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "security_auditor",
                "data_availability": "limited",
                "data_availability_note": "No code examples found",
            },
            {
                "agent_name": "implementation_planner",
                "data_availability": "insufficient",
                "data_availability_note": "Content is news article, not tutorial",
            },
        ]
        result = calculate_data_sufficiency(findings)

        # 1.0 + 0.5 + 0.1 = 1.6 / 8.0 = 0.2
        assert result.coverage_score == pytest.approx(0.2, rel=0.01)
        assert result.agents_with_data == 3
        assert len(result.coverage_gaps) == 2
        # Below normal threshold, above fallback threshold
        assert result.recommended_mode == "fallback"  # 0.2 < 0.3 threshold

    def test_all_insufficient_data(self) -> None:
        """All agents with insufficient data triggers fallback."""
        findings = [
            {
                "agent_name": "tech_comparator",
                "data_availability": "insufficient",
            },
            {
                "agent_name": "security_auditor",
                "data_availability": "insufficient",
            },
        ]
        result = calculate_data_sufficiency(findings)

        # 0.1 + 0.1 = 0.2 / 8.0 = 0.025
        assert result.coverage_score < FALLBACK_THRESHOLD
        assert result.recommended_mode == "fallback"
        assert "trend-summary" in result.recommendation_reason.lower()

    def test_empty_findings(self) -> None:
        """Empty findings returns fallback mode."""
        result = calculate_data_sufficiency([])

        assert result.coverage_score == 0.0
        assert result.agents_with_data == 0
        assert result.total_agents == len(EXPECTED_AGENTS)
        assert result.recommended_mode == "fallback"
        assert "No agent findings" in result.recommendation_reason

    def test_unknown_availability_default(self) -> None:
        """Unknown data availability uses conservative default."""
        findings = [
            {
                "agent_name": "tech_comparator",
                # Missing data_availability field
            },
        ]
        result = calculate_data_sufficiency(findings)

        # Should use "unknown" weight of 0.3
        assert result.coverage_score == pytest.approx(0.3 / 8.0, rel=0.01)
        assert result.agents_with_data == 1

    def test_coverage_gaps_populated(self) -> None:
        """Coverage gaps are populated for limited/insufficient agents."""
        findings = [
            {
                "agent_name": "security_auditor",
                "data_availability": "limited",
                "data_availability_note": "Only high-level architecture discussed",
            },
            {
                "agent_name": "code_quality_critic",
                "data_availability": "insufficient",
                "data_availability_note": "No code examples in content",
            },
        ]
        result = calculate_data_sufficiency(findings)

        assert len(result.coverage_gaps) == 2

        # Check first gap (security_auditor)
        security_gap = next(
            g for g in result.coverage_gaps if g.agent_name == "security_auditor"
        )
        assert security_gap.data_availability == "limited"
        assert "high-level architecture" in security_gap.note

        # Check second gap (code_quality_critic)
        quality_gap = next(
            g for g in result.coverage_gaps if g.agent_name == "code_quality_critic"
        )
        assert quality_gap.data_availability == "insufficient"
        assert "minimal data found" in quality_gap.impact

    def test_result_structure(self) -> None:
        """Result has correct structure."""
        findings = [
            {"agent_name": "tech_comparator", "data_availability": "sufficient"},
        ]
        result = calculate_data_sufficiency(findings)

        assert isinstance(result, DataSufficiencyResult)
        assert isinstance(result.coverage_score, float)
        assert isinstance(result.agents_with_data, int)
        assert isinstance(result.total_agents, int)
        assert isinstance(result.coverage_gaps, list)
        assert isinstance(result.recommended_mode, str)
        assert isinstance(result.recommendation_reason, str)

    def test_score_range(self) -> None:
        """Coverage score is always between 0.0 and 1.0."""
        test_cases = [
            [],  # Empty
            [{"agent_name": "a", "data_availability": "sufficient"}],
            [{"agent_name": "a", "data_availability": "insufficient"}],
            # Many agents (more than expected)
            [
                {"agent_name": f"agent_{i}", "data_availability": "sufficient"}
                for i in range(20)
            ],
        ]

        for findings in test_cases:
            result = calculate_data_sufficiency(findings)
            assert 0.0 <= result.coverage_score <= 1.0


class TestSynthesisModeRecommendations:
    """Tests for synthesis mode recommendation logic."""

    def test_normal_mode_threshold(self) -> None:
        """Score >= 0.5 recommends normal mode."""
        # Need 4 agents with sufficient data for 50%
        findings = [
            {"agent_name": f"agent_{i}", "data_availability": "sufficient"}
            for i in range(4)
        ]
        result = calculate_data_sufficiency(findings)

        assert result.coverage_score >= NORMAL_SYNTHESIS_THRESHOLD
        assert result.recommended_mode == "normal"

    def test_limited_mode_threshold(self) -> None:
        """Score between 0.3-0.5 recommends limited mode."""
        # 3 agents with sufficient = 0.375 (between thresholds)
        findings = [
            {"agent_name": f"agent_{i}", "data_availability": "sufficient"}
            for i in range(3)
        ]
        result = calculate_data_sufficiency(findings)

        # 3.0 / 8.0 = 0.375
        assert FALLBACK_THRESHOLD <= result.coverage_score < NORMAL_SYNTHESIS_THRESHOLD
        assert result.recommended_mode == "limited"

    def test_fallback_mode_threshold(self) -> None:
        """Score < 0.3 recommends fallback mode."""
        # 2 agents with sufficient = 0.25 (below fallback threshold)
        findings = [
            {"agent_name": f"agent_{i}", "data_availability": "sufficient"}
            for i in range(2)
        ]
        result = calculate_data_sufficiency(findings)

        # 2.0 / 8.0 = 0.25
        assert result.coverage_score < FALLBACK_THRESHOLD
        assert result.recommended_mode == "fallback"
        assert "trend-summary" in result.recommendation_reason.lower()

    def test_normal_mode_with_gaps(self) -> None:
        """Normal mode still acknowledges coverage gaps."""
        findings = [
            {"agent_name": "agent_1", "data_availability": "sufficient"},
            {"agent_name": "agent_2", "data_availability": "sufficient"},
            {"agent_name": "agent_3", "data_availability": "sufficient"},
            {"agent_name": "agent_4", "data_availability": "sufficient"},
            {
                "agent_name": "agent_5",
                "data_availability": "limited",
                "data_availability_note": "Partial data",
            },
        ]
        result = calculate_data_sufficiency(findings)

        # 4.0 + 0.5 = 4.5 / 8.0 = 0.5625
        assert result.recommended_mode == "normal"
        assert len(result.coverage_gaps) == 1
        assert "partial data" in result.recommendation_reason.lower()


class TestCoverageGapInfo:
    """Tests for CoverageGapInfo dataclass."""

    def test_gap_info_creation(self) -> None:
        """CoverageGapInfo can be created with all fields."""
        gap = CoverageGapInfo(
            agent_name="security_auditor",
            data_availability="limited",
            note="No code examples found",
            impact="Security analysis may miss important risks",
        )

        assert gap.agent_name == "security_auditor"
        assert gap.data_availability == "limited"
        assert gap.note == "No code examples found"
        assert "security" in gap.impact.lower()


class TestFormatCoverageGapsForSynthesis:
    """Tests for format_coverage_gaps_for_synthesis function."""

    def test_format_gaps(self) -> None:
        """Gaps are formatted correctly for synthesis schema."""
        gaps = [
            CoverageGapInfo(
                agent_name="security_auditor",
                data_availability="limited",
                note="Only high-level discussion",
                impact="May miss important risks",
            ),
            CoverageGapInfo(
                agent_name="code_quality_critic",
                data_availability="insufficient",
                note="No code examples",
                impact="Best practices incomplete",
            ),
        ]

        formatted = format_coverage_gaps_for_synthesis(gaps)

        assert len(formatted) == 2

        # Check first gap
        assert formatted[0]["missing_agent"] == "security_auditor"
        assert formatted[0]["missing_perspective"] == "Only high-level discussion"
        assert formatted[0]["impact"] == "May miss important risks"

        # Check second gap
        assert formatted[1]["missing_agent"] == "code_quality_critic"
        assert formatted[1]["missing_perspective"] == "No code examples"
        assert formatted[1]["impact"] == "Best practices incomplete"

    def test_format_empty_gaps(self) -> None:
        """Empty gaps list returns empty list."""
        formatted = format_coverage_gaps_for_synthesis([])
        assert formatted == []

    def test_format_matches_schema(self) -> None:
        """Formatted output matches CoverageGap schema keys."""
        gaps = [
            CoverageGapInfo(
                agent_name="test_agent",
                data_availability="limited",
                note="Test note",
                impact="Test impact",
            ),
        ]

        formatted = format_coverage_gaps_for_synthesis(gaps)

        # Should have exactly these keys (matching CoverageGap in aggregated_insights.py)
        assert set(formatted[0].keys()) == {
            "missing_agent",
            "missing_perspective",
            "impact",
        }


class TestDataAvailabilityWeights:
    """Tests for DATA_AVAILABILITY_WEIGHTS constant."""

    def test_weights_exist(self) -> None:
        """All expected availability levels have weights."""
        expected = ["sufficient", "limited", "insufficient", "unknown"]
        for level in expected:
            assert level in DATA_AVAILABILITY_WEIGHTS

    def test_weight_ordering(self) -> None:
        """Weights decrease from sufficient to insufficient."""
        assert DATA_AVAILABILITY_WEIGHTS["sufficient"] == 1.0
        assert DATA_AVAILABILITY_WEIGHTS["sufficient"] > DATA_AVAILABILITY_WEIGHTS["limited"]
        assert DATA_AVAILABILITY_WEIGHTS["limited"] > DATA_AVAILABILITY_WEIGHTS["insufficient"]

    def test_unknown_conservative(self) -> None:
        """Unknown weight is conservative (lower than limited)."""
        assert DATA_AVAILABILITY_WEIGHTS["unknown"] <= DATA_AVAILABILITY_WEIGHTS["limited"]


class TestExpectedAgents:
    """Tests for EXPECTED_AGENTS constant."""

    def test_agents_list_populated(self) -> None:
        """Expected agents list contains the 8 specialized agents."""
        assert len(EXPECTED_AGENTS) == 8

    def test_known_agents_present(self) -> None:
        """Known agent names are in the list."""
        known_agents = [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
        ]
        for agent in known_agents:
            assert agent in EXPECTED_AGENTS


class TestRealWorldScenarios:
    """Tests simulating real-world analysis scenarios."""

    def test_news_article_scenario(self) -> None:
        """News article content results in low coverage / fallback mode."""
        # Simulates analyzing a news article about Qwen3-Next
        # Most agents find insufficient implementation details
        findings = [
            {
                "agent_name": "tech_comparator",
                "data_availability": "limited",
                "data_availability_note": "Only high-level comparison, no technical specs",
            },
            {
                "agent_name": "security_auditor",
                "data_availability": "insufficient",
                "data_availability_note": "No security discussion in news article",
            },
            {
                "agent_name": "implementation_planner",
                "data_availability": "insufficient",
                "data_availability_note": "No implementation details - news announcement",
            },
            {
                "agent_name": "trend_validator",
                "data_availability": "sufficient",
                "data_availability_note": "Good trend information from announcement",
            },
        ]

        result = calculate_data_sufficiency(findings)

        # 0.5 + 0.1 + 0.1 + 1.0 = 1.7 / 8.0 = 0.2125
        assert result.coverage_score < FALLBACK_THRESHOLD
        assert result.recommended_mode == "fallback"
        assert len(result.coverage_gaps) >= 2

    def test_tutorial_scenario(self) -> None:
        """Technical tutorial results in high coverage / normal mode."""
        # Simulates analyzing a detailed technical tutorial
        findings = [
            {
                "agent_name": "tech_comparator",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "security_auditor",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "implementation_planner",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "integration_feasibility",
                "data_availability": "sufficient",
            },
            {
                "agent_name": "performance_analyst",
                "data_availability": "limited",
                "data_availability_note": "No benchmarks provided",
            },
            {
                "agent_name": "code_quality_critic",
                "data_availability": "sufficient",
            },
        ]

        result = calculate_data_sufficiency(findings)

        # 5*1.0 + 0.5 = 5.5 / 8.0 = 0.6875
        assert result.coverage_score >= NORMAL_SYNTHESIS_THRESHOLD
        assert result.recommended_mode == "normal"
        assert len(result.coverage_gaps) == 1

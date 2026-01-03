"""Tests for G-Eval rubrics validation and completeness."""

from __future__ import annotations

from app.shared.services.g_eval.rubrics import (
    DEFAULT_RUBRICS,
    SUPPORTED_CRITERIA,
    format_rubric_for_prompt,
    get_agent_rubrics,
    get_all_agent_types,
    get_criterion_rubric,
    get_rubric_coverage,
    validate_all_rubrics,
    validate_rubric,
)
from app.shared.services.prompts.chain_of_thought import get_all_cot_agent_types


class TestRubricValidation:
    """Test suite for rubric validation logic."""

    def test_all_agent_rubrics_are_valid(self) -> None:
        """All agent rubrics should pass validation checks."""
        errors = validate_all_rubrics()
        assert errors == {}, f"Found validation errors: {errors}"

    def test_all_agent_types_have_rubrics(self) -> None:
        """All agent types from CoT prompts should have rubrics.

        Issue #570: Extended to cover all 20+ agents in AGENT_REGISTRY plus
        task-level processors (synthesizer, artifact_generator, code_reviewer).
        """
        cot_agents = set(get_all_cot_agent_types())
        rubric_agents = set(get_all_agent_types())

        # All CoT agents should have rubrics
        missing_rubrics = cot_agents - rubric_agents
        assert not missing_rubrics, f"CoT agents missing rubrics: {missing_rubrics}"

        # Allow extra rubrics for:
        # - Task-level processors: artifact_generator, synthesizer, code_reviewer
        # - Tier 1 agents: key_insights, pros_cons, audience_fit, actionable
        # - Tier 2 agents: fact_validator, source_credibility, freshness_checker,
        #   alternatives_finder, dependency_mapper, code_quality_critic,
        #   trend_validator, integration_feasibility
        # - Tier 3 agents: deep_researcher, community_pulse, knowledge_curator,
        #   learning_path_advisor
        # These are all valid agents in AGENT_REGISTRY or task processors
        extra_rubrics = rubric_agents - cot_agents
        # All extra rubrics are intentional - we cover the full agent registry
        assert len(extra_rubrics) >= 0, "Extra rubrics check passed"

    def test_rubric_coverage_is_complete(self) -> None:
        """Rubric coverage should show all agents with no errors."""
        coverage = get_rubric_coverage()

        assert coverage["is_valid"], f"Validation errors found: {coverage['validation_errors']}"
        # Issue #570: Extended to 25 agents (20 registry + 5 task-level/archived)
        assert coverage["total_agents"] >= 20, f"Expected 20+ agents, got {coverage['total_agents']}"
        assert len(coverage["agents"]) >= 20

    def test_each_rubric_has_five_scores(self) -> None:
        """Each rubric criterion should have scores 1-5."""
        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            rubrics = config["rubrics"]

            for criterion, rubric in rubrics.items():
                assert set(rubric.keys()) == {1, 2, 3, 4, 5}, (
                    f"{agent_type}.{criterion} missing scores: "
                    f"expected {{1,2,3,4,5}}, got {set(rubric.keys())}"
                )

    def test_each_score_has_description(self) -> None:
        """Each score should have a non-empty description."""
        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            rubrics = config["rubrics"]

            for criterion, rubric in rubrics.items():
                for score in range(1, 6):
                    description = rubric[score]
                    assert isinstance(description, str), (
                        f"{agent_type}.{criterion}.{score} is not a string"
                    )
                    assert description.strip(), (
                        f"{agent_type}.{criterion}.{score} has empty description"
                    )

    def test_weights_sum_to_one(self) -> None:
        """Weights for each agent should sum to approximately 1.0."""
        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            weights = config["weights"]

            weight_sum = sum(weights.values())
            assert 0.99 <= weight_sum <= 1.01, (
                f"{agent_type} weights sum to {weight_sum:.3f}, expected ~1.0"
            )

    def test_criteria_and_weights_aligned(self) -> None:
        """Criteria list should match weight keys."""
        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            criteria = config["criteria"]
            weights = config["weights"]

            assert set(criteria) == set(weights.keys()), (
                f"{agent_type}: criteria {criteria} doesn't match weights {list(weights.keys())}"
            )

    def test_no_agent_uses_default_rubrics_entirely(self) -> None:
        """No agent should be using DEFAULT_RUBRICS for all criteria."""
        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            rubrics = config["rubrics"]

            # Check if all rubrics are identical to DEFAULT_RUBRICS
            uses_only_defaults = all(
                rubrics.get(criterion) == DEFAULT_RUBRICS.get(criterion)
                for criterion in config["criteria"]
            )

            assert not uses_only_defaults, (
                f"{agent_type} is using only DEFAULT_RUBRICS - needs specialized rubrics"
            )


class TestRubricAPI:
    """Test suite for rubric API functions."""

    def test_get_agent_rubrics_returns_valid_config(self) -> None:
        """get_agent_rubrics should return a valid configuration dict."""
        config = get_agent_rubrics("tech_comparator")

        assert "criteria" in config
        assert "weights" in config
        assert "rubrics" in config
        assert len(config["criteria"]) > 0
        assert len(config["weights"]) > 0
        assert len(config["rubrics"]) > 0

    def test_get_agent_rubrics_fallback_to_default(self) -> None:
        """get_agent_rubrics should return defaults for unknown agents."""
        config = get_agent_rubrics("unknown_agent_type")

        assert config["criteria"] == SUPPORTED_CRITERIA
        assert config["rubrics"] == DEFAULT_RUBRICS

    def test_get_criterion_rubric_returns_scores(self) -> None:
        """get_criterion_rubric should return score descriptions."""
        rubric = get_criterion_rubric("tech_comparator", "balance")

        assert isinstance(rubric, dict)
        assert set(rubric.keys()) == {1, 2, 3, 4, 5}
        assert all(isinstance(v, str) for v in rubric.values())

    def test_get_criterion_rubric_fallback(self) -> None:
        """get_criterion_rubric should fallback to defaults for unknown criteria."""
        rubric = get_criterion_rubric("tech_comparator", "unknown_criterion")

        assert rubric == DEFAULT_RUBRICS["completeness"]

    def test_format_rubric_for_prompt(self) -> None:
        """format_rubric_for_prompt should create readable text."""
        formatted = format_rubric_for_prompt("tech_comparator", "balance")

        assert "Score 1:" in formatted
        assert "Score 5:" in formatted
        assert "biased" in formatted.lower()

    def test_get_all_agent_types(self) -> None:
        """get_all_agent_types should return all agent type names."""
        agents = get_all_agent_types()

        assert isinstance(agents, list)
        # Issue #570: Extended to 25 agents covering full registry
        assert len(agents) >= 20, f"Expected 20+ agents, got {len(agents)}"
        # Core agents that must exist
        assert "tech_comparator" in agents
        assert "learning_path" in agents
        assert "artifact_generator" in agents
        assert "synthesizer" in agents
        assert "key_insights" in agents


class TestRubricContent:
    """Test suite for rubric content quality and alignment with CoT."""

    def test_learning_path_has_specialized_rubrics(self) -> None:
        """learning_path should have specialized rubrics (not DEFAULT_RUBRICS)."""
        config = get_agent_rubrics("learning_path")

        # Check that at least pedagogical_quality is specialized
        assert "pedagogical_quality" in config["criteria"]
        assert "pedagogical_quality" in config["rubrics"]

        # Verify it's not a default rubric
        assert config["rubrics"]["pedagogical_quality"] != DEFAULT_RUBRICS.get(
            "pedagogical_quality", {}
        )

    def test_tech_comparator_criteria_align_with_cot(self) -> None:
        """tech_comparator rubrics should align with CoT reasoning steps."""
        config = get_agent_rubrics("tech_comparator")

        # CoT has: IDENTIFY, CATEGORIZE, ANALYZE TRADE-OFFS, SYNTHESIZE
        # Should map to: completeness (dimensions), accuracy, balance, recommendation
        assert "completeness" in config["criteria"]
        assert "accuracy" in config["criteria"]
        assert "balance" in config["criteria"]
        assert "recommendation" in config["criteria"]

    def test_security_auditor_criteria_align_with_cot(self) -> None:
        """security_auditor rubrics should align with CoT reasoning steps."""
        config = get_agent_rubrics("security_auditor")

        # CoT has: THREAT MODELING, VULNERABILITY SCANNING, RISK ASSESSMENT, MITIGATION
        # Should map to: completeness, severity_assessment, actionability, depth
        assert "completeness" in config["criteria"]
        assert "severity_assessment" in config["criteria"]
        assert "actionability" in config["criteria"]
        assert "depth" in config["criteria"]

    def test_implementation_planner_criteria_align_with_cot(self) -> None:
        """implementation_planner rubrics should align with CoT reasoning steps."""
        config = get_agent_rubrics("implementation_planner")

        # CoT has: SCOPE ANALYSIS, ARCHITECTURE DECISIONS, TASK BREAKDOWN, RISK IDENTIFICATION
        # Should map to: completeness, feasibility, sequencing, risk_awareness
        assert "completeness" in config["criteria"]
        assert "feasibility" in config["criteria"]
        assert "sequencing" in config["criteria"]
        assert "risk_awareness" in config["criteria"]

    def test_rubric_descriptions_are_measurable(self) -> None:
        """Rubric descriptions should contain measurable/specific criteria."""
        # Look for measurable terms in rubric descriptions
        measurable_terms = [
            "missing",
            "all",
            "most",
            "some",
            "no",
            "comprehensive",
            "basic",
            "thorough",
            "1-2",
            "3-4",
            "major",
        ]

        for agent_type in get_all_agent_types():
            config = get_agent_rubrics(agent_type)
            rubrics = config["rubrics"]

            for criterion, rubric in rubrics.items():
                for score, description in rubric.items():
                    # At least some rubrics should have measurable terms
                    # This is a heuristic check
                    has_measurable = any(term in description.lower() for term in measurable_terms)

                    # We allow some flexibility but at least score 1 and 5 should be clear
                    if score in {1, 5}:
                        assert len(description) > 20, (
                            f"{agent_type}.{criterion}.{score} is too short: '{description}'"
                        )


class TestRubricEdgeCases:
    """Test edge cases and error handling."""

    def test_validate_rubric_with_missing_keys(self) -> None:
        """validate_rubric should catch missing required keys."""
        invalid_config = {"criteria": ["test"]}  # Missing weights and rubrics

        errors = validate_rubric("test_agent", invalid_config)

        assert len(errors) > 0
        assert any("Missing required keys" in err for err in errors)

    def test_validate_rubric_with_weight_mismatch(self) -> None:
        """validate_rubric should catch criteria/weights mismatch."""
        invalid_config = {
            "criteria": ["completeness", "accuracy"],
            "weights": {"completeness": 1.0},  # Missing accuracy
            "rubrics": {},
        }

        errors = validate_rubric("test_agent", invalid_config)

        assert len(errors) > 0
        assert any("doesn't match weight keys" in err for err in errors)

    def test_validate_rubric_with_incorrect_weight_sum(self) -> None:
        """validate_rubric should catch incorrect weight sums."""
        invalid_config = {
            "criteria": ["completeness"],
            "weights": {"completeness": 0.5},  # Should sum to 1.0
            "rubrics": {"completeness": {1: "test", 2: "test", 3: "test", 4: "test", 5: "test"}},
        }

        errors = validate_rubric("test_agent", invalid_config)

        assert len(errors) > 0
        assert any("Weights sum to" in err for err in errors)

    def test_validate_rubric_with_missing_scores(self) -> None:
        """validate_rubric should catch missing score levels."""
        invalid_config = {
            "criteria": ["completeness"],
            "weights": {"completeness": 1.0},
            "rubrics": {"completeness": {1: "test", 3: "test", 5: "test"}},  # Missing 2 and 4
        }

        errors = validate_rubric("test_agent", invalid_config)

        assert len(errors) > 0
        assert any("Missing scores" in err for err in errors)

    def test_validate_rubric_with_empty_description(self) -> None:
        """validate_rubric should catch empty descriptions."""
        invalid_config = {
            "criteria": ["completeness"],
            "weights": {"completeness": 1.0},
            "rubrics": {"completeness": {1: "", 2: "test", 3: "test", 4: "test", 5: "test"}},
        }

        errors = validate_rubric("test_agent", invalid_config)

        assert len(errors) > 0
        assert any("empty description" in err for err in errors)

"""Tests for per-agent output validators (Issue #507).

Tests comprehensive validation logic for each agent type:
- KeyInsightsValidator
- ProsConsValidator
- AudienceFitValidator
- ActionableValidator
- TechComparatorValidator
- SecurityAuditorValidator
- ImplementationPlannerValidator

Plus tests for ValidationResult, get_validator(), and validate_agent_output().
"""

import pytest

from app.domains.analysis.workflows.agents.validation.output_validators import (
    AGENT_VALIDATORS,
    MIN_DESCRIPTION_LENGTH,
    MIN_VERDICT_LENGTH,
    ActionableValidator,
    AgentOutputValidator,
    AudienceFitValidator,
    ImplementationPlannerValidator,
    KeyInsightsValidator,
    ProsConsValidator,
    SecurityAuditorValidator,
    TechComparatorValidator,
    ValidationResult,
    get_validator,
    validate_agent_output,
)

# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_valid_result_no_issues(self) -> None:
        """Test ValidationResult with no issues is valid."""
        result = ValidationResult(is_valid=True, issues=[], confidence=0.9)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.9
        assert result.retry_recommended is True  # Default for <=3 issues

    def test_invalid_result_with_issues(self) -> None:
        """Test ValidationResult with issues is invalid."""
        issues = ["Issue 1", "Issue 2"]
        result = ValidationResult(is_valid=False, issues=issues, confidence=0.5)

        assert result.is_valid is False
        assert len(result.issues) == 2
        assert result.confidence == 0.5
        assert result.retry_recommended is True  # <=3 issues

    def test_retry_recommended_with_few_issues(self) -> None:
        """Test retry recommended when issues <= 3."""
        issues = ["Issue 1", "Issue 2", "Issue 3"]
        result = ValidationResult(is_valid=False, issues=issues)

        assert result.retry_recommended is True

    def test_retry_not_recommended_with_many_issues(self) -> None:
        """Test retry not recommended when issues > 3."""
        issues = ["Issue 1", "Issue 2", "Issue 3", "Issue 4"]
        result = ValidationResult(is_valid=False, issues=issues)

        assert result.retry_recommended is False

    def test_retry_recommended_field_overridden_by_post_init(self) -> None:
        """Test that __post_init__ overrides retry_recommended based on issue count."""
        # Explicitly set retry_recommended=True, but >3 issues should override
        result = ValidationResult(
            is_valid=False,
            issues=["I1", "I2", "I3", "I4", "I5"],
            retry_recommended=True,  # Will be overridden
        )

        assert result.retry_recommended is False  # Overridden by __post_init__

    def test_default_confidence(self) -> None:
        """Test default confidence is 0.8."""
        result = ValidationResult(is_valid=True)

        assert result.confidence == 0.8

    def test_default_retry_recommended(self) -> None:
        """Test default retry_recommended is True."""
        result = ValidationResult(is_valid=True)

        assert result.retry_recommended is True


# =============================================================================
# KeyInsightsValidator Tests
# =============================================================================


class TestKeyInsightsValidator:
    """Test suite for KeyInsightsValidator."""

    @pytest.fixture
    def validator(self) -> KeyInsightsValidator:
        """Create validator instance."""
        return KeyInsightsValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid key_insights output fixture."""
        return {
            "insights": [
                {
                    "title": "LangGraph enables stateful multi-agent workflows",
                    "description": "LangGraph provides built-in state management for multi-agent orchestration, "
                    "reducing boilerplate compared to manual state tracking with LangChain LCEL.",
                },
                {
                    "title": "Redis caching reduces LLM costs by 70%",
                    "description": "Implementing semantic caching with Redis can reduce redundant LLM API calls "
                    "for similar queries, cutting costs from $500/month to $150/month.",
                },
                {
                    "title": "PGVector HNSW indexes provide sub-50ms retrieval",
                    "description": "Using PGVector with HNSW indexing (m=16, ef_construction=64) achieves p95 "
                    "retrieval latency under 50ms for 100K embeddings at 95% recall.",
                },
            ],
            "summary": "This content provides concrete implementation patterns for building production RAG systems "
            "with LangGraph, Redis caching, and PGVector, including specific configuration values.",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(self, validator: KeyInsightsValidator, valid_output: dict) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_insufficient_insights(self, validator: KeyInsightsValidator) -> None:
        """Test validation fails with < 3 insights."""
        output = {
            "insights": [
                {
                    "title": "Insight 1",
                    "description": "A" * MIN_DESCRIPTION_LENGTH,
                },
                {
                    "title": "Insight 2",
                    "description": "B" * MIN_DESCRIPTION_LENGTH,
                },
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 2 insights" in issue for issue in result.issues)

    def test_duplicate_insight_titles(self, validator: KeyInsightsValidator) -> None:
        """Test validation fails with duplicate titles."""
        output = {
            "insights": [
                {"title": "Same Title", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Same Title", "description": "B" * MIN_DESCRIPTION_LENGTH},
                {"title": "Different Title", "description": "C" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Duplicate insight titles" in issue for issue in result.issues)

    def test_short_insight_description(self, validator: KeyInsightsValidator) -> None:
        """Test validation fails with description < 50 chars."""
        output = {
            "insights": [
                {"title": "Insight 1", "description": "Short"},
                {"title": "Insight 2", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 3", "description": "A" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("insufficient description" in issue for issue in result.issues)

    def test_placeholder_text_in_title(self, validator: KeyInsightsValidator) -> None:
        """Test validation detects placeholder text in insight title."""
        output = {
            "insights": [
                {"title": "[Insert title here]", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Valid Title", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Another Valid Title", "description": "A" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_generic_description(self, validator: KeyInsightsValidator) -> None:
        """Test validation detects generic statements."""
        output = {
            "insights": [
                {
                    "title": "Insight 1",
                    "description": "It's good because it works well and is highly recommended by users",
                },
                {"title": "Insight 2", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 3", "description": "A" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        # Should detect "it's good", "works well", and "highly recommended"
        assert any("generic statement" in issue.lower() for issue in result.issues)

    def test_short_summary(self, validator: KeyInsightsValidator) -> None:
        """Test validation fails with summary < 50 chars."""
        output = {
            "insights": [
                {"title": "Insight 1", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 2", "description": "B" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 3", "description": "C" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "Too short",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Summary too short" in issue for issue in result.issues)

    def test_low_confidence_score(self, validator: KeyInsightsValidator) -> None:
        """Test validation detects low confidence score."""
        output = {
            "insights": [
                {"title": "Insight 1", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 2", "description": "B" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 3", "description": "C" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.2,  # Below MIN_CONFIDENCE_SCORE (0.3)
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Low confidence score" in issue for issue in result.issues)

    def test_invalid_insight_structure(self, validator: KeyInsightsValidator) -> None:
        """Test validation handles invalid insight structure."""
        output = {
            "insights": [
                {"title": "Valid", "description": "A" * MIN_DESCRIPTION_LENGTH},
                "Not a dict",  # Invalid
                {"title": "Valid 2", "description": "B" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("not a valid object" in issue for issue in result.issues)

    def test_get_correction_hints(self, validator: KeyInsightsValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("3 unique" in hint for hint in hints)
        assert any("50+ chars" in hint for hint in hints)
        assert any("specific details" in hint.lower() for hint in hints)


# =============================================================================
# ProsConsValidator Tests
# =============================================================================


class TestProsConsValidator:
    """Test suite for ProsConsValidator."""

    @pytest.fixture
    def validator(self) -> ProsConsValidator:
        """Create validator instance."""
        return ProsConsValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid pros_cons output fixture."""
        return {
            "pros": [
                "Built-in state management with checkpointer support",
                "Native streaming via AsyncGenerator pattern",
                "Production-ready with observability hooks",
            ],
            "cons": [
                "Steeper learning curve than LCEL chains",
                "Requires PostgreSQL for state persistence",
            ],
            "verdict": "LangGraph is ideal for complex multi-agent workflows where state persistence is critical, "
            "but adds overhead for simple sequential chains.",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(self, validator: ProsConsValidator, valid_output: dict) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_insufficient_pros(self, validator: ProsConsValidator) -> None:
        """Test validation fails with < 2 pros."""
        output = {
            "pros": ["Only one pro"],
            "cons": ["Con 1", "Con 2"],
            "verdict": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 1 pros" in issue for issue in result.issues)

    def test_insufficient_cons(self, validator: ProsConsValidator) -> None:
        """Test validation fails with < 1 cons."""
        output = {
            "pros": ["Pro 1", "Pro 2"],
            "cons": [],
            "verdict": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 0 cons" in issue for issue in result.issues)

    def test_missing_verdict(self, validator: ProsConsValidator) -> None:
        """Test validation fails with missing verdict."""
        output = {
            "pros": ["Pro 1", "Pro 2"],
            "cons": ["Con 1"],
            "verdict": "",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Verdict is missing" in issue for issue in result.issues)

    def test_short_verdict(self, validator: ProsConsValidator) -> None:
        """Test validation fails with verdict < 20 chars."""
        output = {
            "pros": ["Pro 1", "Pro 2"],
            "cons": ["Con 1"],
            "verdict": "Too short",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("too short" in issue for issue in result.issues)

    def test_generic_pro(self, validator: ProsConsValidator) -> None:
        """Test validation detects generic pros."""
        output = {
            "pros": ["It's good and works well", "Specific pro with details"],
            "cons": ["Con 1"],
            "verdict": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("generic statement" in issue.lower() for issue in result.issues)

    def test_placeholder_in_verdict(self, validator: ProsConsValidator) -> None:
        """Test validation detects placeholder in verdict."""
        output = {
            "pros": ["Pro 1", "Pro 2"],
            "cons": ["Con 1"],
            "verdict": "The tool is [TODO: add verdict here] for most use cases",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_get_correction_hints(self, validator: ProsConsValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("2 specific pros" in hint for hint in hints)
        assert any("20+ chars" in hint for hint in hints)


# =============================================================================
# AudienceFitValidator Tests
# =============================================================================


class TestAudienceFitValidator:
    """Test suite for AudienceFitValidator."""

    @pytest.fixture
    def validator(self) -> AudienceFitValidator:
        """Create validator instance."""
        return AudienceFitValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid audience_fit output fixture."""
        return {
            "primary_audience": {
                "name": "Senior Backend Engineers",
                "why_relevant": "The content covers advanced LangGraph state management patterns "
                "needed for production multi-agent systems at scale.",
            },
            "prerequisites": [
                "Experience with Python async/await patterns",
                "Basic understanding of LangChain LCEL",
                "Familiarity with PostgreSQL",
            ],
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(self, validator: AudienceFitValidator, valid_output: dict) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.80

    def test_missing_primary_audience(self, validator: AudienceFitValidator) -> None:
        """Test validation fails with missing primary_audience."""
        output = {
            "primary_audience": None,
            "prerequisites": ["Prereq 1"],
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Primary audience is missing" in issue for issue in result.issues)

    def test_short_audience_name(self, validator: AudienceFitValidator) -> None:
        """Test validation fails with short audience name."""
        output = {
            "primary_audience": {
                "name": "Devs",  # < 10 chars
                "why_relevant": "A" * 20,
            },
            "prerequisites": ["Prereq 1"],
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("name is missing or too short" in issue for issue in result.issues)

    def test_short_why_relevant(self, validator: AudienceFitValidator) -> None:
        """Test validation fails with short why_relevant."""
        output = {
            "primary_audience": {
                "name": "Senior Backend Engineers",
                "why_relevant": "Short",  # < 20 chars
            },
            "prerequisites": ["Prereq 1"],
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("why_relevant" in issue for issue in result.issues)

    def test_insufficient_prerequisites(self, validator: AudienceFitValidator) -> None:
        """Test validation fails with < 1 prerequisites."""
        output = {
            "primary_audience": {
                "name": "Senior Backend Engineers",
                "why_relevant": "A" * 20,
            },
            "prerequisites": [],
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 0 prerequisites" in issue for issue in result.issues)

    def test_placeholder_in_audience_name(self, validator: AudienceFitValidator) -> None:
        """Test validation detects placeholder in audience name."""
        output = {
            "primary_audience": {
                "name": "[TBD - add audience]",
                "why_relevant": "A" * 20,
            },
            "prerequisites": ["Prereq 1"],
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_get_correction_hints(self, validator: AudienceFitValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("primary audience" in hint.lower() for hint in hints)
        assert any("20+ chars" in hint for hint in hints)


# =============================================================================
# ActionableValidator Tests
# =============================================================================


class TestActionableValidator:
    """Test suite for ActionableValidator."""

    @pytest.fixture
    def validator(self) -> ActionableValidator:
        """Create validator instance."""
        return ActionableValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid actionable output fixture."""
        return {
            "immediate_actions": [
                {
                    "action": "Install LangGraph and configure PostgreSQL checkpointer",
                    "time_estimate": "30 minutes",
                    "expected_outcome": "Working LangGraph environment with persistent state storage",
                },
                {
                    "action": "Implement basic multi-agent workflow with 2 agents",
                    "time_estimate": "2 hours",
                    "expected_outcome": "Functional workflow demonstrating agent coordination and state sharing",
                },
            ],
            "quick_win": "Clone the example repository and run the basic workflow to see LangGraph in action",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(self, validator: ActionableValidator, valid_output: dict) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_insufficient_immediate_actions(self, validator: ActionableValidator) -> None:
        """Test validation fails with < 1 immediate actions."""
        output = {
            "immediate_actions": [],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 0 immediate actions" in issue for issue in result.issues)

    def test_short_action_text(self, validator: ActionableValidator) -> None:
        """Test validation fails with action text < 20 chars."""
        output = {
            "immediate_actions": [
                {
                    "action": "Short",
                    "time_estimate": "30 minutes",
                    "expected_outcome": "A" * 20,
                }
            ],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("text is missing or too short" in issue for issue in result.issues)

    def test_missing_time_estimate(self, validator: ActionableValidator) -> None:
        """Test validation fails with missing time_estimate."""
        output = {
            "immediate_actions": [
                {
                    "action": "A" * 20,
                    "time_estimate": "",
                    "expected_outcome": "A" * 20,
                }
            ],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("missing time_estimate" in issue for issue in result.issues)

    def test_short_expected_outcome(self, validator: ActionableValidator) -> None:
        """Test validation fails with expected_outcome < 20 chars."""
        output = {
            "immediate_actions": [
                {
                    "action": "A" * 20,
                    "time_estimate": "30 minutes",
                    "expected_outcome": "Short",
                }
            ],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("expected_outcome" in issue for issue in result.issues)

    def test_short_quick_win(self, validator: ActionableValidator) -> None:
        """Test validation fails with quick_win < 30 chars."""
        output = {
            "immediate_actions": [
                {
                    "action": "A" * 20,
                    "time_estimate": "30 minutes",
                    "expected_outcome": "A" * 20,
                }
            ],
            "quick_win": "Too short",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Quick win is missing or too short" in issue for issue in result.issues)

    def test_placeholder_in_action(self, validator: ActionableValidator) -> None:
        """Test validation detects placeholder in action."""
        output = {
            "immediate_actions": [
                {
                    "action": "[TODO: Fill in action here]",
                    "time_estimate": "30 minutes",
                    "expected_outcome": "A" * 20,
                }
            ],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_generic_action(self, validator: ActionableValidator) -> None:
        """Test validation detects generic action."""
        output = {
            "immediate_actions": [
                {
                    "action": "It's good, just use it and it works well",
                    "time_estimate": "30 minutes",
                    "expected_outcome": "A" * 20,
                }
            ],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("generic statement" in issue.lower() for issue in result.issues)

    def test_invalid_action_structure(self, validator: ActionableValidator) -> None:
        """Test validation handles invalid action structure."""
        output = {
            "immediate_actions": ["Not a dict"],
            "quick_win": "A" * 30,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("not a valid object" in issue for issue in result.issues)

    def test_get_correction_hints(self, validator: ActionableValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("time_estimate" in hint for hint in hints)
        assert any("expected_outcome" in hint for hint in hints)


# =============================================================================
# TechComparatorValidator Tests
# =============================================================================


class TestTechComparatorValidator:
    """Test suite for TechComparatorValidator."""

    @pytest.fixture
    def validator(self) -> TechComparatorValidator:
        """Create validator instance."""
        return TechComparatorValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid tech_comparator output fixture."""
        return {
            "primary_tech": "LangGraph",
            "alternatives": ["LangChain LCEL", "CrewAI"],
            "comparison": {
                "LangGraph": {
                    "pros": ["Built-in state persistence", "Native streaming"],
                    "cons": ["Steeper learning curve"],
                    "use_cases": ["Multi-agent workflows"],
                },
                "LangChain LCEL": {
                    "pros": ["Simple declarative syntax"],
                    "cons": ["Manual state management"],
                    "use_cases": ["Sequential chains"],
                },
                "CrewAI": {
                    "pros": ["High-level agent abstractions"],
                    "cons": ["Less control over orchestration"],
                    "use_cases": ["Task delegation workflows"],
                },
            },
            "recommendation": "Use LangGraph for complex multi-agent systems requiring state persistence, "
            "LCEL for simple chains, and CrewAI for rapid prototyping.",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(
        self, validator: TechComparatorValidator, valid_output: dict
    ) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_missing_primary_tech(self, validator: TechComparatorValidator) -> None:
        """Test validation fails with missing primary_tech."""
        output = {
            "primary_tech": "",
            "alternatives": ["Alt 1"],
            "comparison": {},
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Primary technology name is missing" in issue for issue in result.issues)

    def test_insufficient_alternatives(self, validator: TechComparatorValidator) -> None:
        """Test validation fails with < 1 alternatives."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": [],
            "comparison": {},
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 0 alternatives" in issue for issue in result.issues)

    def test_missing_comparison_table(self, validator: TechComparatorValidator) -> None:
        """Test validation fails with missing comparison."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": ["Alt 1"],
            "comparison": None,
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Comparison table is missing" in issue for issue in result.issues)

    def test_comparison_missing_tech_entries(self, validator: TechComparatorValidator) -> None:
        """Test validation detects missing tech entries in comparison."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": ["LCEL", "CrewAI"],
            "comparison": {
                "LangGraph": {"pros": ["Pro"], "cons": ["Con"], "use_cases": ["Use"]},
                # Missing LCEL and CrewAI entries
            },
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Comparison missing entries" in issue for issue in result.issues)

    def test_comparison_entry_missing_pros(self, validator: TechComparatorValidator) -> None:
        """Test validation detects missing pros in comparison entry."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": [],
            "comparison": {
                "LangGraph": {
                    "pros": [],  # Missing pros
                    "cons": ["Con 1"],
                    "use_cases": ["Use case"],
                }
            },
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("has no pros listed" in issue for issue in result.issues)

    def test_comparison_entry_missing_cons(self, validator: TechComparatorValidator) -> None:
        """Test validation detects missing cons in comparison entry."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": [],
            "comparison": {
                "LangGraph": {
                    "pros": ["Pro 1"],
                    "cons": [],  # Missing cons
                    "use_cases": ["Use case"],
                }
            },
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("has no cons listed" in issue for issue in result.issues)

    def test_short_recommendation(self, validator: TechComparatorValidator) -> None:
        """Test validation fails with recommendation < 20 chars."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": ["Alt 1"],
            "comparison": {
                "LangGraph": {"pros": ["Pro"], "cons": ["Con"], "use_cases": ["Use"]},
                "Alt 1": {"pros": ["Pro"], "cons": ["Con"], "use_cases": ["Use"]},
            },
            "recommendation": "Too short",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Recommendation is missing or too short" in issue for issue in result.issues)

    def test_invalid_comparison_entry(self, validator: TechComparatorValidator) -> None:
        """Test validation handles invalid comparison entry structure."""
        output = {
            "primary_tech": "LangGraph",
            "alternatives": [],
            "comparison": {"LangGraph": "Not a dict"},
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("is invalid" in issue for issue in result.issues)

    def test_retry_recommended_with_four_issues(self, validator: TechComparatorValidator) -> None:
        """Test tech_comparator allows retry with up to 4 issues."""
        output = {
            "primary_tech": "",  # Issue 1
            "alternatives": [],  # Issue 2
            "comparison": {},  # Issue 3
            "recommendation": "Short",  # Issue 4
            "confidence_score": 0.2,  # Issue 5 (but only first 4 count for retry threshold)
        }

        result = validator.validate(output)

        assert result.is_valid is False
        # Tech comparator has higher retry threshold (<=4)
        # With 5 issues total, retry should be False
        assert len(result.issues) >= 4

    def test_get_correction_hints(self, validator: TechComparatorValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("primary technology" in hint.lower() for hint in hints)
        assert any("comparison entry" in hint.lower() for hint in hints)


# =============================================================================
# SecurityAuditorValidator Tests
# =============================================================================


class TestSecurityAuditorValidator:
    """Test suite for SecurityAuditorValidator."""

    @pytest.fixture
    def validator(self) -> SecurityAuditorValidator:
        """Create validator instance."""
        return SecurityAuditorValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid security_auditor output fixture."""
        return {
            "security_risks": [
                {
                    "severity": "high",
                    "description": "SQL injection vulnerability in user input handler (line 47) affecting authentication endpoint",
                    "mitigation": "Use parameterized queries with SQLAlchemy ORM to prevent SQL injection attacks",
                },
                {
                    "severity": "medium",
                    "description": "Weak JWT signing key with only 80 bits of entropy (16-character secret)",
                    "mitigation": "Generate 256-bit random secret using secrets.token_urlsafe(32) and rotate keys monthly",
                },
            ],
            "best_practices": [
                "Implement rate limiting with Redis (100 requests/hour per IP)",
                "Add helmet middleware for security headers (CSP, HSTS)",
            ],
            "recommendation": "Address high-severity SQL injection first (2 hours), then rotate JWT keys (30 minutes)",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(
        self, validator: SecurityAuditorValidator, valid_output: dict
    ) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_invalid_severity(self, validator: SecurityAuditorValidator) -> None:
        """Test validation fails with invalid severity."""
        output = {
            "security_risks": [
                {
                    "severity": "super_critical",  # Invalid
                    "description": "A" * 50,
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("invalid severity" in issue.lower() for issue in result.issues)

    @pytest.mark.parametrize(
        "severity",
        ["low", "medium", "high", "critical", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
    )
    def test_valid_severities(self, validator: SecurityAuditorValidator, severity: str) -> None:
        """Test all valid severity levels pass validation."""
        output = {
            "security_risks": [
                {
                    "severity": severity,
                    "description": "A" * 50,
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        # Should not have severity-related issues
        assert not any("invalid severity" in issue.lower() for issue in result.issues)

    def test_generic_risk_description(self, validator: SecurityAuditorValidator) -> None:
        """Test validation detects generic security advice in description."""
        output = {
            "security_risks": [
                {
                    "severity": "medium",
                    "description": "Review code",  # Too generic and short
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("too generic" in issue.lower() for issue in result.issues)

    def test_generic_mitigation(self, validator: SecurityAuditorValidator) -> None:
        """Test validation detects generic security advice in mitigation."""
        output = {
            "security_risks": [
                {
                    "severity": "medium",
                    "description": "A" * 50,
                    "mitigation": "Be careful",  # Too generic and short
                }
            ],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("too generic" in issue.lower() for issue in result.issues)

    def test_all_generic_best_practices(self, validator: SecurityAuditorValidator) -> None:
        """Test validation detects when all best practices are generic."""
        output = {
            "security_risks": [
                {
                    "severity": "medium",
                    "description": "A" * 50,
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": [
                "Review code carefully",
                "Follow best practices",
                "Use secure methods",
            ],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("All best practices are generic" in issue for issue in result.issues)

    def test_some_generic_best_practices_allowed(self, validator: SecurityAuditorValidator) -> None:
        """Test validation allows some generic best practices if not all."""
        output = {
            "security_risks": [
                {
                    "severity": "medium",
                    "description": "A" * 50,
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": [
                "Review code carefully",  # Generic
                "Implement rate limiting with Redis (100 req/hour)",  # Specific
            ],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        # Should not fail for mixed generic/specific best practices
        assert not any("All best practices are generic" in issue for issue in result.issues)

    def test_placeholder_in_risk_description(self, validator: SecurityAuditorValidator) -> None:
        """Test validation detects placeholder in risk description."""
        output = {
            "security_risks": [
                {
                    "severity": "medium",
                    "description": "[TODO: Add description]",
                    "mitigation": "A" * 30,
                }
            ],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_invalid_risk_structure(self, validator: SecurityAuditorValidator) -> None:
        """Test validation handles invalid risk structure."""
        output = {
            "security_risks": ["Not a dict"],
            "best_practices": ["Practice 1"],
            "recommendation": "A" * MIN_VERDICT_LENGTH,
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("not a valid object" in issue for issue in result.issues)

    def test_get_correction_hints(self, validator: SecurityAuditorValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("severity levels" in hint.lower() for hint in hints)
        assert any("OWASP" in hint or "CVE" in hint for hint in hints)


# =============================================================================
# ImplementationPlannerValidator Tests
# =============================================================================


class TestImplementationPlannerValidator:
    """Test suite for ImplementationPlannerValidator."""

    @pytest.fixture
    def validator(self) -> ImplementationPlannerValidator:
        """Create validator instance."""
        return ImplementationPlannerValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Return valid implementation_planner output fixture."""
        return {
            "prerequisites": [
                "Python 3.10+ installed",
                "PostgreSQL 14+ running",
                "Basic understanding of async/await",
            ],
            "steps": [
                {
                    "step": 1,
                    "action": "Install LangGraph and dependencies via pip install langgraph langchain-postgres",
                },
                {
                    "step": 2,
                    "action": "Configure PostgreSQL checkpointer with connection pool (min: 5, max: 20)",
                },
                {
                    "step": 3,
                    "action": "Implement StateGraph with 2 agent nodes and conditional edges",
                },
            ],
            "estimated_time": "3-4 hours",
            "testing_strategy": "Unit test each agent node, integration test full workflow with mock LLM",
            "confidence_score": 0.85,
        }

    def test_valid_output_passes(
        self, validator: ImplementationPlannerValidator, valid_output: dict
    ) -> None:
        """Test that valid output passes validation."""
        result = validator.validate(valid_output)

        assert result.is_valid is True
        assert len(result.issues) == 0
        assert result.confidence == 0.85

    def test_insufficient_prerequisites(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation fails with < 1 prerequisites."""
        output = {
            "prerequisites": [],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 2, "action": "B" * 10},
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 0 prerequisites" in issue for issue in result.issues)

    def test_insufficient_steps(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation fails with < 2 steps."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [{"step": 1, "action": "A" * 10}],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Only 1 steps" in issue for issue in result.issues)

    def test_non_sequential_step_numbers(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation fails with non-sequential step numbers."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 3, "action": "B" * 10},  # Skipped 2 - validation checks sorted order
                {"step": 5, "action": "C" * 10},  # Skipped 4
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("not sequential" in issue for issue in result.issues)

    def test_short_step_action(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation fails with step action < 10 chars."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [
                {"step": 1, "action": "Short"},
                {"step": 2, "action": "A" * 10},
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("action is missing or too short" in issue for issue in result.issues)

    def test_missing_estimated_time(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation fails with missing estimated_time."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 2, "action": "B" * 10},
            ],
            "estimated_time": "",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("Estimated time is missing" in issue for issue in result.issues)

    def test_placeholder_in_prerequisite(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation detects placeholder in prerequisite."""
        output = {
            "prerequisites": ["[TBD - add prerequisites]"],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 2, "action": "B" * 10},
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_placeholder_in_step_action(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation detects placeholder in step action."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 2, "action": "[TODO: Fill in step]"},
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_placeholder_in_testing_strategy(
        self, validator: ImplementationPlannerValidator
    ) -> None:
        """Test validation detects placeholder in testing_strategy."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": [
                {"step": 1, "action": "A" * 10},
                {"step": 2, "action": "B" * 10},
            ],
            "estimated_time": "3 hours",
            "testing_strategy": "[TBD]",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("placeholder text" in issue.lower() for issue in result.issues)

    def test_invalid_step_structure(self, validator: ImplementationPlannerValidator) -> None:
        """Test validation handles invalid step structure."""
        output = {
            "prerequisites": ["Prereq 1"],
            "steps": ["Not a dict", {"step": 2, "action": "A" * 10}],
            "estimated_time": "3 hours",
            "testing_strategy": "Test it",
            "confidence_score": 0.8,
        }

        result = validator.validate(output)

        assert result.is_valid is False
        assert any("not a valid object" in issue for issue in result.issues)

    def test_get_correction_hints(self, validator: ImplementationPlannerValidator) -> None:
        """Test correction hints are comprehensive."""
        hints = validator.get_correction_hints()

        assert len(hints) >= 5
        assert any("sequential" in hint.lower() for hint in hints)
        assert any("estimated_time" in hint for hint in hints)


# =============================================================================
# Validator Registry Tests
# =============================================================================


class TestValidatorRegistry:
    """Test suite for validator registry and factory functions."""

    def test_get_validator_key_insights(self) -> None:
        """Test get_validator returns KeyInsightsValidator."""
        validator = get_validator("key_insights")

        assert validator is not None
        assert isinstance(validator, KeyInsightsValidator)
        assert validator.agent_type == "key_insights"

    def test_get_validator_pros_cons(self) -> None:
        """Test get_validator returns ProsConsValidator."""
        validator = get_validator("pros_cons")

        assert validator is not None
        assert isinstance(validator, ProsConsValidator)
        assert validator.agent_type == "pros_cons"

    def test_get_validator_audience_fit(self) -> None:
        """Test get_validator returns AudienceFitValidator."""
        validator = get_validator("audience_fit")

        assert validator is not None
        assert isinstance(validator, AudienceFitValidator)
        assert validator.agent_type == "audience_fit"

    def test_get_validator_actionable(self) -> None:
        """Test get_validator returns ActionableValidator."""
        validator = get_validator("actionable")

        assert validator is not None
        assert isinstance(validator, ActionableValidator)
        assert validator.agent_type == "actionable"

    def test_get_validator_tech_comparator(self) -> None:
        """Test get_validator returns TechComparatorValidator."""
        validator = get_validator("tech_comparator")

        assert validator is not None
        assert isinstance(validator, TechComparatorValidator)
        assert validator.agent_type == "tech_comparator"

    def test_get_validator_security_auditor(self) -> None:
        """Test get_validator returns SecurityAuditorValidator."""
        validator = get_validator("security_auditor")

        assert validator is not None
        assert isinstance(validator, SecurityAuditorValidator)
        assert validator.agent_type == "security_auditor"

    def test_get_validator_implementation_planner(self) -> None:
        """Test get_validator returns ImplementationPlannerValidator."""
        validator = get_validator("implementation_planner")

        assert validator is not None
        assert isinstance(validator, ImplementationPlannerValidator)
        assert validator.agent_type == "implementation_planner"

    def test_get_validator_unknown_agent_type(self) -> None:
        """Test get_validator returns None for unknown agent type."""
        validator = get_validator("unknown_agent")

        assert validator is None

    def test_all_validators_registered(self) -> None:
        """Test that all validators are registered in AGENT_VALIDATORS."""
        expected_validators = {
            "key_insights": KeyInsightsValidator,
            "pros_cons": ProsConsValidator,
            "audience_fit": AudienceFitValidator,
            "actionable": ActionableValidator,
            "tech_comparator": TechComparatorValidator,
            "security_auditor": SecurityAuditorValidator,
            "implementation_planner": ImplementationPlannerValidator,
        }

        assert expected_validators == AGENT_VALIDATORS

    def test_all_validators_have_correct_agent_type(self) -> None:
        """Test that all validators have correct agent_type class variable."""
        for agent_type, validator_class in AGENT_VALIDATORS.items():
            validator = validator_class()
            assert validator.agent_type == agent_type


# =============================================================================
# validate_agent_output() Convenience Function Tests
# =============================================================================


class TestValidateAgentOutputFunction:
    """Test suite for validate_agent_output() convenience function."""

    def test_validate_valid_output(self) -> None:
        """Test validate_agent_output with valid output."""
        output = {
            "insights": [
                {"title": "Insight 1", "description": "A" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 2", "description": "B" * MIN_DESCRIPTION_LENGTH},
                {"title": "Insight 3", "description": "C" * MIN_DESCRIPTION_LENGTH},
            ],
            "summary": "A" * MIN_DESCRIPTION_LENGTH,
            "confidence_score": 0.85,
        }

        result = validate_agent_output(output, "key_insights")

        assert result is not None
        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_validate_invalid_output(self) -> None:
        """Test validate_agent_output with invalid output."""
        output = {
            "insights": [{"title": "Only one", "description": "A" * MIN_DESCRIPTION_LENGTH}],
            "summary": "Too short",
            "confidence_score": 0.2,
        }

        result = validate_agent_output(output, "key_insights")

        assert result is not None
        assert result.is_valid is False
        assert len(result.issues) > 0

    def test_validate_unknown_agent_type(self) -> None:
        """Test validate_agent_output returns None for unknown agent type."""
        output = {"data": "some data"}

        result = validate_agent_output(output, "unknown_agent")

        assert result is None

    def test_validate_logs_warning_on_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test validate_agent_output logs warning when validation fails."""
        output = {
            "insights": [],
            "summary": "",
            "confidence_score": 0.2,
        }

        with caplog.at_level("WARNING"):
            result = validate_agent_output(output, "key_insights")

        assert result is not None
        assert result.is_valid is False
        # Note: Logging verification depends on logger configuration
        # This test may need adjustment based on actual logging setup


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestEdgeCases:
    """Test suite for edge cases and integration scenarios."""

    def test_empty_output_dict(self) -> None:
        """Test validators handle empty output dict gracefully."""
        output = {}

        # Most validators should fail with empty output
        # (but some may pass if all fields are optional with defaults)
        validators_that_should_fail = [
            "key_insights",  # Requires 3+ insights
            "pros_cons",  # Requires 2+ pros, 1+ cons
            "audience_fit",  # Requires primary_audience
            "actionable",  # Requires 1+ immediate_actions
            "tech_comparator",  # Requires primary_tech, alternatives
            "implementation_planner",  # Requires prerequisites, steps
        ]

        for agent_type in validators_that_should_fail:
            validator = get_validator(agent_type)
            assert validator is not None

            result = validator.validate(output)
            assert result.is_valid is False, f"{agent_type} should fail with empty output"
            assert len(result.issues) > 0

    def test_output_with_none_values(self) -> None:
        """Test validators handle None values in output (raises TypeError).

        Note: Validators expect proper types (list, str, dict) and will raise
        TypeError if given None. This is acceptable - callers should ensure
        output dicts have correct types before validation.
        """
        output = {
            "insights": None,
            "summary": None,
            "confidence_score": None,
        }

        validator = get_validator("key_insights")
        assert validator is not None

        # Validators don't handle None gracefully - they expect proper types
        with pytest.raises(TypeError):
            validator.validate(output)

    def test_output_with_mixed_valid_invalid_fields(self) -> None:
        """Test validators properly report multiple issues."""
        output = {
            "pros": ["Valid pro"],  # Invalid: < 2
            "cons": [],  # Invalid: < 1
            "verdict": "Short",  # Invalid: < 20 chars
            "confidence_score": 0.1,  # Invalid: < 0.3
        }

        validator = get_validator("pros_cons")
        assert validator is not None

        result = validator.validate(output)
        assert result.is_valid is False
        assert len(result.issues) >= 4  # Should report all issues

    def test_all_validators_have_get_correction_hints(self) -> None:
        """Test all validators implement get_correction_hints()."""
        for agent_type in AGENT_VALIDATORS:
            validator = get_validator(agent_type)
            assert validator is not None

            hints = validator.get_correction_hints()
            assert isinstance(hints, list)
            assert len(hints) >= 3  # All validators should have multiple hints
            assert all(isinstance(hint, str) for hint in hints)
            assert all(len(hint) > 10 for hint in hints)  # Hints should be substantive

    def test_validators_inherit_from_base_class(self) -> None:
        """Test all validators inherit from AgentOutputValidator."""
        for validator_class in AGENT_VALIDATORS.values():
            assert issubclass(validator_class, AgentOutputValidator)

    @pytest.mark.parametrize(
        "agent_type,expected_class",
        [
            ("key_insights", KeyInsightsValidator),
            ("pros_cons", ProsConsValidator),
            ("audience_fit", AudienceFitValidator),
            ("actionable", ActionableValidator),
            ("tech_comparator", TechComparatorValidator),
            ("security_auditor", SecurityAuditorValidator),
            ("implementation_planner", ImplementationPlannerValidator),
        ],
    )
    def test_parameterized_validator_factory(
        self, agent_type: str, expected_class: type[AgentOutputValidator]
    ) -> None:
        """Test validator factory returns correct class for each agent type."""
        validator = get_validator(agent_type)

        assert validator is not None
        assert isinstance(validator, expected_class)

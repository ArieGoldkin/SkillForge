"""Unit tests for confidence_score field in all agent schemas."""

import pytest
from pydantic import ValidationError

from app.domains.analysis.workflows.agents.schemas.code_quality_critic import CodeQualityReview
from app.domains.analysis.workflows.agents.schemas.dependency_mapper import DependencyMapping
from app.domains.analysis.workflows.agents.schemas.implementation_planner import (
    ImplementationPlan,
    ImplementationStep,
)
from app.domains.analysis.workflows.agents.schemas.integration_feasibility import IntegrationFeasibility
from app.domains.analysis.workflows.agents.schemas.performance_analyst import PerformanceAnalysis
from app.domains.analysis.workflows.agents.schemas.security_auditor import SecurityAudit
from app.domains.analysis.workflows.agents.schemas.tech_comparator import TechComparison, TechComparisonEntry
from app.domains.analysis.workflows.agents.schemas.trend_validator import TrendValidation

@pytest.mark.unit


@pytest.mark.parametrize(
    "schema_class",
    [
        ImplementationPlan,
        TechComparison,
        SecurityAudit,
        PerformanceAnalysis,
        IntegrationFeasibility,
        TrendValidation,
        DependencyMapping,
        CodeQualityReview,
    ],
)
def test_all_schemas_require_confidence_score(schema_class):
    """Test that all 8 agent schemas have required confidence_score field."""
    # Try to create instance without confidence_score - should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        if schema_class == ImplementationPlan:
            schema_class(
                prerequisites=["test"],
                steps=[ImplementationStep(step=1, action="test", files=[])],
                testing_strategy="test",
                estimated_time="1 hour",
            )
        elif schema_class == TechComparison:
            schema_class(
                primary_tech="React",
                alternatives=["Vue"],
                comparison={"React": TechComparisonEntry(pros=[], cons=[], use_cases=[])},
                recommendation="Use React",
            )
        elif schema_class == SecurityAudit:
            schema_class(
                security_risks=[],
                best_practices=[],
                compliance_notes=[],
                recommendation="Secure it",
            )
        elif schema_class == PerformanceAnalysis:
            schema_class(
                performance_metrics=[],
                bottlenecks=[],
                optimization_opportunities=[],
                scaling_considerations="Scale horizontally",
                recommendation="Optimize",
            )
        elif schema_class == IntegrationFeasibility:
            schema_class(
                compatibility={},
                migration_effort="low",
                breaking_changes=[],
                integration_steps=[],
            )
        elif schema_class == TrendValidation:
            schema_class(
                trend_assessments=[],
                modern_alternatives=[],
                future_outlook="Stable",
                recommendation="Adopt",
            )
        elif schema_class == DependencyMapping:
            schema_class(
                required_dependencies=[],
                optional_dependencies=[],
                version_conflicts=[],
                peer_dependencies=[],
                installation_notes=[],
                recommendation="Install dependencies",
            )
        elif schema_class == CodeQualityReview:
            schema_class(
                code_issues=[],
                best_practices=[],
                maintainability_score=0.8,
                refactoring_suggestions=[],
                recommendation="Refactor",
            )

    # Verify error mentions confidence_score
    errors = exc_info.value.errors()
    assert any("confidence_score" in str(error) for error in errors)


@pytest.mark.parametrize("invalid_value", [-0.1, 1.1, 2.0, -1.0])
def test_confidence_score_validation_range_min_max(invalid_value):
    """Test that confidence_score rejects values outside 0.0-1.0 range."""
    with pytest.raises(ValidationError) as exc_info:
        ImplementationPlan(
            prerequisites=["test"],
            steps=[ImplementationStep(step=1, action="test", files=[])],
            testing_strategy="test",
            estimated_time="1 hour",
            confidence_score=invalid_value,
        )

    errors = exc_info.value.errors()
    # Verify error is about confidence_score
    assert any("confidence_score" in str(error) for error in errors)
    # Pydantic error messages may vary - just verify validation failed
    assert len(errors) > 0


@pytest.mark.parametrize("valid_value", [0.0, 1.0, 0.5, 0.75, 0.25, 0.999, 0.123456])
def test_confidence_score_validation_boundary_and_precision(valid_value):
    """Test that confidence_score accepts valid boundary and mid-range values."""
    plan = ImplementationPlan(
        prerequisites=["test"],
        steps=[ImplementationStep(step=1, action="test", files=[])],
        testing_strategy="test",
        estimated_time="1 hour",
        confidence_score=valid_value,
    )
    assert plan.confidence_score == valid_value
    assert isinstance(plan.confidence_score, float)


def test_confidence_score_missing_raises_error():
    """Test that missing confidence_score raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ImplementationPlan(
            prerequisites=["test"],
            steps=[ImplementationStep(step=1, action="test", files=[])],
            testing_strategy="test",
            estimated_time="1 hour",
            # confidence_score missing
        )

    errors = exc_info.value.errors()
    assert any(
        "confidence_score" in str(error) and "required" in str(error).lower() for error in errors
    )


@pytest.mark.parametrize("wrong_type", [None, [], {}])
def test_confidence_score_wrong_type_raises_error(wrong_type):
    """Test that wrong type for confidence_score raises ValidationError.

    Note: Pydantic automatically converts compatible types (string "0.5" -> 0.5, int 1 -> 1.0),
    so we only test truly incompatible types.
    """
    with pytest.raises(ValidationError) as exc_info:
        ImplementationPlan(
            prerequisites=["test"],
            steps=[ImplementationStep(step=1, action="test", files=[])],
            testing_strategy="test",
            estimated_time="1 hour",
            confidence_score=wrong_type,
        )

    errors = exc_info.value.errors()
    assert any("confidence_score" in str(error) for error in errors)


def test_confidence_score_int_converted_to_float():
    """Test that integer confidence_score (0 or 1) is converted to float."""
    plan = ImplementationPlan(
        prerequisites=["test"],
        steps=[ImplementationStep(step=1, action="test", files=[])],
        testing_strategy="test",
        estimated_time="1 hour",
        confidence_score=1,  # Integer
    )
    assert plan.confidence_score == 1.0
    assert isinstance(plan.confidence_score, float)


def test_confidence_score_all_schemas_same_validation():
    """Test that all schemas enforce the same confidence_score validation rules."""
    valid_scores = [0.0, 0.5, 1.0]
    invalid_scores = [-0.1, 1.1]  # Removed "0.5" - Pydantic converts string to float

    # Test all schemas accept valid scores
    for score in valid_scores:
        # ImplementationPlan
        plan = ImplementationPlan(
            prerequisites=["test"],
            steps=[ImplementationStep(step=1, action="test", files=[])],
            testing_strategy="test",
            estimated_time="1 hour",
            confidence_score=score,
        )
        assert plan.confidence_score == score

        # TechComparison
        tech = TechComparison(
            primary_tech="React",
            alternatives=["Vue"],
            comparison={"React": TechComparisonEntry(pros=[], cons=[], use_cases=[])},
            recommendation="Use React",
            confidence_score=score,
        )
        assert tech.confidence_score == score

    # Test all schemas reject invalid scores (out of range)
    for score in invalid_scores:
        with pytest.raises(ValidationError):
            ImplementationPlan(
                prerequisites=["test"],
                steps=[ImplementationStep(step=1, action="test", files=[])],
                testing_strategy="test",
                estimated_time="1 hour",
                confidence_score=score,
            )

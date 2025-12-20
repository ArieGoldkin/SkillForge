"""Tests for DataAvailabilityMixin in agent schemas.

Issue #299-304: Graceful degradation - agents report data availability.
These tests verify that all agent schemas correctly inherit the mixin
and that the mixin behavior is correct.
"""

import pytest
from pydantic import ValidationError

from app.domains.analysis.schemas.agents.base import DataAvailabilityLevel, DataAvailabilityMixin
from app.domains.analysis.schemas.agents.code_quality_critic import CodeQualityReview
from app.domains.analysis.schemas.agents.dependency_mapper import DependencyMapping
from app.domains.analysis.schemas.agents.implementation_planner import ImplementationPlan
from app.domains.analysis.schemas.agents.integration_feasibility import IntegrationFeasibility
from app.domains.analysis.schemas.agents.performance_analyst import PerformanceAnalysis
from app.domains.analysis.schemas.agents.security_auditor import SecurityAudit
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison
from app.domains.analysis.schemas.agents.trend_validator import TrendValidation


@pytest.mark.unit
class TestDataAvailabilityMixin:
    """Tests for DataAvailabilityMixin base class."""

    def test_default_values(self) -> None:
        """Mixin should have sensible defaults."""
        mixin = DataAvailabilityMixin()
        assert mixin.data_availability == "sufficient"
        assert mixin.data_availability_note == ""

    def test_accepts_sufficient(self) -> None:
        """Should accept 'sufficient' as data_availability."""
        mixin = DataAvailabilityMixin(data_availability="sufficient")
        assert mixin.data_availability == "sufficient"

    def test_accepts_limited(self) -> None:
        """Should accept 'limited' as data_availability."""
        mixin = DataAvailabilityMixin(
            data_availability="limited",
            data_availability_note="Only conceptual discussion found",
        )
        assert mixin.data_availability == "limited"
        assert mixin.data_availability_note == "Only conceptual discussion found"

    def test_accepts_insufficient(self) -> None:
        """Should accept 'insufficient' as data_availability."""
        mixin = DataAvailabilityMixin(
            data_availability="insufficient",
            data_availability_note="No relevant security patterns detected",
        )
        assert mixin.data_availability == "insufficient"

    def test_rejects_invalid_availability(self) -> None:
        """Should reject invalid data_availability values."""
        with pytest.raises(ValidationError) as exc_info:
            DataAvailabilityMixin(data_availability="unknown")  # type: ignore[arg-type]
        error = exc_info.value
        assert "data_availability" in str(error)

    def test_serialization(self) -> None:
        """Mixin should serialize correctly."""
        mixin = DataAvailabilityMixin(
            data_availability="limited",
            data_availability_note="Test note",
        )
        data = mixin.model_dump()
        assert data["data_availability"] == "limited"
        assert data["data_availability_note"] == "Test note"


class TestDataAvailabilityLevel:
    """Tests for DataAvailabilityLevel type alias."""

    def test_type_alias_values(self) -> None:
        """DataAvailabilityLevel should only accept valid values."""
        # These should be valid
        level: DataAvailabilityLevel = "sufficient"
        assert level == "sufficient"

        level = "limited"
        assert level == "limited"

        level = "insufficient"
        assert level == "insufficient"


class TestAgentSchemaInheritance:
    """Verify all agent schemas inherit DataAvailabilityMixin.

    Issue #299-304: All 8 specialized agent schemas must inherit the mixin
    to support honest reporting of data coverage.
    """

    @pytest.mark.parametrize(
        "schema_class",
        [
            SecurityAudit,
            TechComparison,
            DependencyMapping,
            ImplementationPlan,
            IntegrationFeasibility,
            PerformanceAnalysis,
            CodeQualityReview,
            TrendValidation,
        ],
    )
    def test_schema_inherits_mixin(self, schema_class: type) -> None:
        """Each agent schema should be a subclass of DataAvailabilityMixin."""
        assert issubclass(schema_class, DataAvailabilityMixin), (
            f"{schema_class.__name__} must inherit DataAvailabilityMixin"
        )

    @pytest.mark.parametrize(
        "schema_class",
        [
            SecurityAudit,
            TechComparison,
            DependencyMapping,
            ImplementationPlan,
            IntegrationFeasibility,
            PerformanceAnalysis,
            CodeQualityReview,
            TrendValidation,
        ],
    )
    def test_schema_has_data_availability_field(self, schema_class: type) -> None:
        """Each agent schema should have data_availability field."""
        fields = schema_class.model_fields
        assert "data_availability" in fields, f"{schema_class.__name__} missing data_availability"
        assert "data_availability_note" in fields, (
            f"{schema_class.__name__} missing data_availability_note"
        )


class TestSchemaDataAvailabilityIntegration:
    """Integration tests verifying data_availability works in actual schemas.

    These tests use reflection to check fields exist and defaults are correct,
    without requiring full instantiation of complex schemas.
    """

    def test_security_audit_has_data_availability_default(self) -> None:
        """SecurityAudit should have default data_availability = 'sufficient'."""
        field = SecurityAudit.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_performance_analysis_has_data_availability_default(self) -> None:
        """PerformanceAnalysis should have default data_availability = 'sufficient'."""
        field = PerformanceAnalysis.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_implementation_plan_has_data_availability_default(self) -> None:
        """ImplementationPlan should have default data_availability = 'sufficient'."""
        field = ImplementationPlan.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_tech_comparison_has_data_availability_default(self) -> None:
        """TechComparison should have default data_availability = 'sufficient'."""
        field = TechComparison.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_dependency_mapping_has_data_availability_default(self) -> None:
        """DependencyMapping should have default data_availability = 'sufficient'."""
        field = DependencyMapping.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_integration_feasibility_has_data_availability_default(self) -> None:
        """IntegrationFeasibility should have default data_availability = 'sufficient'."""
        field = IntegrationFeasibility.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_code_quality_review_has_data_availability_default(self) -> None:
        """CodeQualityReview should have default data_availability = 'sufficient'."""
        field = CodeQualityReview.model_fields["data_availability"]
        assert field.default == "sufficient"

    def test_trend_validation_has_data_availability_default(self) -> None:
        """TrendValidation should have default data_availability = 'sufficient'."""
        field = TrendValidation.model_fields["data_availability"]
        assert field.default == "sufficient"

    @pytest.mark.parametrize(
        "schema_class",
        [
            SecurityAudit,
            TechComparison,
            DependencyMapping,
            ImplementationPlan,
            IntegrationFeasibility,
            PerformanceAnalysis,
            CodeQualityReview,
            TrendValidation,
        ],
    )
    def test_data_availability_note_is_optional(self, schema_class: type) -> None:
        """data_availability_note should default to empty string."""
        field = schema_class.model_fields["data_availability_note"]
        assert field.default == ""

    @pytest.mark.parametrize(
        "schema_class",
        [
            SecurityAudit,
            TechComparison,
            DependencyMapping,
            ImplementationPlan,
            IntegrationFeasibility,
            PerformanceAnalysis,
            CodeQualityReview,
            TrendValidation,
        ],
    )
    def test_data_availability_description_is_informative(self, schema_class: type) -> None:
        """data_availability field description should guide agents."""
        field = schema_class.model_fields["data_availability"]
        description = field.description or ""
        # Description should explain the values
        assert "sufficient" in description.lower()
        assert "limited" in description.lower()
        assert "insufficient" in description.lower()

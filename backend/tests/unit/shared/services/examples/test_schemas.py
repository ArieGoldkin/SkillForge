"""Unit tests for example selection schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.shared.services.examples.schemas import AgentExample, ExampleSelectionResult


@pytest.mark.unit
class TestAgentExample:
    """Tests for AgentExample Pydantic schema."""

    def test_valid_example_creation(self):
        """AgentExample validates and creates with valid data."""
        example_id = uuid.uuid4()
        example = AgentExample(
            id=example_id,
            agent_type="tech_comparator",
            input_summary="Comparing React vs Vue for state management",
            output_example={"comparison": "React uses Redux, Vue uses Vuex"},
            quality_score=0.95,
        )

        assert example.id == example_id
        assert example.agent_type == "tech_comparator"
        assert example.quality_score == 0.95
        assert example.output_example == {"comparison": "React uses Redux, Vue uses Vuex"}

    def test_quality_score_must_be_between_0_and_1(self):
        """AgentExample rejects quality_score outside [0, 1] range."""
        with pytest.raises(ValidationError) as exc_info:
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test",
                output_example={},
                quality_score=1.5,  # Invalid: > 1.0
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("quality_score",) for e in errors)

    def test_negative_quality_score_rejected(self):
        """AgentExample rejects negative quality_score."""
        with pytest.raises(ValidationError) as exc_info:
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test",
                output_example={},
                quality_score=-0.1,  # Invalid: < 0.0
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("quality_score",) for e in errors)

    def test_optional_fields_can_be_none(self):
        """AgentExample allows None for optional fields."""
        example = AgentExample(
            id=uuid.uuid4(),
            agent_type="tech_comparator",
            input_summary="Test input",
            output_example={"result": "test"},
            quality_score=0.8,
            input_content_preview=None,
            context_note=None,
            content_type=None,
            difficulty_level=None,
            similarity_distance=None,
        )

        assert example.input_content_preview is None
        assert example.context_note is None
        assert example.content_type is None
        assert example.difficulty_level is None
        assert example.similarity_distance is None

    def test_optional_fields_can_be_set(self):
        """AgentExample accepts optional field values."""
        example = AgentExample(
            id=uuid.uuid4(),
            agent_type="implementation_planner",
            input_summary="How to implement authentication",
            input_content_preview="JWT tokens vs session cookies...",
            output_example={"steps": ["Choose auth method", "Implement"]},
            context_note="Extracted from golden dataset",
            quality_score=0.9,
            content_type="tutorial",
            difficulty_level="intermediate",
            similarity_distance=0.15,
        )

        assert example.input_content_preview == "JWT tokens vs session cookies..."
        assert example.context_note == "Extracted from golden dataset"
        assert example.content_type == "tutorial"
        assert example.difficulty_level == "intermediate"
        assert example.similarity_distance == 0.15

    def test_from_attributes_mode_enabled(self):
        """AgentExample Config.from_attributes is enabled for ORM compatibility."""
        # This is tested implicitly when converting from SQLAlchemy models
        # The Config class should have from_attributes = True
        assert AgentExample.model_config["from_attributes"] is True


@pytest.mark.unit
class TestExampleSelectionResult:
    """Tests for ExampleSelectionResult schema."""

    def test_valid_selection_result(self):
        """ExampleSelectionResult validates with valid data."""
        examples = [
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test 1",
                output_example={},
                quality_score=0.9,
            ),
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test 2",
                output_example={},
                quality_score=0.85,
            ),
        ]

        result = ExampleSelectionResult(
            examples=examples,
            total_candidates=10,
            selection_strategy="semantic_similarity",
            avg_quality_score=0.875,
            avg_similarity_distance=0.12,
        )

        assert len(result.examples) == 2
        assert result.total_candidates == 10
        assert result.selection_strategy == "semantic_similarity"
        assert result.avg_quality_score == 0.875
        assert result.avg_similarity_distance == 0.12

    def test_empty_examples_list_allowed(self):
        """ExampleSelectionResult allows empty examples list (no results)."""
        result = ExampleSelectionResult(
            examples=[],
            total_candidates=0,
            selection_strategy="semantic_similarity",
            avg_quality_score=None,
            avg_similarity_distance=None,
        )

        assert result.examples == []
        assert result.total_candidates == 0
        assert result.avg_quality_score is None
        assert result.avg_similarity_distance is None

    def test_optional_metrics_can_be_none(self):
        """ExampleSelectionResult allows None for optional metric fields."""
        result = ExampleSelectionResult(
            examples=[],
            total_candidates=5,
            selection_strategy="quality_based",
            avg_quality_score=None,
            avg_similarity_distance=None,
        )

        assert result.avg_quality_score is None
        assert result.avg_similarity_distance is None

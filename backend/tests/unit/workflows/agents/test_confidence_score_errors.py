"""Unit tests for confidence_score error handling and edge cases."""

import pytest
from pydantic import ValidationError

from app.domains.analysis.workflows.agents.result_processing import process_agent_result
from app.domains.analysis.workflows.agents.schemas.implementation_planner import (

    ImplementationPlan,
    ImplementationStep,
)


@pytest.mark.asyncio
async def test_confidence_score_missing_validation_error():
    """Test that schema validation fails if confidence_score is missing."""
    with pytest.raises(ValidationError) as exc_info:
        ImplementationPlan(
            prerequisites=["test"],
            steps=[ImplementationStep(step=1, action="test", files=[])],
            testing_strategy="test",
            estimated_time="1 hour",
            # confidence_score missing - should raise ValidationError
        )

    errors = exc_info.value.errors()
    assert any("confidence_score" in str(error) for error in errors)
    assert any("required" in str(error).lower() for error in errors)


@pytest.mark.asyncio
async def test_confidence_score_out_of_range_validation_error():
    """Test that schema validation fails if confidence_score is out of range."""
    invalid_values = [-0.1, 1.1, 2.0, -1.0]

    for invalid_value in invalid_values:
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


@pytest.mark.asyncio
async def test_confidence_score_wrong_type_validation_error():
    """Test that schema validation fails if confidence_score has wrong type.

    Note: Pydantic automatically converts compatible types (string "0.5" -> 0.5),
    so we only test truly incompatible types.
    """
    wrong_types = [None, [], {}]  # Removed "0.5" and "high" - Pydantic converts strings

    for wrong_type in wrong_types:
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


@pytest.mark.asyncio
async def test_extraction_handles_missing_gracefully():
    """Test that extraction code handles missing confidence_score gracefully (backward compat).

    Even though schemas now require confidence_score, the extraction code should
    handle cases where it might be missing (defensive programming).
    """
    from unittest.mock import AsyncMock, patch

    findings = {
        "primary_tech": "React",
        # confidence_score missing (shouldn't happen with new schemas, but handle gracefully)
    }

    with (
        patch("app.domains.analysis.workflows.agents.base.save_agent_finding", new_callable=AsyncMock),
        patch("app.domains.analysis.workflows.agents.base.emit_agent_progress", new_callable=AsyncMock),
    ):
        result = await process_agent_result(
            findings=findings,
            analysis_id="test-id",
            agent_type="tech_comparator",
            session=AsyncMock(),
            start_time=0.0,
        )

        # Should not raise - returns None for confidence_score
        assert result is not None


@pytest.mark.asyncio
async def test_extraction_handles_invalid_type_gracefully():
    """Test that extraction handles invalid confidence_score type gracefully."""
    from unittest.mock import AsyncMock, patch

    findings = {
        "primary_tech": "React",
        "confidence_score": "high",  # Invalid type (string)
    }

    from uuid import uuid4

    with (
        patch(
            "app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock
        ) as mock_save,
        patch("app.domains.analysis.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock),
        patch("app.shared.services.messaging.sse_helpers.persist_progress_event_async", new_callable=AsyncMock),
    ):
        await process_agent_result(
            findings=findings,
            analysis_id=str(uuid4()),  # Use valid UUID
            agent_type="tech_comparator",
            session=AsyncMock(),
            start_time=0.0,
        )

        # Should handle gracefully - set to None
        assert mock_save.called, "save_agent_finding should have been called"
        call_kwargs = mock_save.call_args.kwargs
        assert call_kwargs["confidence_score"] is None
        # Invalid value should be removed from findings
        assert "confidence_score" not in call_kwargs["findings"]


@pytest.mark.asyncio
async def test_persistence_handles_null_gracefully():
    """Test that database persistence handles NULL confidence_score gracefully (backward compat).

    Even though schemas now require confidence_score, the database column accepts NULL
    for backward compatibility with old records.
    """
    from app.models.agent_finding import AgentFinding

    # Simulate old record with NULL confidence_score
    finding = AgentFinding(
        analysis_id="test-id",
        agent_type="tech_comparator",
        findings={"primary_tech": "React"},
        confidence_score=None,  # NULL - should be accepted
    )

    # Should not raise - NULL is valid for backward compatibility
    assert finding.confidence_score is None

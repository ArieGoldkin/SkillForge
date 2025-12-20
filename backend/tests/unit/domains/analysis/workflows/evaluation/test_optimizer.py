"""Unit tests for agent strategy optimizer."""

import pytest

from app.domains.analysis.workflows.evaluation.optimizer import optimize_agent_strategy


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optimize_agent_strategy_with_history() -> None:
    """Test optimizer analyzes evaluation history and suggests improvements."""
    evaluation_history = [
        {"quality_score": 0.6, "timestamp": "2024-01-01T00:00:00Z"},
        {"quality_score": 0.65, "timestamp": "2024-01-02T00:00:00Z"},
        {"quality_score": 0.55, "timestamp": "2024-01-03T00:00:00Z"},
    ]

    result = await optimize_agent_strategy("tech_comparator", evaluation_history)

    # Verify result structure
    assert "suggested_prompt_changes" in result
    assert "strategy_adjustments" in result
    assert "expected_improvement" in result

    # Verify types
    assert isinstance(result["suggested_prompt_changes"], list)
    assert isinstance(result["strategy_adjustments"], dict)
    assert isinstance(result["expected_improvement"], float)


@pytest.mark.asyncio
async def test_optimize_agent_strategy_no_history() -> None:
    """Test optimizer handles empty history gracefully."""
    result = await optimize_agent_strategy("tech_comparator", [])

    # Should return empty optimizations
    assert result["suggested_prompt_changes"] == []
    assert result["strategy_adjustments"] == {}
    assert result["expected_improvement"] == 0.0


@pytest.mark.asyncio
async def test_optimize_agent_strategy_low_scores() -> None:
    """Test optimizer suggests improvements for low average scores."""
    evaluation_history = [
        {"quality_score": 0.5, "timestamp": "2024-01-01T00:00:00Z"},
        {"quality_score": 0.4, "timestamp": "2024-01-02T00:00:00Z"},
        {"quality_score": 0.45, "timestamp": "2024-01-03T00:00:00Z"},
    ]

    result = await optimize_agent_strategy("tech_comparator", evaluation_history)

    # Low scores should trigger suggestions
    assert len(result["suggested_prompt_changes"]) > 0
    assert result["expected_improvement"] > 0.0


@pytest.mark.asyncio
async def test_optimize_agent_strategy_high_scores() -> None:
    """Test optimizer doesn't suggest changes for high scores."""
    evaluation_history = [
        {"quality_score": 0.9, "timestamp": "2024-01-01T00:00:00Z"},
        {"quality_score": 0.85, "timestamp": "2024-01-02T00:00:00Z"},
        {"quality_score": 0.88, "timestamp": "2024-01-03T00:00:00Z"},
    ]

    result = await optimize_agent_strategy("tech_comparator", evaluation_history)

    # High scores should not trigger suggestions
    assert len(result["suggested_prompt_changes"]) == 0
    assert result["expected_improvement"] == 0.0

"""Unit tests for skill level prompt utility."""

import pytest

from app.workflows.agents.skill_level_prompts import (
    SKILL_LEVEL_INSTRUCTIONS,
    get_skill_level_instructions,
)


def test_skill_level_instructions_dict_complete():
    """Test that all skill levels have instructions defined."""
    expected_levels = ["beginner", "intermediate", "expert"]
    assert set(SKILL_LEVEL_INSTRUCTIONS.keys()) == set(expected_levels)


def test_get_skill_level_instructions_beginner():
    """Test that beginner level returns valid instructions."""
    instructions = get_skill_level_instructions("beginner")

    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert "Beginner Developer" in instructions
    assert "Explain technical terms" in instructions


def test_get_skill_level_instructions_intermediate():
    """Test that intermediate level returns valid instructions."""
    instructions = get_skill_level_instructions("intermediate")

    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert "Intermediate Developer" in instructions
    assert "best practices" in instructions


def test_get_skill_level_instructions_expert():
    """Test that expert level returns valid instructions."""
    instructions = get_skill_level_instructions("expert")

    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert "Expert Developer" in instructions
    assert "edge cases" in instructions


def test_get_skill_level_instructions_all_levels():
    """Test that all skill levels return non-empty instructions."""
    for level in ["beginner", "intermediate", "expert"]:
        instructions = get_skill_level_instructions(level)
        assert isinstance(instructions, str)
        assert len(instructions) > 0
        assert f"{level.title()} Developer" in instructions


def test_get_skill_level_instructions_invalid():
    """Test that invalid skill level raises ValueError."""
    with pytest.raises(ValueError, match="Invalid skill_level: advanced"):
        get_skill_level_instructions("advanced")

    with pytest.raises(ValueError, match="Invalid skill_level: newbie"):
        get_skill_level_instructions("newbie")

    with pytest.raises(ValueError, match="Invalid skill_level"):
        get_skill_level_instructions("")


def test_skill_level_instructions_have_target_audience():
    """Test that all instructions include TARGET AUDIENCE marker."""
    for level, instructions in SKILL_LEVEL_INSTRUCTIONS.items():
        assert "TARGET AUDIENCE:" in instructions, f"{level} missing TARGET AUDIENCE"
        assert f"{level.title()} Developer" in instructions


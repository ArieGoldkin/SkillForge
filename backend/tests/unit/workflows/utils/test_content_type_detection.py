"""Unit tests for content type detection utilities."""

from app.workflows.utils.content_type_detection import (
    AGENT_CAPABILITIES,
    can_agent_process_content,
    detect_content_type,
    filter_agents_by_content_type,
)


def test_detect_content_type_code():
    """Test detection of code content."""
    code_content = """
import os
from typing import List

def hello_world():
    print("Hello, World!")
    """
    assert detect_content_type(code_content) == "code"


def test_detect_content_type_changelog():
    """Test detection of changelog content."""
    changelog_content = """
## [1.2.3] - 2024-01-15

### Added
- New feature X
- Feature Y

### Fixed
- Bug fix Z
"""
    assert detect_content_type(changelog_content) == "changelog"


def test_detect_content_type_documentation():
    """Test detection of documentation content."""
    doc_content = """
# API Reference

## Introduction
This is the API documentation.

### Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/users | Get users |
"""
    assert detect_content_type(doc_content) == "documentation"


def test_detect_content_type_with_hint():
    """Test detection respects content type hint when patterns match."""
    code_content = "def hello(): pass"
    assert detect_content_type(code_content, content_type_hint="code") == "code"


def test_can_agent_process_content():
    """Test agent capability checking."""
    # Code quality critic can only process code
    assert can_agent_process_content("code_quality_critic", "code") is True
    assert can_agent_process_content("code_quality_critic", "changelog") is False

    # Tech comparator can process multiple types
    assert can_agent_process_content("tech_comparator", "code") is True
    assert can_agent_process_content("tech_comparator", "changelog") is True
    assert can_agent_process_content("tech_comparator", "documentation") is True


def test_filter_agents_by_content_type():
    """Test filtering agents based on content type."""
    agent_names = ["code_quality_critic", "dependency_mapper", "tech_comparator"]
    filtered, skipped = filter_agents_by_content_type(agent_names, "changelog")

    # Code quality critic and dependency mapper should be skipped
    assert "code_quality_critic" in skipped
    assert "dependency_mapper" in skipped
    # Tech comparator should be included
    assert "tech_comparator" in filtered
    assert len(filtered) == 1
    assert len(skipped) == 2


def test_filter_agents_all_can_process():
    """Test filtering when all agents can process content type."""
    agent_names = ["tech_comparator", "trend_validator"]
    filtered, skipped = filter_agents_by_content_type(agent_names, "changelog")

    assert len(filtered) == 2
    assert len(skipped) == 0


def test_agent_capabilities_complete():
    """Test that all agents have capability mappings."""
    # Verify all expected agents are in the capabilities mapping
    expected_agents = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]

    for agent in expected_agents:
        assert agent in AGENT_CAPABILITIES
        assert isinstance(AGENT_CAPABILITIES[agent], list)
        assert len(AGENT_CAPABILITIES[agent]) > 0

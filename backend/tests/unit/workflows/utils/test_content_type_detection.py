"""Unit tests for content type detection utilities."""

from app.shared.workflows.utils.content_type_detection import (

@pytest.mark.unit
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
    # Need at least 3 changelog patterns to match (changelog_score >= 3)
    changelog_content = """
## [1.2.3] - 2024-01-15

### Added
- New feature X
- Feature Y

### Fixed
- Bug fix Z

## [1.2.4] - 2024-02-20

### Changed
- Updated feature Y

2024-03-01
- Removed deprecated feature
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
    # Need at least 2 code patterns to match with hint (code_score >= 2)
    code_content = """import os
from typing import List

def hello():
    pass

class Test:
    pass
"""
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


def test_dependency_mapper_can_process_article():
    """Test that dependency_mapper can process article content type."""
    # dependency_mapper should be able to extract dependency info from tutorials/articles
    assert can_agent_process_content("dependency_mapper", "article") is True


def test_dependency_mapper_can_process_documentation():
    """Test that dependency_mapper can process documentation content type."""
    # dependency_mapper should be able to extract dependency info from documentation
    assert can_agent_process_content("dependency_mapper", "documentation") is True


def test_dependency_mapper_can_process_code():
    """Test that dependency_mapper can still process code content type."""
    # dependency_mapper should still be able to process code
    assert can_agent_process_content("dependency_mapper", "code") is True


def test_filter_agents_dependency_mapper_with_article():
    """Test filtering agents with dependency_mapper and article content."""
    agent_names = ["dependency_mapper", "code_quality_critic", "tech_comparator"]
    filtered, skipped = filter_agents_by_content_type(agent_names, "article")

    # dependency_mapper should be included (can process article)
    assert "dependency_mapper" in filtered
    # code_quality_critic should be skipped (only processes code)
    assert "code_quality_critic" in skipped
    # tech_comparator should be included (can process article)
    assert "tech_comparator" in filtered
    assert len(filtered) == 2
    assert len(skipped) == 1


def test_filter_agents_dependency_mapper_with_documentation():
    """Test filtering agents with dependency_mapper and documentation content."""
    agent_names = ["dependency_mapper", "code_quality_critic", "implementation_planner"]
    filtered, skipped = filter_agents_by_content_type(agent_names, "documentation")

    # dependency_mapper should be included (can process documentation)
    assert "dependency_mapper" in filtered
    # code_quality_critic should be skipped (only processes code)
    assert "code_quality_critic" in skipped
    # implementation_planner should be included (can process documentation)
    assert "implementation_planner" in filtered
    assert len(filtered) == 2
    assert len(skipped) == 1


def test_detect_content_type_tutorial_patterns():
    """Test that tutorial-specific patterns are detected as documentation."""
    # Tutorial with "getting started" pattern
    tutorial_content = """
    # Getting Started with FastAPI

    ## Installation
    To install FastAPI, run:
    pip install fastapi

    ## Step-by-Step Guide
    1. Create a new project
    2. Install dependencies
    """
    # Should detect as documentation (has markdown headers, pip install, step-by-step)
    assert detect_content_type(tutorial_content) == "documentation"

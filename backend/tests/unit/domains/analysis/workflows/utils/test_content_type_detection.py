"""Unit tests for content type detection utilities."""

from app.shared.workflows.utils.content_type_detection import (
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


# =============================================================================
# Issue #490: News Content Type Tests
# =============================================================================


def test_detect_content_type_news_announcement():
    """Test detection of news/announcement content (Issue #490)."""
    news_content = """
    OpenAI Announces GPT-5: The Next Generation of Language Models

    Today, OpenAI unveiled its latest breakthrough in artificial intelligence.
    The new model, now available to enterprise customers, represents a major
    leap forward in AI capabilities. This partnership with Microsoft enables
    global availability starting next month.
    """
    assert detect_content_type(news_content) == "news"


def test_detect_content_type_news_product_launch():
    """Test detection of product launch announcements."""
    launch_content = """
    Google Cloud Launches New AI Platform Features

    Google introduces enhanced machine learning capabilities
    with the launch of Vertex AI 2.0. The new version is now available
    and includes breakthrough performance improvements.
    """
    assert detect_content_type(launch_content) == "news"


def test_detect_content_type_news_partnership():
    """Test detection of partnership/acquisition news."""
    partnership_content = """
    Major Tech Acquisition Announced Today

    Company A has unveiled its acquisition of Company B, marking a significant
    partnership in the industry. The merger is now available for regulatory
    review and expected to close next quarter.
    """
    assert detect_content_type(partnership_content) == "news"


def test_detect_content_type_news_vs_technical_article():
    """Test that technical articles with code are NOT classified as news."""
    # Technical article with code should NOT be news
    article_with_code = """
    Announcing Our New Python Library

    Today we're launching our new library. Here's how to use it:

    ```python
    import new_library
    from new_library import Client

    client = Client()
    result = client.process()
    ```

    Step 1: Install the package
    Step 2: Configure your settings
    """
    # Should NOT be news because it has code patterns
    result = detect_content_type(article_with_code)
    assert result != "news"
    # Should be documentation (has code blocks, step-by-step)
    assert result == "documentation"


def test_detect_content_type_news_hint():
    """Test news content type hint validation."""
    news_content = """
    Breaking: Major AI announcement today.
    The company unveiled its new product, now available worldwide.
    """
    # With hint and matching patterns, should return news
    assert detect_content_type(news_content, content_type_hint="news") == "news"


def test_can_agent_process_news():
    """Test that only trend_validator and tech_comparator can process news."""
    # These should process news (Issue #490)
    assert can_agent_process_content("trend_validator", "news") is True
    assert can_agent_process_content("tech_comparator", "news") is True

    # These should NOT process news
    assert can_agent_process_content("security_auditor", "news") is False
    assert can_agent_process_content("implementation_planner", "news") is False
    assert can_agent_process_content("performance_analyst", "news") is False
    assert can_agent_process_content("code_quality_critic", "news") is False
    assert can_agent_process_content("dependency_mapper", "news") is False
    assert can_agent_process_content("integration_feasibility", "news") is False


def test_filter_agents_by_content_type_news():
    """Test filtering agents for news content - only 2 should pass."""
    all_agents = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]

    filtered, skipped = filter_agents_by_content_type(all_agents, "news")

    # Only 2 agents should be filtered (allowed to process news)
    assert len(filtered) == 2
    assert "trend_validator" in filtered
    assert "tech_comparator" in filtered

    # 6 agents should be skipped
    assert len(skipped) == 6
    assert "security_auditor" in skipped
    assert "implementation_planner" in skipped
    assert "performance_analyst" in skipped
    assert "code_quality_critic" in skipped
    assert "dependency_mapper" in skipped
    assert "integration_feasibility" in skipped


def test_agent_capabilities_includes_news():
    """Test that news is in AGENT_CAPABILITIES for exactly 2 agents."""
    agents_with_news = [agent for agent, types in AGENT_CAPABILITIES.items() if "news" in types]
    assert len(agents_with_news) == 2
    assert "trend_validator" in agents_with_news
    assert "tech_comparator" in agents_with_news

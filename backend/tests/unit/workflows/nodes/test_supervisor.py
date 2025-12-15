"""Unit tests for supervisor node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.nodes.supervisor import _get_content_for_supervisor, supervisor_route
from app.workflows.nodes.supervisor_schema import AgentSelection
from app.workflows.utils.import_detection import detect_code_patterns


@pytest.fixture
def mock_agent_selection():
    """Mock AgentSelection with selected agents.

    ISSUE #299-304: Updated to reflect minimum 3 agents requirement.
    """
    return AgentSelection(
        agents=["tech_comparator", "security_auditor", "implementation_planner"],
        reasoning="Tech content needs comparison and security analysis",
        confidence=0.9,
    )


@pytest.fixture
def mock_agent_selection_minimal():
    """Mock AgentSelection with minimal agents (3 agents - minimum enforced).

    ISSUE #299-304: Updated to reflect minimum 3 agents requirement.
    """
    return AgentSelection(
        agents=["implementation_planner", "dependency_mapper", "trend_validator"],
        reasoning="Simple content needs basic implementation guidance",
        confidence=0.7,
    )


def test_get_content_for_supervisor_small():
    """Test dynamic content sizing for small content (<5K)."""
    content = "x" * 3000
    result = _get_content_for_supervisor(content, "article")
    assert len(result) == 3000  # All content used


def test_get_content_for_supervisor_medium():
    """Test dynamic content sizing for medium content (5K-15K)."""
    content = "x" * 12000
    result = _get_content_for_supervisor(content, "article")
    assert len(result) == 10000  # Truncated to 10K


def test_get_content_for_supervisor_large():
    """Test dynamic content sizing for large content (15K+)."""
    content = "x" * 25000
    result = _get_content_for_supervisor(content, "article")
    # Should be 10K + 2K middle section + separator text
    assert len(result) > 10000
    assert len(result) <= 15000


def test_get_content_for_supervisor_very_large():
    """Test dynamic content sizing for very large content (>50K)."""
    content = "x" * 60000
    result = _get_content_for_supervisor(content, "article")
    assert len(result) == 12000  # Truncated to 12K


@pytest.mark.asyncio
async def test_supervisor_route_success(mock_agent_selection):
    """Test supervisor_route with successful agent selection."""
    # Mock the structured model that with_structured_output returns
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_agent_selection)

    # Mock the base model that get_chat_model returns
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        # Use "code" content type so both agents can process it
        # security_auditor can only process "code" and "documentation", not "article"
        result = await supervisor_route(
            content="import os\nfrom typing import List\n\ndef hello_world():\n    print('Hello, World!')",
            content_type="code",
            analysis_id="test-analysis-id",
        )

        # Verify supervisor decision structure
        assert "supervisor_decision" in result
        decision = result["supervisor_decision"]
        assert "agents" in decision
        assert "priority" in decision
        assert "reasoning" in decision
        assert "confidence" in decision

        # Verify agents were selected (all 3 from fixture + dependency_mapper)
        # Note: dependency_mapper should be auto-activated due to import statements
        assert len(decision["agents"]) >= 4, (
            f"Expected at least 4 agents (3 from fixture + auto-activated dependency_mapper), "
            f"got {len(decision['agents'])}: {decision['agents']}"
        )
        assert "tech_comparator" in decision["agents"]
        assert "security_auditor" in decision["agents"]
        assert "implementation_planner" in decision["agents"]
        # dependency_mapper should be auto-activated
        assert "dependency_mapper" in decision["agents"]
        assert len(decision["priority"]) == len(decision["agents"])
        assert decision["confidence"] == 0.9

        # Verify SSE events were emitted
        assert mock_emit.call_count >= 2  # Start and complete events
        start_call = mock_emit.call_args_list[0]
        assert start_call[1]["stage"] == "supervisor_routing"
        assert start_call[1]["status"] == "running"


@pytest.mark.asyncio
async def test_supervisor_route_minimal_agents_selected(mock_agent_selection_minimal):
    """Test supervisor_route enforces minimum 3 agents even when LLM selects only 1.

    ISSUE #299-304: This test verifies the fix that prevents poor artifact quality
    by ensuring at least 3 agents are always selected for diverse analysis.
    """
    # Mock the structured model that with_structured_output returns
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_agent_selection_minimal)

    # Mock the base model that get_chat_model returns
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        result = await supervisor_route(
            content="Simple content that needs basic implementation guidance.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Verify decision structure - MINIMUM 3 AGENTS enforced
        assert "supervisor_decision" in result
        decision = result["supervisor_decision"]
        # CHANGED: Minimum enforcement means exactly 3 agents from fixture
        assert len(decision["agents"]) == 3, (
            f"Expected 3 agents from fixture, got {len(decision['agents'])}: {decision['agents']}"
        )
        # All agents from fixture should be present
        assert "implementation_planner" in decision["agents"]
        assert "dependency_mapper" in decision["agents"]
        assert "trend_validator" in decision["agents"]
        assert len(decision["priority"]) == len(decision["agents"])
        assert decision["confidence"] == 0.7

        # Verify complete event was emitted with agent_count = 3
        complete_calls = [c for c in mock_emit.call_args_list if c[1].get("status") == "complete"]
        assert len(complete_calls) > 0
        complete_call = complete_calls[0]
        assert complete_call[1]["agent_count"] == 3


@pytest.mark.asyncio
async def test_supervisor_route_error_handling():
    """Test supervisor_route handles errors gracefully."""
    # Mock the structured model that with_structured_output returns
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(side_effect=Exception("Model invocation failed"))

    # Mock the base model that get_chat_model returns
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
        pytest.raises(Exception, match="Model invocation failed"),
    ):
        await supervisor_route(
            content="Test content",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Verify error event was emitted
        error_calls = [c for c in mock_emit.call_args_list if c[1].get("status") == "failed"]
        assert len(error_calls) > 0
        error_call = error_calls[0]
        assert error_call[1]["stage"] == "supervisor"
        assert "error" in error_call[1]


@pytest.mark.asyncio
async def test_supervisor_route_content_dynamic_sizing():
    """Test that content is dynamically sized based on length."""
    mock_selection = AgentSelection(
        agents=["tech_comparator", "implementation_planner", "dependency_mapper"],
        reasoning="Test",
        confidence=0.8,
    )
    # Mock the structured model that with_structured_output returns
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)

    # Mock the base model that get_chat_model returns
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Create content of different sizes
    small_content = "x" * 3000  # <5K: use all
    medium_content = "x" * 12000  # 5K-15K: use 10K
    large_content = "x" * 25000  # 15K+: use 12K-15K

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        # Test small content (uses all)
        await supervisor_route(
            content=small_content,
            content_type="article",
            analysis_id="test-small",
        )
        call_args = mock_structured_model.ainvoke.call_args[0][0]
        assert len(call_args) > 3000  # Includes prompt + all content

        # Test medium content (truncated to 10K)
        await supervisor_route(
            content=medium_content,
            content_type="article",
            analysis_id="test-medium",
        )
        call_args = mock_structured_model.ainvoke.call_args[0][0]
        # Should contain ~10K chars of content (plus prompt)
        assert "Content Type: article" in call_args


@pytest.mark.asyncio
async def test_supervisor_route_decision_structure(mock_agent_selection):
    """Test that supervisor decision has correct structure."""
    # Mock the structured model that with_structured_output returns
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_agent_selection)

    # Mock the base model that get_chat_model returns
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(
            content="Test content about React and security.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        decision = result["supervisor_decision"]
        assert isinstance(decision, dict)
        assert isinstance(decision["agents"], list)
        assert isinstance(decision["priority"], list)
        assert isinstance(decision["reasoning"], str)
        assert isinstance(decision["confidence"], float)
        assert len(decision["agents"]) == len(decision["priority"])
        # Priorities should match confidence
        assert all(p == decision["confidence"] for p in decision["priority"])
        assert decision["confidence"] == 0.9


@pytest.mark.asyncio
async def test_supervisor_auto_activates_dependency_mapper_with_imports():
    """Test supervisor auto-activates dependency_mapper when import statements detected."""
    # Mock agent selection without dependency_mapper
    mock_selection = AgentSelection(
        agents=["implementation_planner", "security_auditor", "performance_analyst"],
        reasoning="Simple tutorial content",
        confidence=0.8,
    )

    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content with import statements
    content_with_imports = """
    import fastapi
    from fastapi import FastAPI
    from typing import List

    app = FastAPI()
    """

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(
            content=content_with_imports,
            content_type="code",
            analysis_id="test-analysis-id",
        )

        decision = result["supervisor_decision"]
        # dependency_mapper should be auto-activated
        assert "dependency_mapper" in decision["agents"]
        assert "implementation_planner" in decision["agents"]
        assert (
            "auto-activated" in decision["reasoning"].lower()
            or "code patterns" in decision["reasoning"].lower()
        )


@pytest.mark.asyncio
async def test_supervisor_auto_activates_dependency_mapper_with_package_files():
    """Test supervisor auto-activates dependency_mapper when package files mentioned."""
    mock_selection = AgentSelection(
        agents=["tech_comparator", "implementation_planner", "performance_analyst"],
        reasoning="Framework comparison",
        confidence=0.85,
    )

    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content mentioning package files
    content_with_package = """
    Add dependencies to requirements.txt:
    fastapi==0.100.0
    uvicorn==0.23.0
    """

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(
            content=content_with_package,
            content_type="article",
            analysis_id="test-analysis-id",
        )

        decision = result["supervisor_decision"]
        # dependency_mapper should be auto-activated
        assert "dependency_mapper" in decision["agents"]


@pytest.mark.asyncio
async def test_supervisor_auto_activates_dependency_mapper_with_install_commands():
    """Test supervisor auto-activates dependency_mapper when install commands detected."""
    mock_selection = AgentSelection(
        agents=["implementation_planner", "security_auditor", "tech_comparator"],
        reasoning="Setup guide",
        confidence=0.9,
    )

    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content with installation commands
    content_with_install = """
    Install dependencies:
    pip install fastapi uvicorn
    npm install react react-dom
    """

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(
            content=content_with_install,
            content_type="article",
            analysis_id="test-analysis-id",
        )

        decision = result["supervisor_decision"]
        # dependency_mapper should be auto-activated
        assert "dependency_mapper" in decision["agents"]


def test_detect_code_patterns_utility():
    """Test import detection utility function."""
    # Test with imports
    content1 = "import fastapi\nfrom fastapi import FastAPI"
    patterns1 = detect_code_patterns(content1)
    assert patterns1["has_imports"] is True

    # Test with package files
    content2 = "Update requirements.txt with dependencies"
    patterns2 = detect_code_patterns(content2)
    assert patterns2["has_package_files"] is True

    # Test with install commands
    content3 = "Run: pip install fastapi"
    patterns3 = detect_code_patterns(content3)
    assert patterns3["has_install_commands"] is True

    # Test with frameworks
    content4 = "FastAPI is a modern framework"
    patterns4 = detect_code_patterns(content4)
    assert patterns4["has_frameworks"] is True


@pytest.mark.asyncio
async def test_supervisor_auto_activates_performance_analyst():
    """Test supervisor auto-activates performance_analyst when performance keywords detected.

    Issue #299-304: Content must have benchmark patterns (p99, latency metrics, req/sec)
    for performance_analyst to NOT be skipped by content signal filtering.
    """
    mock_selection = AgentSelection(
        agents=["implementation_planner", "security_auditor", "tech_comparator"],
        reasoning="Plan",
        confidence=0.8,
    )

    # Mock models
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content with performance keywords AND benchmark patterns (required for signal detection)
    content = """
    We need to optimize the asyncpg connection pool latency.
    Current metrics: p99 latency is 450ms, throughput is 1000 req/sec.
    Target: reduce p99 to <100ms while maintaining 2000 req/sec.
    """

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(content, "code", "test-id")
        agents = result["supervisor_decision"]["agents"]
        assert "performance_analyst" in agents


@pytest.mark.asyncio
async def test_supervisor_auto_activates_security_auditor():
    """Test supervisor auto-activates security_auditor when security keywords detected."""
    mock_selection = AgentSelection(
        agents=["implementation_planner", "security_auditor", "tech_comparator"],
        reasoning="Plan",
        confidence=0.8,
    )

    # Mock models
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content with security keywords
    content = "Use python-jose to decode the JWT token."

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(content, "code", "test-id")
        agents = result["supervisor_decision"]["agents"]
        assert "security_auditor" in agents
        assert (
            "security_indicators_detected" in str(result)
            or "security keywords" in result["supervisor_decision"]["reasoning"]
        )


@pytest.mark.asyncio
async def test_supervisor_auto_activates_tech_comparator():
    """Test supervisor auto-activates tech_comparator when comparison logic detected."""
    mock_selection = AgentSelection(
        agents=["implementation_planner", "security_auditor", "tech_comparator"],
        reasoning="Plan",
        confidence=0.8,
    )

    # Mock models
    mock_structured_model = MagicMock()
    mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
    mock_model = MagicMock()
    mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

    # Content with comparison indicators (FastAPI vs Django)
    content = "Should we migrate from Django to FastAPI for better performance?"

    with (
        patch("app.workflows.nodes.supervisor.get_chat_model", return_value=mock_model),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        result = await supervisor_route(content, "article", "test-id")
        agents = result["supervisor_decision"]["agents"]
        assert "tech_comparator" in agents
        assert (
            "comparison_indicators_detected" in str(result)
            or "comparison detected" in result["supervisor_decision"]["reasoning"]
        )

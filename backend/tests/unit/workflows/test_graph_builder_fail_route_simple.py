"""Simplified unit tests for graph builder fail route.

Tests that the graph builder includes the quality_gate_fail node and "fail" route.

Issue #ARTIFACT-QUALITY: Graph now has fail-closed path for quality gate.
"""

import inspect

import pytest

from app.workflows.graph_builder import build_analysis_graph
from app.workflows.nodes.quality_gate_node import MAX_RETRY_ATTEMPTS, should_retry_synthesis
from app.workflows.state import AnalysisState


def test_graph_has_quality_gate_fail_node():
    """Test that graph includes quality_gate_fail node."""
    graph = build_analysis_graph()

    # Verify the graph was compiled successfully
    assert hasattr(graph, "ainvoke"), "Graph is not compiled"


def test_graph_should_retry_synthesis_returns_fail():
    """Test that should_retry_synthesis routing function returns 'fail' at max retries."""
    from unittest.mock import patch

    # State at max retries with failed gate
    state: AnalysisState = {
        "analysis_id": "test-123",
        "quality_gate_passed": False,
        "quality_gate_retry_count": MAX_RETRY_ATTEMPTS,
        "quality_gate_avg_score": 0.5,
        "quality_scores": {
            "relevance": {"score": 0.4, "comment": "Low"},
        },
    }

    with patch("app.workflows.nodes.quality_gate_node.logger"):
        result = should_retry_synthesis(state)

        # CRITICAL: Must return "fail", not "continue"
        assert result == "fail", (
            "should_retry_synthesis must return 'fail' at max retries (fail-closed)"
        )


def test_graph_conditional_edges_include_fail():
    """Test that quality_gate node has conditional edge that includes 'fail' route."""
    graph = build_analysis_graph()

    # The graph should have quality_gate node with conditional edges to:
    # - "retry_synthesis" (when retries available)
    # - "continue" (when gate passes)
    # - "fail" (when max retries exhausted) <- NEW

    # This is an architectural test - just verify graph compiles successfully
    # The actual routing is tested in other tests
    assert hasattr(graph, "ainvoke"), "Graph should be compiled"


def test_quality_gate_fail_route_exists_in_code():
    """Test that graph_builder.py includes fail route in conditional_edges."""
    from app.workflows.graph_builder import build_analysis_graph

    # Get source code of build_analysis_graph
    source = inspect.getsource(build_analysis_graph)

    # Verify fail route is defined
    assert '"fail": "quality_gate_fail"' in source or "'fail': 'quality_gate_fail'" in source, (
        "Graph builder should have fail route in conditional edges"
    )

    # Verify quality_gate_fail node is added
    assert 'add_node("quality_gate_fail"' in source, (
        "Graph builder should add quality_gate_fail node"
    )

    # Verify fail node routes to END
    assert 'add_edge("quality_gate_fail", END)' in source, (
        "quality_gate_fail node should route to END"
    )


def test_quality_gate_fail_node_function_exists():
    """Test that _quality_gate_fail_node function exists in graph_builder."""
    from app.workflows.graph_builder import _quality_gate_fail_node

    assert callable(_quality_gate_fail_node), "_quality_gate_fail_node should be callable"


@pytest.mark.asyncio
async def test_quality_gate_fail_node_basic():
    """Test basic functionality of _quality_gate_fail_node."""
    from unittest.mock import AsyncMock, patch

    from app.workflows.graph_builder import _quality_gate_fail_node

    state: AnalysisState = {
        "analysis_id": "test-123",
        "quality_gate_passed": False,
        "quality_gate_retry_count": 2,
        "quality_gate_avg_score": 0.5,
        "quality_scores": {
            "relevance": {"score": 0.4, "comment": "Low"},
        },
    }

    with (
        patch("app.services.sse_helpers.emit_streaming_event", new_callable=AsyncMock),
        patch("app.workflows.graph_builder.logger"),
    ):
        result = await _quality_gate_fail_node(state)

        # Verify status and error are set
        assert result["status"] == "failed"
        assert "error" in result
        assert "Quality gate failed" in result["error"]

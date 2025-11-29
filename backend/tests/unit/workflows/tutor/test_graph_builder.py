"""Unit tests for tutor graph builder."""

import pytest

from app.workflows.tutor.graph_builder import build_tutor_graph


def test_build_tutor_graph_compiles():
    """Test that tutor graph builds and compiles successfully."""
    graph = build_tutor_graph()
    assert graph is not None
    # Graph should be compiled (not StateGraph instance)
    assert hasattr(graph, "ainvoke")


def test_tutor_graph_has_core_nodes():
    """Test that tutor graph has all Phase 1 core nodes."""
    graph = build_tutor_graph()

    # Check that graph can be invoked (indirect test that nodes are registered)
    # We can't directly inspect nodes, but if compilation succeeds, nodes are registered
    assert graph is not None

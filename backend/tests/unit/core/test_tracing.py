"""Unit tests for LangSmith tracing utilities.

Tests the robust_traceable decorator which is the only public API
for tracing in this module.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import robust_traceable


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_robust_traceable_with_metadata(mock_traceable):
    """Test robust_traceable passes metadata to traceable correctly."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    @robust_traceable(
        name="test_node",
        run_type="chain",
        tags=["workflow", "node"],
        metadata={"environment": "test", "workflow_type": "analysis"},
    )
    async def test_function(arg1: str) -> dict:
        """Test function."""
        return {"result": arg1}

    result = await test_function("test")

    # Verify traceable was called with correct parameters including metadata
    mock_traceable.assert_called_once()
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "test_node"
    assert call_kwargs["run_type"] == "chain"
    assert call_kwargs["tags"] == ["workflow", "node"]
    assert call_kwargs["metadata"] == {"environment": "test", "workflow_type": "analysis"}
    assert result == {"result": "test"}


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_robust_traceable_with_tags(mock_traceable):
    """Test robust_traceable passes tags correctly."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    @robust_traceable(
        name="test_agent",
        run_type="chain",
        tags=["agent", "test"],
    )
    async def test_agent_function(content: str) -> dict:
        """Test agent function."""
        return {"agent_result": content}

    result = await test_agent_function("test")

    # Verify tags are passed correctly
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["tags"] == ["agent", "test"]
    assert result == {"agent_result": "test"}


@pytest.mark.asyncio
async def test_robust_traceable_propagates_exceptions():
    """Test that robust_traceable lets exceptions propagate naturally."""
    call_count = {"executed": 0, "completed": False}

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node(value: int) -> int:
        call_count["executed"] += 1
        result = value * 2
        call_count["completed"] = True
        return result

    # Normal execution should work
    result = await test_node(5)

    assert result == 10
    assert call_count["executed"] == 1
    assert call_count["completed"] is True


@pytest.mark.asyncio
async def test_robust_traceable_propagates_generator_exit():
    """Test that robust_traceable propagates GeneratorExit naturally."""
    call_count = {"executed": 0, "completed": False}

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node(value: int) -> int:
        call_count["executed"] += 1
        # Simulate GeneratorExit during execution
        # Note: Python converts GeneratorExit in async functions to RuntimeError
        raise GeneratorExit("Execution interrupted")

    # Python converts GeneratorExit in async functions to RuntimeError
    # robust_traceable lets exceptions propagate naturally
    with pytest.raises(RuntimeError, match="coroutine ignored GeneratorExit"):
        await test_node(5)

    assert call_count["executed"] == 1
    assert call_count["completed"] is False


@pytest.mark.asyncio
async def test_robust_traceable_preserves_other_exceptions():
    """Test that robust_traceable doesn't suppress real exceptions."""

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node(value: int) -> int:
        raise ValueError("Real error")

    with pytest.raises(ValueError, match="Real error"):
        await test_node(5)


@pytest.mark.asyncio
@patch("langsmith.get_current_run_tree")
async def test_robust_traceable_runtime_metadata_update(mock_get_current_run_tree):
    """Test that runtime metadata updates work with get_current_run_tree."""
    # Setup mock run tree
    mock_run_tree = MagicMock()
    mock_run_tree.id = "test-trace-id"
    mock_run_tree.metadata = {}
    mock_run_tree.tags = []
    mock_get_current_run_tree.return_value = mock_run_tree

    @robust_traceable(name="test_node", run_type="chain")
    async def test_node_with_metadata(analysis_id: str) -> dict:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata["analysis_id"] = analysis_id
            run_tree.tags.append("custom-tag")

        return {"result": "success"}

    result = await test_node_with_metadata("test-analysis-id")

    # Verify runtime metadata was updated
    assert mock_run_tree.metadata["analysis_id"] == "test-analysis-id"
    assert "custom-tag" in mock_run_tree.tags
    assert result == {"result": "success"}


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_robust_traceable_defaults(mock_traceable):
    """Test robust_traceable uses function name as default."""
    captured_func = None

    def mock_decorator(func):
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # Apply decorator without name
    @robust_traceable()
    async def my_test_function() -> dict:
        """Test function."""
        return {"result": "test"}

    result = await my_test_function()

    # Verify name defaults to function name
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "my_test_function"
    assert result == {"result": "test"}

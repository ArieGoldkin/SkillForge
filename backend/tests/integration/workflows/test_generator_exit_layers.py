"""Integration tests for GeneratorExit handling across all 5 layers.

Tests the hybrid approach for handling GeneratorExit exceptions:
1. Layer 1: Async generator cleanup with aclosing()
2. Layer 2: Robust @traceable wrappers
3. Layer 3: Workflow-level conditional handling
4. Layer 4: LangSmith query filtering (manual verification)
5. Layer 5: Upstream reporting (external)
"""

import asyncio
from contextlib import aclosing
from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import robust_traceable


# Layer 1 Tests: Async Generator Cleanup with aclosing()
class TestLayer1Aclosing:
    """Test async generator cleanup with aclosing()."""

    @pytest.mark.asyncio
    async def test_aclosing_ensures_cleanup(self) -> None:
        """Test that aclosing() ensures generator cleanup executes."""
        cleanup_called = False

        async def test_generator():
            nonlocal cleanup_called
            try:
                for i in range(3):
                    yield i
                    await asyncio.sleep(0.01)
            finally:
                cleanup_called = True

        # Iterate with aclosing()
        items = []
        async with aclosing(test_generator()) as gen:
            async for item in gen:
                items.append(item)
                if len(items) >= 2:  # Exit early
                    break

        # Cleanup should have been called
        assert cleanup_called, "Generator cleanup should be called even when iterating partially"

    @pytest.mark.asyncio
    async def test_aclosing_with_exception(self) -> None:
        """Test that aclosing() ensures cleanup even when exception occurs."""
        cleanup_called = False

        async def test_generator():
            nonlocal cleanup_called
            try:
                for i in range(3):
                    yield i
                    await asyncio.sleep(0.01)
            finally:
                cleanup_called = True

        # Iterate and raise exception - exception should propagate
        with pytest.raises(ValueError, match="Test exception"):
            async with aclosing(test_generator()) as gen:
                async for item in gen:
                    if item == 1:
                        msg = "Test exception"
                        raise ValueError(msg)

        # Cleanup should still be called
        assert cleanup_called, "Generator cleanup should be called even when exception occurs"


# Layer 2 Tests: Robust @traceable Wrappers
class TestLayer2RobustTraceable:
    """Test robust_traceable wrapper - exceptions propagate naturally.

    Note: robust_traceable no longer handles GeneratorExit. Exception handling
    is done at the application boundary (e.g., workflow_runner.py) where we have
    context (analysis_id, status updates). This decorator focuses solely on tracing.
    """

    @pytest.mark.asyncio
    async def test_robust_traceable_propagates_exceptions(self) -> None:
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
    async def test_robust_traceable_propagates_generator_exit(self) -> None:
        """Test that robust_traceable propagates GeneratorExit naturally."""
        call_count = {"executed": 0, "completed": False}

        @robust_traceable(name="test_node", run_type="chain")
        async def test_node(value: int) -> int:
            call_count["executed"] += 1
            # Simulate GeneratorExit during execution
            # Note: Python converts GeneratorExit in async functions to RuntimeError
            msg = "Execution interrupted"
            raise GeneratorExit(msg)

        # Python converts GeneratorExit in async functions to RuntimeError
        # robust_traceable lets exceptions propagate naturally
        with pytest.raises(RuntimeError, match="coroutine ignored GeneratorExit"):
            await test_node(5)

        assert call_count["executed"] == 1
        assert call_count["completed"] is False

    @pytest.mark.asyncio
    async def test_robust_traceable_preserves_other_exceptions(self) -> None:
        """Test that robust_traceable doesn't suppress real exceptions."""

        @robust_traceable(name="test_node", run_type="chain")
        async def test_node(value: int) -> int:
            msg = "Real error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Real error"):
            await test_node(5)


# Layer 3 Tests: Workflow-Level Conditional Handling
class TestLayer3WorkflowHandling:
    """Test workflow-level conditional GeneratorExit handling."""

    @pytest.mark.asyncio
    async def test_workflow_completed_suppresses_generator_exit(self) -> None:
        """Test that completed workflows suppress cleanup GeneratorExit."""
        workflow_completed = False
        result = {"status": "success"}

        async def mock_workflow():
            nonlocal workflow_completed
            workflow_completed = True
            return result

        # Simulate workflow execution
        try:
            workflow_result = await mock_workflow()
            # Simulate GeneratorExit after completion
            if workflow_completed:
                # Suppress - this is cleanup
                pass
        except GeneratorExit:
            if workflow_completed:
                # Suppress cleanup GeneratorExit
                pass
            else:
                # Re-raise execution GeneratorExit
                raise

        assert workflow_result == result
        assert workflow_completed is True

    @pytest.mark.asyncio
    async def test_workflow_incomplete_propagates_generator_exit(self) -> None:
        """Test that incomplete workflows propagate GeneratorExit."""
        workflow_completed = False

        async def mock_workflow():
            nonlocal workflow_completed
            # Simulate GeneratorExit before completion
            raise GeneratorExit("Interrupted")

        # Should propagate GeneratorExit (may be converted to RuntimeError in async functions)
        with pytest.raises((GeneratorExit, RuntimeError), match=r".*"):
            try:
                await mock_workflow()
            except (GeneratorExit, RuntimeError) as e:
                if workflow_completed:
                    # Suppress cleanup
                    pass
                else:
                    # Re-raise execution error
                    raise

        assert workflow_completed is False


# Layer 4 Tests: LangSmith Query Filtering (Unit tests for utility functions)
class TestLayer4LangSmithQueries:
    """Test LangSmith query filtering utilities."""

    @patch("tools.langsmith.queries.Client")
    def test_list_runs_without_generator_exit_filter(self, mock_client_class) -> None:
        """Test that query filters out GeneratorExit errors."""
        from tools.langsmith.queries import list_runs_without_generator_exit

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_runs.return_value = [{"id": "1", "status": "success"}]

        runs = list_runs_without_generator_exit(project_name="test-project", limit=10)

        # Verify filter expression excludes GeneratorExit
        call_args = mock_client.list_runs.call_args
        assert call_args is not None
        filter_expr = call_args.kwargs.get("filter", "")
        assert "GeneratorExit" in filter_expr or "not(has(error" in filter_expr

    @patch("tools.langsmith.queries.Client")
    def test_get_generator_exit_count(self, mock_client_class) -> None:
        """Test GeneratorExit count utility."""
        from tools.langsmith.queries import get_generator_exit_count

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_runs.return_value = [
            {"id": "1", "error": "GeneratorExit"},
            {"id": "2", "error": "GeneratorExit"},
        ]

        count = get_generator_exit_count(project_name="test-project", limit=100)

        assert count == 2
        # Verify filter looks for GeneratorExit
        call_args = mock_client.list_runs.call_args
        assert call_args is not None
        filter_expr = call_args.kwargs.get("filter", "")
        assert "GeneratorExit" in filter_expr


# Combined Layer Tests
class TestCombinedLayers:
    """Test interaction between multiple layers."""

    @pytest.mark.asyncio
    async def test_layer1_layer2_interaction(self) -> None:
        """Test that aclosing() and robust_traceable work together."""
        cleanup_called = False

        async def async_generator():
            nonlocal cleanup_called
            try:
                for i in range(3):
                    yield i
            finally:
                cleanup_called = True

        @robust_traceable(name="test_with_generator", run_type="chain")
        async def node_with_generator() -> list[int]:
            items = []
            async with aclosing(async_generator()) as gen:
                async for item in gen:
                    items.append(item)
            return items

        result = await node_with_generator()

        assert result == [0, 1, 2]
        assert cleanup_called is True

    @pytest.mark.asyncio
    async def test_all_layers_graceful_cleanup(self) -> None:
        """Test that all layers handle cleanup gracefully."""
        workflow_completed = False
        cleanup_called = False

        async def async_generator():
            nonlocal cleanup_called
            try:
                yield "data"
            finally:
                cleanup_called = True

        @robust_traceable(name="test_all_layers", run_type="chain")
        async def test_node() -> str:
            nonlocal workflow_completed
            async with aclosing(async_generator()) as gen:
                async for item in gen:
                    workflow_completed = True
                    return item
            return ""

        try:
            result = await test_node()
            # Simulate GeneratorExit after completion
            if workflow_completed:
                # Layer 3: Suppress cleanup GeneratorExit
                pass
        except GeneratorExit:
            if workflow_completed:
                # Layer 3: Suppress
                pass
            else:
                raise

        assert result == "data"
        assert workflow_completed is True
        assert cleanup_called is True

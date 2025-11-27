"""Unit tests for LangSmith tracing utilities."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from app.core.tracing import trace_agent, trace_guardrail, trace_node


class MockSchema(BaseModel):
    """Mock Pydantic schema for testing."""

    field1: str
    field2: int


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_trace_node_decorator(mock_traceable):
    """Test trace_node decorator applies tracing correctly."""
    # Store the original function to call it later
    captured_func = None

    # Setup mock - traceable returns a decorator that wraps the function
    def mock_decorator(func):
        """Mock decorator that captures the function."""
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            """Mock wrapper that calls original function."""
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # Apply decorator
    @trace_node(name="test_node", run_type="tool", tags=["custom"])
    async def test_function(arg1: str) -> dict:
        """Test function."""
        return {"result": arg1}

    # Call decorated function
    result = await test_function("test")

    # Verify traceable was called with correct parameters
    mock_traceable.assert_called_once()
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "test_node"
    assert call_kwargs["run_type"] == "tool"
    assert "workflow" in call_kwargs["tags"]
    assert "node" in call_kwargs["tags"]
    assert "custom" in call_kwargs["tags"]
    assert result == {"result": "test"}


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_trace_agent_decorator(mock_traceable):
    """Test trace_agent decorator applies tracing correctly."""
    # Store the original function to call it later
    captured_func = None

    # Setup mock - traceable returns a decorator that wraps the function
    def mock_decorator(func):
        """Mock decorator that captures the function."""
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            """Mock wrapper that calls original function."""
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # Apply decorator
    @trace_agent(name="test_agent", tags=["custom_agent"])
    async def test_agent_function(content: str) -> dict:
        """Test agent function."""
        return {"agent_result": content}

    # Call decorated function
    result = await test_agent_function("test")

    # Verify traceable was called with correct parameters
    mock_traceable.assert_called_once()
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "test_agent"
    assert call_kwargs["run_type"] == "chain"
    assert "agent" in call_kwargs["tags"]
    assert "custom_agent" in call_kwargs["tags"]
    assert result == {"agent_result": "test"}


@pytest.mark.asyncio
@patch("app.core.tracing.RunTree")
async def test_trace_guardrail_success(mock_run_tree):
    """Test trace_guardrail with successful validation."""
    # Setup mock RunTree
    mock_run = MagicMock()
    mock_run.id = str(uuid4())
    mock_run_tree.return_value = mock_run

    # Validation function
    def validate_func(inputs: dict) -> MockSchema:
        """Validate inputs."""
        return MockSchema(**inputs)

    # Test successful validation
    inputs = {"field1": "test", "field2": 42}
    result = await trace_guardrail(
        name="validate_test",
        schema_name="MockSchema",
        inputs=inputs,
        validation_func=validate_func,
    )

    # Verify RunTree was created
    mock_run_tree.assert_called_once()
    call_kwargs = mock_run_tree.call_args.kwargs
    assert call_kwargs["name"] == "validate_test"
    assert call_kwargs["run_type"] == "tool"
    assert "guardrail" in call_kwargs["tags"]
    assert "validation" in call_kwargs["tags"]

    # Verify run lifecycle
    mock_run.post.assert_called_once()
    mock_run.end.assert_called_once()
    mock_run.patch.assert_called()

    # Verify result
    assert isinstance(result, MockSchema)
    assert result.field1 == "test"
    assert result.field2 == 42

    # Verify end was called with success outputs
    end_call = mock_run.end.call_args
    assert end_call.kwargs["outputs"]["validated"] is True
    assert end_call.kwargs["outputs"]["schema"] == "MockSchema"


@pytest.mark.asyncio
@patch("app.core.tracing.RunTree")
@patch("app.core.tracing.logger")
async def test_trace_guardrail_validation_failure(mock_logger, mock_run_tree):
    """Test trace_guardrail with validation failure."""
    # Setup mock RunTree
    mock_run = MagicMock()
    mock_run.id = str(uuid4())
    mock_run_tree.return_value = mock_run

    # Validation function that raises error
    def validate_func(inputs: dict) -> MockSchema:
        """Validate inputs - will fail."""
        raise ValidationError.from_exception_data(
            "MockSchema", [{"type": "missing", "loc": ("field1",), "msg": "Field required"}]
        )

    # Test validation failure
    inputs = {"field2": 42}  # Missing field1
    with pytest.raises(ValidationError):
        await trace_guardrail(
            name="validate_test",
            schema_name="MockSchema",
            inputs=inputs,
            validation_func=validate_func,
        )

    # Verify RunTree was created
    mock_run_tree.assert_called_once()

    # Verify run lifecycle
    mock_run.post.assert_called_once()
    mock_run.end.assert_called_once()
    mock_run.patch.assert_called()

    # Verify end was called with error
    end_call = mock_run.end.call_args
    assert "error" in end_call.kwargs
    assert end_call.kwargs["outputs"]["validated"] is False
    assert "error" in end_call.kwargs["outputs"]

    # Verify logger was called
    mock_logger.warning.assert_called_once()
    log_call = mock_logger.warning.call_args
    assert log_call.kwargs["schema_name"] == "MockSchema"
    assert "error" in log_call.kwargs


@pytest.mark.asyncio
@patch("app.core.tracing.RunTree")
async def test_trace_guardrail_with_parent_run(mock_run_tree):
    """Test trace_guardrail with parent RunTree."""
    # Setup parent run
    parent_run = MagicMock()
    parent_run.id = str(uuid4())

    # Setup mock RunTree
    mock_run = MagicMock()
    mock_run.id = str(uuid4())
    mock_run_tree.return_value = mock_run

    # Validation function
    def validate_func(inputs: dict) -> MockSchema:
        """Validate inputs."""
        return MockSchema(**inputs)

    # Test with parent run
    inputs = {"field1": "test", "field2": 42}
    await trace_guardrail(
        name="validate_test",
        schema_name="MockSchema",
        inputs=inputs,
        validation_func=validate_func,
        parent_run=parent_run,
    )

    # Verify parent_run_id was set
    call_kwargs = mock_run_tree.call_args.kwargs
    assert call_kwargs["parent_run_id"] == parent_run.id


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_trace_node_defaults(mock_traceable):
    """Test trace_node uses function name as default."""
    # Store the original function to call it later
    captured_func = None

    # Setup mock - traceable returns a decorator that wraps the function
    def mock_decorator(func):
        """Mock decorator that captures the function."""
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            """Mock wrapper that calls original function."""
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # Apply decorator without name
    @trace_node()
    async def my_test_function() -> dict:
        """Test function."""
        return {"result": "test"}

    # Call decorated function
    result = await my_test_function()

    # Verify name defaults to function name
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "my_test_function"
    assert result == {"result": "test"}


@pytest.mark.asyncio
@patch("app.core.tracing.traceable")
async def test_trace_agent_defaults(mock_traceable):
    """Test trace_agent uses function name as default."""
    # Store the original function to call it later
    captured_func = None

    # Setup mock - traceable returns a decorator that wraps the function
    def mock_decorator(func):
        """Mock decorator that captures the function."""
        nonlocal captured_func
        captured_func = func

        async def mock_wrapper(*args, **kwargs):
            """Mock wrapper that calls original function."""
            return await captured_func(*args, **kwargs)

        return mock_wrapper

    mock_traceable.return_value = mock_decorator

    # Apply decorator without name
    @trace_agent()
    async def my_agent_function() -> dict:
        """Test agent function."""
        return {"result": "test"}

    # Call decorated function
    result = await my_agent_function()

    # Verify name defaults to function name
    call_kwargs = mock_traceable.call_args.kwargs
    assert call_kwargs["name"] == "my_agent_function"
    assert result == {"result": "test"}

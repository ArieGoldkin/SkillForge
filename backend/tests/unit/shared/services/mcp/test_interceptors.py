"""Tests for MCP tool call interceptors.

Tests the chain-of-responsibility pattern interceptors that wrap MCP tool calls
to provide authentication, retry logic, result enrichment, and logging.

Test Coverage:
    - AuthInterceptor: Header injection based on server configuration
    - RetryInterceptor: Exponential backoff retry on transient failures
    - ResultEnrichmentInterceptor: Metadata logging for observability
    - LoggingInterceptor: Structured logging with Langfuse correlation
    - create_default_interceptors: Factory function for interceptor chain

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from app.shared.services.mcp.config import MCPServerConfig, MCPSettings, MCPTransport
from app.shared.services.mcp.exceptions import MCPConnectionError, MCPTimeoutError
from app.shared.services.mcp.interceptors import (
    AuthInterceptor,
    InterceptorConfig,
    LoggingInterceptor,
    ResultEnrichmentInterceptor,
    RetryInterceptor,
    create_default_interceptors,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable



# ============================================================================
# Test Fixtures
# ============================================================================


@dataclass
class MockToolCallResult:
    """Mock MCP tool call result for testing."""

    content: str
    success: bool = True


@pytest.fixture
def sample_request() -> MCPToolCallRequest:
    """Create a sample MCP tool call request for testing."""
    return MCPToolCallRequest(
        name="test_tool",
        args={"param1": "value1", "param2": 42},
        server_name="test_server",
        headers=None,
        runtime=None,
    )


@pytest.fixture
def sample_result() -> MockToolCallResult:
    """Create a sample MCP tool call result for testing."""
    return MockToolCallResult(content="Test result", success=True)


@pytest.fixture
def mock_handler(sample_result: MockToolCallResult) -> AsyncMock:
    """Create a mock handler that returns a successful result."""
    handler = AsyncMock()
    handler.return_value = sample_result
    return handler


@pytest.fixture
def mcp_settings() -> MCPSettings:
    """Create MCP settings for testing."""
    return MCPSettings(
        enabled=True,
        servers={
            "github": MCPServerConfig(
                name="github",
                transport=MCPTransport.STDIO,
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                headers={"Authorization": "Bearer github-token"},
                max_retries=3,
            ),
            "weather": MCPServerConfig(
                name="weather",
                transport=MCPTransport.STREAMABLE_HTTP,
                url="http://localhost:8000/mcp",
                headers={"X-API-Key": "weather-key"},
                max_retries=2,
            ),
            "no_auth_server": MCPServerConfig(
                name="no_auth_server",
                transport=MCPTransport.STDIO,
                command="python",
                args=["server.py"],
                max_retries=3,
            ),
        },
    )


# ============================================================================
# AuthInterceptor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_auth_interceptor_injects_headers_for_configured_server(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
    mcp_settings: MCPSettings,
) -> None:
    """Test that AuthInterceptor injects headers for servers with auth configured."""
    # Arrange
    request = sample_request
    request = request.override()  # Copy to avoid mutation
    request.server_name = "github"  # Server with auth headers

    interceptor = AuthInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, mock_handler)

    # Assert
    assert result == sample_result
    assert mock_handler.call_count == 1

    # Verify handler was called with modified request containing auth headers
    called_request: MCPToolCallRequest = mock_handler.call_args[0][0]
    assert called_request.headers == {"Authorization": "Bearer github-token"}


@pytest.mark.asyncio
async def test_auth_interceptor_merges_with_existing_headers(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
    mcp_settings: MCPSettings,
) -> None:
    """Test that AuthInterceptor merges auth headers with existing request headers."""
    # Arrange
    request = sample_request.override(
        headers={"Content-Type": "application/json", "X-Custom": "value"}
    )
    request.server_name = "weather"  # Server with auth headers

    interceptor = AuthInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, mock_handler)

    # Assert
    assert result == sample_result

    # Verify headers were merged (auth headers take precedence)
    called_request: MCPToolCallRequest = mock_handler.call_args[0][0]
    assert called_request.headers == {
        "Content-Type": "application/json",
        "X-Custom": "value",
        "X-API-Key": "weather-key",
    }


@pytest.mark.asyncio
async def test_auth_interceptor_passes_through_for_unconfigured_server(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
    mcp_settings: MCPSettings,
) -> None:
    """Test that AuthInterceptor passes through requests for servers without auth."""
    # Arrange
    request = sample_request.override()
    request.server_name = "no_auth_server"  # Server without auth headers

    interceptor = AuthInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, mock_handler)

    # Assert
    assert result == sample_result

    # Verify handler was called with original request (no modification)
    called_request: MCPToolCallRequest = mock_handler.call_args[0][0]
    assert called_request.headers is None


@pytest.mark.asyncio
async def test_auth_interceptor_passes_through_for_unknown_server(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
    mcp_settings: MCPSettings,
) -> None:
    """Test that AuthInterceptor passes through requests for unknown servers."""
    # Arrange
    request = sample_request.override()
    request.server_name = "unknown_server"  # Not in settings

    interceptor = AuthInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, mock_handler)

    # Assert
    assert result == sample_result

    # Verify handler was called with original request
    called_request: MCPToolCallRequest = mock_handler.call_args[0][0]
    assert called_request.headers is None


# ============================================================================
# RetryInterceptor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_retry_interceptor_succeeds_on_first_attempt(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor returns result on first successful attempt."""
    # Arrange
    interceptor = RetryInterceptor(mcp_settings)

    # Act
    result = await interceptor(sample_request, mock_handler)

    # Assert
    assert result == sample_result
    assert mock_handler.call_count == 1


@pytest.mark.asyncio
async def test_retry_interceptor_retries_on_connection_error(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor retries on MCPConnectionError."""
    # Arrange
    request = sample_request.override()
    request.server_name = "github"  # max_retries = 3

    # Fail twice, then succeed
    handler = AsyncMock()
    handler.side_effect = [
        MCPConnectionError("Connection failed", server_name="github"),
        MCPConnectionError("Connection failed", server_name="github"),
        sample_result,
    ]

    interceptor = RetryInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, handler)

    # Assert
    assert result == sample_result
    assert handler.call_count == 3  # 2 failures + 1 success


@pytest.mark.asyncio
async def test_retry_interceptor_retries_on_timeout_error(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor retries on MCPTimeoutError."""
    # Arrange
    request = sample_request.override()
    request.server_name = "weather"  # max_retries = 2

    # Fail once, then succeed
    handler = AsyncMock()
    handler.side_effect = [
        MCPTimeoutError("Timeout", server_name="weather", timeout_seconds=30.0),
        sample_result,
    ]

    interceptor = RetryInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, handler)

    # Assert
    assert result == sample_result
    assert handler.call_count == 2


@pytest.mark.asyncio
async def test_retry_interceptor_exhausts_retries_and_raises(
    sample_request: MCPToolCallRequest,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor raises original error after max retries."""
    # Arrange
    request = sample_request.override()
    request.server_name = "weather"  # max_retries = 2

    error = MCPConnectionError("Persistent failure", server_name="weather")
    handler = AsyncMock()
    handler.side_effect = error

    interceptor = RetryInterceptor(mcp_settings)

    # Act & Assert
    with pytest.raises(MCPConnectionError) as exc_info:
        await interceptor(request, handler)

    assert str(exc_info.value) == "[weather] Persistent failure"
    assert handler.call_count == 2  # max_retries for weather server


@pytest.mark.asyncio
async def test_retry_interceptor_does_not_retry_on_non_transient_errors(
    sample_request: MCPToolCallRequest,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor does not retry on non-transient errors."""
    # Arrange
    # ValueError is not a transient error
    error = ValueError("Invalid argument")
    handler = AsyncMock()
    handler.side_effect = error

    interceptor = RetryInterceptor(mcp_settings)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await interceptor(sample_request, handler)

    assert str(exc_info.value) == "Invalid argument"
    assert handler.call_count == 1  # No retry, only initial attempt


@pytest.mark.asyncio
async def test_retry_interceptor_uses_default_retries_for_unconfigured_server(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mcp_settings: MCPSettings,
) -> None:
    """Test that RetryInterceptor uses default retry count for unknown servers."""
    # Arrange
    request = sample_request.override()
    request.server_name = "unknown_server"  # Not in settings

    # Fail twice, then succeed (default max_retries = 3)
    handler = AsyncMock()
    handler.side_effect = [
        MCPConnectionError("Connection failed"),
        MCPConnectionError("Connection failed"),
        sample_result,
    ]

    interceptor = RetryInterceptor(mcp_settings)

    # Act
    result = await interceptor(request, handler)

    # Assert
    assert result == sample_result
    assert handler.call_count == 3


# ============================================================================
# ResultEnrichmentInterceptor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_result_enrichment_interceptor_logs_success_metadata(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
) -> None:
    """Test that ResultEnrichmentInterceptor logs metadata on success."""
    # Arrange
    interceptor = ResultEnrichmentInterceptor()

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        result = await interceptor(sample_request, mock_handler)

    # Assert
    assert result == sample_result
    assert mock_handler.call_count == 1

    # Verify metadata was logged
    assert mock_logger.info.call_count == 1
    log_call = mock_logger.info.call_args

    assert log_call[0][0] == "mcp_result_enriched"
    assert log_call[1]["server"] == "test_server"
    assert log_call[1]["tool"] == "test_tool"
    assert log_call[1]["success"] is True
    assert "duration_seconds" in log_call[1]
    assert "trace_id" in log_call[1]


@pytest.mark.asyncio
async def test_result_enrichment_interceptor_logs_error_metadata(
    sample_request: MCPToolCallRequest,
    mcp_settings: MCPSettings,
) -> None:
    """Test that ResultEnrichmentInterceptor logs metadata on error."""
    # Arrange
    error = ValueError("Tool execution failed")
    handler = AsyncMock()
    handler.side_effect = error

    interceptor = ResultEnrichmentInterceptor()

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        with pytest.raises(ValueError):
            await interceptor(sample_request, handler)

    # Assert
    assert handler.call_count == 1

    # Verify error metadata was logged
    assert mock_logger.exception.call_count == 1
    log_call = mock_logger.exception.call_args

    assert log_call[0][0] == "mcp_result_enriched"
    assert log_call[1]["server"] == "test_server"
    assert log_call[1]["tool"] == "test_tool"
    assert log_call[1]["success"] is False
    assert "duration_seconds" in log_call[1]
    assert "trace_id" in log_call[1]


@pytest.mark.asyncio
async def test_result_enrichment_interceptor_calculates_duration(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
) -> None:
    """Test that ResultEnrichmentInterceptor calculates execution duration."""
    # Arrange
    import asyncio

    async def slow_handler(request: MCPToolCallRequest) -> MockToolCallResult:
        await asyncio.sleep(0.1)  # Simulate 100ms execution
        return sample_result

    interceptor = ResultEnrichmentInterceptor()

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        result = await interceptor(sample_request, slow_handler)

    # Assert
    assert result == sample_result

    # Verify duration was logged and is approximately 100ms
    log_call = mock_logger.info.call_args
    duration = log_call[1]["duration_seconds"]
    assert 0.09 < duration < 0.2  # Allow some variance


# ============================================================================
# LoggingInterceptor Tests
# ============================================================================


@pytest.mark.asyncio
async def test_logging_interceptor_logs_request_start_and_complete(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
) -> None:
    """Test that LoggingInterceptor logs start and complete events."""
    # Arrange
    interceptor = LoggingInterceptor(log_arguments=False)

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        result = await interceptor(sample_request, mock_handler)

    # Assert
    assert result == sample_result
    assert mock_logger.info.call_count == 2

    # Verify start log
    start_call = mock_logger.info.call_args_list[0]
    assert start_call[0][0] == "mcp_tool_call_start"
    assert start_call[1]["server"] == "test_server"
    assert start_call[1]["tool"] == "test_tool"
    assert start_call[1]["args"] == ["param1", "param2"]  # Keys only

    # Verify complete log
    complete_call = mock_logger.info.call_args_list[1]
    assert complete_call[0][0] == "mcp_tool_call_complete"
    assert complete_call[1]["server"] == "test_server"
    assert complete_call[1]["tool"] == "test_tool"
    assert "duration_seconds" in complete_call[1]


@pytest.mark.asyncio
async def test_logging_interceptor_logs_full_arguments_when_enabled(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
) -> None:
    """Test that LoggingInterceptor logs full arguments when enabled."""
    # Arrange
    interceptor = LoggingInterceptor(log_arguments=True)

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        result = await interceptor(sample_request, mock_handler)

    # Assert
    assert result == sample_result

    # Verify full arguments were logged
    start_call = mock_logger.info.call_args_list[0]
    assert start_call[1]["args"] == {"param1": "value1", "param2": 42}


@pytest.mark.asyncio
async def test_logging_interceptor_logs_error_on_failure(
    sample_request: MCPToolCallRequest,
) -> None:
    """Test that LoggingInterceptor logs error event on failure."""
    # Arrange
    error = RuntimeError("Handler failed")
    handler = AsyncMock()
    handler.side_effect = error

    interceptor = LoggingInterceptor(log_arguments=False)

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        with pytest.raises(RuntimeError):
            await interceptor(sample_request, handler)

    # Assert
    assert mock_logger.info.call_count == 1  # Start log only
    assert mock_logger.exception.call_count == 1  # Error log

    # Verify error log
    error_call = mock_logger.exception.call_args
    assert error_call[0][0] == "mcp_tool_call_error"
    assert error_call[1]["server"] == "test_server"
    assert error_call[1]["tool"] == "test_tool"
    assert "duration_seconds" in error_call[1]


@pytest.mark.asyncio
async def test_logging_interceptor_correlates_with_langfuse_trace(
    sample_result: MockToolCallResult,
    mock_handler: AsyncMock,
) -> None:
    """Test that LoggingInterceptor extracts Langfuse trace ID from runtime."""
    # Arrange
    # Create mock runtime with trace_id (simulating LangGraph runtime)
    mock_runtime = Mock()
    mock_runtime.trace_id = "langfuse-trace-123"

    request = MCPToolCallRequest(
        name="test_tool",
        args={"param": "value"},
        server_name="test_server",
        runtime=mock_runtime,
    )

    interceptor = LoggingInterceptor(log_arguments=False)

    # Act
    with patch("app.shared.services.mcp.interceptors.logger") as mock_logger:
        result = await interceptor(request, mock_handler)

    # Assert
    assert result == sample_result

    # Verify Langfuse trace ID was logged
    start_call = mock_logger.info.call_args_list[0]
    assert start_call[1]["langfuse_trace_id"] == "langfuse-trace-123"

    complete_call = mock_logger.info.call_args_list[1]
    assert complete_call[1]["langfuse_trace_id"] == "langfuse-trace-123"


# ============================================================================
# create_default_interceptors Tests
# ============================================================================


def test_create_default_interceptors_returns_all_interceptors(
    mcp_settings: MCPSettings,
) -> None:
    """Test that create_default_interceptors returns all enabled interceptors."""
    # Act
    interceptors = create_default_interceptors(mcp_settings)

    # Assert
    assert len(interceptors) == 4
    assert isinstance(interceptors[0], LoggingInterceptor)
    assert isinstance(interceptors[1], AuthInterceptor)
    assert isinstance(interceptors[2], RetryInterceptor)
    assert isinstance(interceptors[3], ResultEnrichmentInterceptor)


def test_create_default_interceptors_respects_enable_flags(
    mcp_settings: MCPSettings,
) -> None:
    """Test that create_default_interceptors respects enable flags."""
    # Act
    config = InterceptorConfig(
        enable_auth=False,
        enable_retry=False,
        enable_enrichment=True,
        enable_logging=True,
    )
    interceptors = create_default_interceptors(mcp_settings, config)

    # Assert
    assert len(interceptors) == 2
    assert isinstance(interceptors[0], LoggingInterceptor)
    assert isinstance(interceptors[1], ResultEnrichmentInterceptor)


def test_create_default_interceptors_configures_logging_with_arguments(
    mcp_settings: MCPSettings,
) -> None:
    """Test that create_default_interceptors configures LoggingInterceptor."""
    # Act
    config = InterceptorConfig(log_arguments=True)
    interceptors = create_default_interceptors(mcp_settings, config)

    # Assert
    logging_interceptor = interceptors[0]
    assert isinstance(logging_interceptor, LoggingInterceptor)
    assert logging_interceptor.log_arguments is True


def test_create_default_interceptors_returns_empty_when_all_disabled(
    mcp_settings: MCPSettings,
) -> None:
    """Test that create_default_interceptors returns empty list when all disabled."""
    # Act
    config = InterceptorConfig(
        enable_auth=False,
        enable_retry=False,
        enable_enrichment=False,
        enable_logging=False,
    )
    interceptors = create_default_interceptors(mcp_settings, config)

    # Assert
    assert len(interceptors) == 0


# ============================================================================
# Integration Tests - Interceptor Chain
# ============================================================================


@pytest.mark.asyncio
async def test_interceptor_chain_executes_in_order(
    sample_request: MCPToolCallRequest,
    sample_result: MockToolCallResult,
    mcp_settings: MCPSettings,
) -> None:
    """Test that multiple interceptors execute in the correct order."""
    # Arrange
    execution_log: list[str] = []

    # Create custom interceptors that log execution order
    class OrderLoggingInterceptor:
        def __init__(self, name: str) -> None:
            self.name = name

        async def __call__(
            self,
            request: MCPToolCallRequest,
            handler: Callable[[MCPToolCallRequest], Awaitable[MockToolCallResult]],
        ) -> MockToolCallResult:
            execution_log.append(f"{self.name}_before")
            result = await handler(request)
            execution_log.append(f"{self.name}_after")
            return result

    # Create handler
    async def final_handler(request: MCPToolCallRequest) -> MockToolCallResult:
        execution_log.append("handler")
        return sample_result

    # Create interceptor chain (outermost to innermost)
    interceptor1 = OrderLoggingInterceptor("outer")
    interceptor2 = OrderLoggingInterceptor("middle")
    interceptor3 = OrderLoggingInterceptor("inner")

    # Build nested handler (similar to how langchain-mcp-adapters chains them)
    handler = final_handler
    for interceptor in reversed([interceptor1, interceptor2, interceptor3]):
        # Capture current handler in closure
        current_handler = handler

        async def wrapped_handler(
            req: MCPToolCallRequest,
            interceptor=interceptor,
            h=current_handler,
        ) -> MockToolCallResult:
            return await interceptor(req, h)

        handler = wrapped_handler

    # Act
    result = await handler(sample_request)

    # Assert
    assert result == sample_result
    assert execution_log == [
        "outer_before",
        "middle_before",
        "inner_before",
        "handler",
        "inner_after",
        "middle_after",
        "outer_after",
    ]

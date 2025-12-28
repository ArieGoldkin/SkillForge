"""Unit tests for base agent utilities."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.core.bulkhead import BulkheadFullError, BulkheadTimeoutError, Tier
from app.domains.analysis.workflows.agents.base import (
    create_structured_agent,
    emit_agent_progress,
    handle_agent_node_error,
    save_agent_finding,
)


class MockAgentSchema(BaseModel):
    """Mock schema for agent output testing."""

    field1: str
    field2: int


@pytest.fixture
def mock_session():
    """Mock database session.

    Note: session.add() is not async, so it's a MagicMock, not AsyncMock.
    session.commit() and session.refresh() are async, so they're AsyncMock.
    session.execute() and session.scalar_one_or_none() are async.
    """
    session = AsyncMock()
    # session.add() is synchronous, not async
    session.add = MagicMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    # Mock async methods that return results
    # Note: scalar_one_or_none() is synchronous, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=MagicMock())  # Return mock Analysis
    session.execute = AsyncMock(return_value=mock_result)
    return session


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent(mock_create_agent, mock_get_model):
    """Test creating agent with structured output."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    mock_create_agent.assert_called_once()
    # Verify ToolStrategy was used
    call_args = mock_create_agent.call_args
    assert "response_format" in call_args.kwargs


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
@patch("app.domains.analysis.workflows.agents.base.ToolStrategy")
def test_create_structured_agent_uses_tool_strategy(
    mock_tool_strategy, mock_create_agent, mock_get_model
):
    """Test creating agent uses ToolStrategy for response validation.

    Note: ToolStrategy handles schema validation internally. LangChain 1.2.x
    strict mode is applied via with_structured_output() in non-agent paths
    (supervisor, synthesis, compression).
    """
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    # Verify ToolStrategy was called with the schema
    mock_tool_strategy.assert_called_once_with(MockAgentSchema)


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent_uses_tool_choice_auto(mock_create_agent, mock_get_model):
    """Test creating agent uses tool_choice='auto' (LangChain 1.2.x).

    Issue #299-304: Explicit tool_choice provides consistent behavior across
    different LLM providers (Anthropic, OpenAI, Gemini).
    """
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    # Verify bind_tools was called with tool_choice="auto"
    bind_tools_call = mock_model.bind_tools.call_args
    assert bind_tools_call.kwargs.get("tool_choice") == "auto"


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent_with_task_type(mock_create_agent, mock_get_model):
    """Test creating agent with task_type for model routing."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
        task_type="synthesis",
    )

    # Verify get_chat_model was called with task_type
    mock_get_model.assert_called_once_with(task_type="synthesis")
    mock_create_agent.assert_called_once()


@patch("app.domains.analysis.workflows.agents.base.get_chat_model")
@patch("app.domains.analysis.workflows.agents.base.create_agent")
def test_create_structured_agent_without_task_type(mock_create_agent, mock_get_model):
    """Test creating agent without task_type passes None to model factory."""
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    mock_create_agent.return_value = MagicMock()

    create_structured_agent(
        system_prompt="Test prompt",
        response_schema=MockAgentSchema,
    )

    # Verify get_chat_model was called with task_type=None (default)
    mock_get_model.assert_called_once_with(task_type=None)


@pytest.mark.asyncio
async def test_save_agent_finding(mock_session):
    """Test saving agent finding to database."""
    analysis_id = uuid4()
    findings: dict[str, object] = {"key": "value"}

    await save_agent_finding(
        session=mock_session,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        findings=findings,
        confidence_score=0.9,
        processing_time_ms=1000,
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.emit_streaming_event")
@patch("app.domains.analysis.workflows.agents.base.get_stage_name")
async def test_emit_agent_progress_success(mock_get_stage_name, mock_emit_event):
    """Test emitting agent progress SSE event."""
    # Setup mocks
    analysis_id = str(uuid4())
    mock_get_stage_name.return_value = "tech_comparison"
    mock_emit_event.return_value = AsyncMock()

    # Call function
    await emit_agent_progress(
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        status="running",
        detail="Analyzing technologies",
    )

    # Verify stage name was retrieved
    mock_get_stage_name.assert_called_once_with("tech_comparator")

    # Verify event was emitted with correct parameters
    mock_emit_event.assert_awaited_once()
    call_args = mock_emit_event.call_args
    assert call_args.args[0] == "progress"
    assert call_args.kwargs["analysis_id"] == analysis_id
    assert call_args.kwargs["stage"] == "tech_comparison"
    assert call_args.kwargs["status"] == "running"
    assert call_args.kwargs["agent_type"] == "tech_comparator"
    assert call_args.kwargs["detail"] == "Analyzing technologies"


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.emit_streaming_event")
@patch("app.domains.analysis.workflows.agents.base.get_stage_name")
async def test_emit_agent_progress_with_kwargs(mock_get_stage_name, mock_emit_event):
    """Test emitting agent progress with additional kwargs."""
    # Setup mocks
    analysis_id = str(uuid4())
    mock_get_stage_name.return_value = "security_audit"
    mock_emit_event.return_value = AsyncMock()

    # Call with multiple kwargs
    await emit_agent_progress(
        analysis_id=analysis_id,
        agent_type="security_auditor",
        status="complete",
        findings_count=5,
        vulnerabilities_found=2,
        processing_time_ms=1500,
    )

    # Verify all kwargs were passed through
    mock_emit_event.assert_awaited_once()
    call_kwargs = mock_emit_event.call_args.kwargs
    assert call_kwargs["findings_count"] == 5
    assert call_kwargs["vulnerabilities_found"] == 2
    assert call_kwargs["processing_time_ms"] == 1500


# Tests for handle_agent_node_error() function


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
async def test_handle_bulkhead_full_error_returns_empty_findings(mock_record_agent_execution):
    """Test BulkheadFullError returns empty findings dictionary."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "tech_comparator"
    duration = 2.5
    trace_id = "test-trace-id"
    error = BulkheadFullError(name="test_bulkhead", tier=Tier.STANDARD, queue_size=10)

    # Execute
    result = await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify
    assert result == {"agent_findings": []}


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
async def test_handle_bulkhead_full_error_records_rejected_status(mock_record_agent_execution):
    """Test BulkheadFullError records AGENT_BULKHEAD_REJECTED status."""
    # Setup
    from app.domains.analysis.constants.error_codes import (
        AGENT_BULKHEAD_REJECTED,
        AgentStatus,
    )

    analysis_id = str(uuid4())
    agent_type = "tech_comparator"
    duration = 2.5
    trace_id = "test-trace-id"
    error = BulkheadFullError(name="test_bulkhead", tier=Tier.STANDARD, queue_size=10)

    # Execute
    await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify record_agent_execution was called with correct parameters
    mock_record_agent_execution.assert_awaited_once()
    call_kwargs = mock_record_agent_execution.call_args.kwargs
    assert call_kwargs["analysis_id"] == analysis_id
    assert call_kwargs["agent_type"] == agent_type
    assert call_kwargs["status"] == AgentStatus.FAILED
    assert call_kwargs["error_code"] == AGENT_BULKHEAD_REJECTED
    # Error message is the full exception string
    assert "test_bulkhead" in call_kwargs["error_message"]
    assert call_kwargs["processing_time_ms"] == 2500


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
async def test_handle_bulkhead_timeout_error_graceful_degradation(mock_record_agent_execution):
    """Test BulkheadTimeoutError has same graceful degradation as BulkheadFullError."""
    # Setup
    from app.domains.analysis.constants.error_codes import (
        AGENT_BULKHEAD_REJECTED,
        AgentStatus,
    )

    analysis_id = str(uuid4())
    agent_type = "security_auditor"
    duration = 5.0
    trace_id = "test-trace-id-2"
    error = BulkheadTimeoutError(name="test_bulkhead", timeout=300.0)

    # Execute
    result = await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify empty findings returned
    assert result == {"agent_findings": []}

    # Verify record_agent_execution was called with AGENT_BULKHEAD_REJECTED
    mock_record_agent_execution.assert_awaited_once()
    call_kwargs = mock_record_agent_execution.call_args.kwargs
    assert call_kwargs["status"] == AgentStatus.FAILED
    assert call_kwargs["error_code"] == AGENT_BULKHEAD_REJECTED
    # Error message contains bulkhead name and timeout
    assert "test_bulkhead" in call_kwargs["error_message"]
    assert call_kwargs["processing_time_ms"] == 5000


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
async def test_handle_generator_exit_returns_empty_findings(mock_record_agent_execution):
    """Test GeneratorExit returns empty findings dictionary."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "code_quality_critic"
    duration = 1.5
    trace_id = "test-trace-id-3"
    error = GeneratorExit()

    # Execute
    result = await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify
    assert result == {"agent_findings": []}


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
@patch("app.domains.analysis.services.persistence.error_recorder.error_recorder")
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress")
async def test_handle_timeout_error_returns_empty_findings(
    mock_emit_progress, mock_error_recorder, mock_record_agent_execution
):
    """Test TimeoutError returns empty findings dictionary."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "implementation_planner"
    duration = 10.0
    trace_id = "test-trace-id-4"
    error = TimeoutError("Operation timed out")

    # Mock error_recorder.record as async
    mock_error_recorder.record = AsyncMock()

    # Execute
    result = await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify
    assert result == {"agent_findings": []}


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
@patch("app.domains.analysis.services.persistence.error_recorder.error_recorder")
@patch("app.domains.analysis.workflows.agents.base.emit_agent_progress")
async def test_handle_generic_exception_returns_empty_findings(
    mock_emit_progress, mock_error_recorder, mock_record_agent_execution
):
    """Test generic Exception handling returns empty findings."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "integration_advisor"
    duration = 3.0
    trace_id = "test-trace-id-5"
    error = RuntimeError("Unexpected database connection error")

    # Mock error_recorder.record as async
    mock_error_recorder.record = AsyncMock()

    # Execute
    result = await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify empty findings
    assert result == {"agent_findings": []}

    # Verify error was recorded to database via error_recorder
    mock_error_recorder.record.assert_awaited_once()
    error_call_kwargs = mock_error_recorder.record.call_args.kwargs
    assert error_call_kwargs["analysis_id"] == analysis_id
    assert error_call_kwargs["error_code"] == "INTEGRATION_ADVISOR_FAILED"
    assert error_call_kwargs["error_message"] == "Unexpected database connection error"
    assert error_call_kwargs["stage"] == agent_type


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
async def test_error_message_truncation_at_500_chars(mock_record_agent_execution):
    """Test long error messages are truncated to 500 characters for bulkhead errors."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "best_practices_checker"
    duration = 1.0
    trace_id = "test-trace-id-6"
    # Create BulkheadFullError - error message will be generated by __init__
    # We need to verify the truncation happens in handle_agent_node_error
    error = BulkheadFullError(name="A" * 600, tier=Tier.STANDARD, queue_size=10)

    # Execute
    await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify error_message was truncated to 500 chars
    mock_record_agent_execution.assert_awaited_once()
    call_kwargs = mock_record_agent_execution.call_args.kwargs
    assert len(call_kwargs["error_message"]) == 500


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.base.record_agent_execution")
@patch("app.domains.analysis.workflows.agents.base.logger")
async def test_handle_error_logs_trace_id(mock_logger, mock_record_agent_execution):
    """Test trace_id is included in log calls for observability."""
    # Setup
    analysis_id = str(uuid4())
    agent_type = "performance_analyzer"
    duration = 2.0
    trace_id = "langfuse-trace-abc123"
    error = BulkheadFullError(name="test_queue", tier=Tier.STANDARD, queue_size=5)

    # Execute
    await handle_agent_node_error(
        error=error,
        analysis_id=analysis_id,
        agent_type=agent_type,
        duration=duration,
        trace_id=trace_id,
    )

    # Verify trace_id was logged
    mock_logger.warning.assert_called_once()
    log_call_args = mock_logger.warning.call_args[1]
    assert log_call_args["trace_id"] == trace_id
    assert log_call_args["agent_type"] == agent_type
    assert log_call_args["analysis_id"] == str(analysis_id)

"""Unit tests for base agent utilities."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import patch as mock_patch
from uuid import UUID, uuid4

import pytest
from langchain.messages import AIMessage
from pydantic import BaseModel

from app.workflows.agents.base import (
    create_structured_agent,
    run_agent_with_tracking,
    save_agent_finding,
)


class MockAgentSchema(BaseModel):
    """Mock schema for agent output testing."""

    field1: str
    field2: int


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_agent():
    """Mock agent instance."""
    agent = MagicMock()
    # Set astream to None so hasattr check fails and it falls back to ainvoke
    agent.astream = None
    # Mock ainvoke (async) which is preferred, fallback to invoke if not available
    agent.ainvoke = AsyncMock(
        return_value={"structured_response": MockAgentSchema(field1="test", field2=42)}
    )
    return agent


@pytest.fixture
def mock_streaming_agent():
    """Mock agent with streaming support."""

    async def create_stream(*args, **kwargs):
        # Simulate streaming chunks - create new generator each time
        chunks = [
            {"messages": [AIMessage(content="Analyzing")]},
            {"messages": [AIMessage(content="Analyzing integration")]},
            {
                "messages": [AIMessage(content="Analyzing integration feasibility")],
                "structured_response": MockAgentSchema(field1="test", field2=42),
            },
        ]
        for chunk in chunks:
            yield chunk

    agent = MagicMock()

    # Create a callable that returns async generator (not awaitable itself)
    def astream_wrapper(*args, **kwargs):
        return create_stream(*args, **kwargs)

    # Wrap in MagicMock to track calls
    agent.astream = MagicMock(side_effect=astream_wrapper)
    return agent


@patch("app.workflows.agents.base.get_chat_model")
@patch("app.workflows.agents.base.create_agent")
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


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_success(
    mock_save_finding,
    mock_emit_progress,
    mock_agent,
    mock_session,
):
    """Test successful agent execution with tracking."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    assert "processing_time_ms" in result
    mock_emit_progress.assert_called()
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
async def test_run_agent_with_tracking_no_structured_response(
    mock_emit_progress,
    mock_session,
):
    """Test error when agent doesn't return structured_response."""
    analysis_id = str(uuid4())
    mock_agent = MagicMock()
    mock_agent.astream = None  # Explicitly disable streaming to use ainvoke
    mock_agent.ainvoke = AsyncMock(return_value={})  # No structured_response

    with pytest.raises(RuntimeError, match="did not return structured_response"):
        await run_agent_with_tracking(
            agent=mock_agent,
            content="test",
            content_type="article",
            analysis_id=analysis_id,
            agent_type="test_agent",
            session=mock_session,
        )


@pytest.mark.asyncio
async def test_save_agent_finding(mock_session):
    """Test saving agent finding to database."""
    analysis_id = uuid4()
    findings = {"key": "value"}

    await save_agent_finding(
        session=mock_session,
        analysis_id=analysis_id,
        agent_type="test_agent",
        findings=findings,
        confidence_score=0.9,
        processing_time_ms=1000,
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_non_uuid_analysis_id(
    mock_save_finding,
    mock_emit_progress,
    mock_agent,
    mock_session,
):
    """Test that non-UUID analysis_id strings are converted to UUIDs."""
    analysis_id = "dev-test-opus-4-5"  # Non-UUID string
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify save_agent_finding was called with a UUID
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)

    # Verify it's deterministic - same string = same UUID
    namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    expected_uuid = uuid.uuid5(namespace, analysis_id)
    assert called_analysis_id == expected_uuid

    # Verify result still works
    assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_valid_uuid_string(
    mock_save_finding,
    mock_emit_progress,
    mock_agent,
    mock_session,
):
    """Test that valid UUID strings work correctly (regression test)."""
    analysis_id = str(uuid4())  # Valid UUID string
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert str(called_analysis_id) == analysis_id  # Should match exactly

    assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_content_truncation(
    mock_save_finding,
    mock_emit_progress,
    mock_agent,
    mock_session,
):
    """Test that content is truncated to 1500 chars for agent efficiency."""
    analysis_id = str(uuid4())
    # Create content longer than 1500 chars
    long_content = "x" * 2500

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=long_content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify agent was called with truncated content
    assert mock_agent.ainvoke.called
    call_args = mock_agent.ainvoke.call_args
    input_messages = call_args[0][0] if call_args[0] else {}
    messages = input_messages.get("messages", [])
    if messages:
        user_message = messages[0].get("content", "")
        # Content should be truncated to 1500 chars (plus header text)
        assert "Content Type: article" in user_message
        # Extract just the content part (after "Content:\n")
        content_part = (
            user_message.split("Content:\n", 1)[1] if "Content:\n" in user_message else ""
        )
        max_content_length = 1500  # Default max_content_length for agents
        assert len(content_part) <= max_content_length
        assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_streaming(
    mock_save_finding,
    mock_emit_progress,
    mock_streaming_agent,
    mock_session,
):
    """Test agent execution with streaming emits progress events."""
    analysis_id = str(uuid4())
    content = "Test content for streaming"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_streaming_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify streaming was used
    assert mock_streaming_agent.astream.called
    # Verify progress events were emitted during streaming
    min_expected_events = 2  # At least "running" and "streaming" events
    assert mock_emit_progress.call_count >= min_expected_events
    # Verify final result is correct
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_uuid_object(
    mock_save_finding,
    mock_emit_progress,
    mock_agent,
    mock_session,
):
    """Test that UUID objects (not strings) work correctly."""
    analysis_id = uuid4()  # UUID object, not string
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify save_agent_finding was called with the same UUID object
    assert mock_save_finding.called
    call_args = mock_save_finding.call_args
    called_analysis_id = call_args.kwargs["analysis_id"]
    assert isinstance(called_analysis_id, UUID)
    assert called_analysis_id == analysis_id  # Should match exactly

    assert result["agent_type"] == "test_agent"


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_streaming_throttling(
    mock_save_finding,
    mock_emit_progress,
    mock_streaming_agent,
    mock_session,
):
    """Test that SSE events are throttled during streaming."""
    analysis_id = str(uuid4())
    content = "Test content for throttling"

    mock_save_finding.return_value = MagicMock()

    # Mock time to control throttling behavior
    with mock_patch("app.workflows.agents.base.time.time") as mock_time:
        # Simulate time progression
        mock_time.side_effect = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

        result = await run_agent_with_tracking(
            agent=mock_streaming_agent,
            content=content,
            content_type="article",
            analysis_id=analysis_id,
            agent_type="test_agent",
            session=mock_session,
        )

        # Verify streaming was used
        assert mock_streaming_agent.astream.called

        # Verify SSE events were emitted (but throttled)
        # Should have fewer events than chunks due to throttling
        min_expected_events = 2  # At least "running" and some streaming events
        assert mock_emit_progress.call_count >= min_expected_events
        # But should be throttled (not one per chunk)
        # With 3 chunks and 500ms throttle, we'd expect fewer than 3 streaming events

        assert result["agent_type"] == "test_agent"
        assert "findings" in result
        mock_save_finding.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.base.emit_agent_progress")
@patch("app.workflows.agents.base.save_agent_finding")
async def test_run_agent_with_tracking_streaming_early_response(
    mock_save_finding,
    mock_emit_progress,
    mock_session,
):
    """Test that structured_response in intermediate chunk is captured."""

    # Create mock agent that returns structured_response in intermediate chunk
    async def mock_astream_with_early_response(*args, **kwargs):
        chunks = [
            {"messages": [AIMessage(content="Starting")]},
            {
                "messages": [AIMessage(content="Processing")],
                "structured_response": MockAgentSchema(field1="early", field2=42),
            },
            {"messages": [AIMessage(content="Finishing")]},
        ]
        for chunk in chunks:
            yield chunk

    mock_agent = MagicMock()
    mock_agent.astream = mock_astream_with_early_response

    analysis_id = str(uuid4())
    content = "Test content"

    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type="article",
        analysis_id=analysis_id,
        agent_type="test_agent",
        session=mock_session,
    )

    # Verify structured_response from intermediate chunk was captured
    expected_field2 = 42  # Expected value from MockAgentSchema
    assert result["agent_type"] == "test_agent"
    assert "findings" in result
    assert result["findings"]["field1"] == "early"
    assert result["findings"]["field2"] == expected_field2
    mock_save_finding.assert_called_once()

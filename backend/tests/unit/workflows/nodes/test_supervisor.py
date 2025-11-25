"""Unit tests for supervisor node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.nodes.supervisor import _parse_tool_calls_from_messages, supervisor_route


@pytest.fixture
def mock_agent_response_with_tool_calls():
    """Mock agent response with tool calls."""
    return {
        "messages": [
            {
                "id": "msg_1",
                "type": "ai",
                "tool_calls": [
                    {
                        "name": "tech_comparator_tool",
                        "args": {"content": "test content"},
                        "id": "call_1",
                    },
                    {
                        "name": "security_auditor_tool",
                        "args": {"content": "test content"},
                        "id": "call_2",
                    },
                ],
            }
        ]
    }


@pytest.fixture
def mock_agent_response_no_tool_calls():
    """Mock agent response without tool calls."""
    return {
        "messages": [
            {
                "id": "msg_1",
                "type": "ai",
                "content": "No agents needed for this content.",
            }
        ]
    }


@pytest.fixture
def mock_ai_message_with_tool_calls():
    """Create a mock AIMessage with tool calls."""
    from langchain_core.messages import AIMessage

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "tech_comparator_tool",
                "args": {"content": "test"},
                "id": "call_1",
            },
            {
                "name": "implementation_planner_tool",
                "args": {"content": "test"},
                "id": "call_2",
            },
        ],
    )


@pytest.fixture
def mock_ai_message_no_tool_calls():
    """Create a mock AIMessage without tool calls."""
    from langchain_core.messages import AIMessage

    return AIMessage(content="No agents needed.")


def test_parse_tool_calls_from_ai_message(mock_ai_message_with_tool_calls):
    """Test parsing tool calls from AIMessage."""
    messages = [mock_ai_message_with_tool_calls]
    selected_agents = _parse_tool_calls_from_messages(messages)

    assert len(selected_agents) == 2
    assert "tech_comparator" in selected_agents
    assert "implementation_planner" in selected_agents


def test_parse_tool_calls_no_tool_calls(mock_ai_message_no_tool_calls):
    """Test parsing when no tool calls are present."""
    messages = [mock_ai_message_no_tool_calls]
    selected_agents = _parse_tool_calls_from_messages(messages)

    assert len(selected_agents) == 0


def test_parse_tool_calls_empty_messages():
    """Test parsing with empty messages list."""
    selected_agents = _parse_tool_calls_from_messages([])
    assert len(selected_agents) == 0


def test_parse_tool_calls_all_agents():
    """Test parsing all 8 agent tool calls."""
    from langchain_core.messages import AIMessage

    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "tech_comparator_tool", "args": {}, "id": f"call_{i}"} for i in range(8)
            ]
            + [
                {"name": "security_auditor_tool", "args": {}, "id": "call_9"},
                {"name": "integration_feasibility_tool", "args": {}, "id": "call_10"},
                {"name": "implementation_planner_tool", "args": {}, "id": "call_11"},
                {"name": "performance_analyst_tool", "args": {}, "id": "call_12"},
                {"name": "code_quality_critic_tool", "args": {}, "id": "call_13"},
                {"name": "trend_validator_tool", "args": {}, "id": "call_14"},
                {"name": "dependency_mapper_tool", "args": {}, "id": "call_15"},
            ],
        )
    ]

    selected_agents = _parse_tool_calls_from_messages(messages)
    assert len(selected_agents) == 8
    assert "tech_comparator" in selected_agents
    assert "security_auditor" in selected_agents
    assert "integration_feasibility" in selected_agents
    assert "implementation_planner" in selected_agents
    assert "performance_analyst" in selected_agents
    assert "code_quality_critic" in selected_agents
    assert "trend_validator" in selected_agents
    assert "dependency_mapper" in selected_agents


def _create_mock_agent_with_streaming(messages: list) -> MagicMock:
    """Create a mock agent that supports astream() for streaming."""

    async def mock_astream_generator(*args, **kwargs):
        yield {"messages": messages}

    class MockAsyncIterator:
        def __init__(self, messages):
            self.messages = messages

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not hasattr(self, "_yielded"):
                self._yielded = True
                return {"messages": self.messages}
            raise StopAsyncIteration

    mock_agent = MagicMock()
    mock_agent.astream = MagicMock(return_value=MockAsyncIterator(messages))
    mock_agent.invoke = MagicMock(return_value={"messages": messages})  # Fallback
    return mock_agent


@pytest.mark.asyncio
async def test_supervisor_route_success(mock_ai_message_with_tool_calls):
    """Test supervisor_route with successful agent selection."""
    mock_agent = _create_mock_agent_with_streaming([mock_ai_message_with_tool_calls])

    with (
        patch("app.workflows.nodes.supervisor._get_supervisor_agent", return_value=mock_agent),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        result = await supervisor_route(
            content="This is a test article about React and security best practices.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Verify supervisor decision structure
        assert "supervisor_decision" in result
        decision = result["supervisor_decision"]
        assert "agents" in decision
        assert "priority" in decision
        assert "reasoning" in decision

        # Verify agents were selected
        assert len(decision["agents"]) > 0
        assert len(decision["priority"]) == len(decision["agents"])

        # Verify SSE events were emitted
        assert mock_emit.call_count >= 2  # Start and complete events
        start_call = mock_emit.call_args_list[0]
        assert start_call[1]["stage"] == "supervisor"
        assert start_call[1]["status"] == "running"


@pytest.mark.asyncio
async def test_supervisor_route_no_agents_selected(mock_ai_message_no_tool_calls):
    """Test supervisor_route when no agents are selected."""
    mock_agent = _create_mock_agent_with_streaming([mock_ai_message_no_tool_calls])

    with (
        patch("app.workflows.nodes.supervisor._get_supervisor_agent", return_value=mock_agent),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
    ):
        result = await supervisor_route(
            content="Simple content that doesn't need analysis.",
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Verify decision structure even when no agents selected
        assert "supervisor_decision" in result
        decision = result["supervisor_decision"]
        assert decision["agents"] == []
        assert decision["priority"] == []

        # Verify complete event was emitted with agent_count=0
        complete_calls = [c for c in mock_emit.call_args_list if c[1].get("status") == "complete"]
        assert len(complete_calls) > 0
        complete_call = complete_calls[0]
        assert complete_call[1]["agent_count"] == 0


@pytest.mark.asyncio
async def test_supervisor_route_error_handling():
    """Test supervisor_route handles errors gracefully."""
    mock_agent = MagicMock()
    mock_agent.astream = MagicMock(side_effect=Exception("Agent invocation failed"))
    mock_agent.invoke = MagicMock(side_effect=Exception("Agent invocation failed"))

    with (
        patch("app.workflows.nodes.supervisor._get_supervisor_agent", return_value=mock_agent),
        patch(
            "app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
        pytest.raises(Exception, match="Agent invocation failed"),
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
async def test_supervisor_route_content_truncation():
    """Test that content is truncated to 2000 chars for prompt efficiency."""
    mock_ai_message = MagicMock()
    mock_ai_message.tool_calls = []
    mock_agent = _create_mock_agent_with_streaming([mock_ai_message])

    # Create content longer than 2000 chars
    long_content = "x" * 3000

    with (
        patch("app.workflows.nodes.supervisor._get_supervisor_agent", return_value=mock_agent),
        patch("app.workflows.nodes.supervisor.emit_streaming_event", new_callable=AsyncMock),
    ):
        await supervisor_route(
            content=long_content,
            content_type="article",
            analysis_id="test-analysis-id",
        )

        # Verify agent was called with truncated content
        # astream is called with input_messages
        assert mock_agent.astream.called
        call_args = mock_agent.astream.call_args
        if call_args:
            input_messages = call_args[0][0] if call_args[0] else {}
            messages = input_messages.get("messages", [])
            if messages:
                user_message = messages[0].get("content", "")
                # Content should be truncated to 2000 chars (plus header text)
                assert "Content Type: article" in user_message
                assert len(user_message) < 3000  # Should be truncated


@pytest.mark.asyncio
async def test_supervisor_route_decision_structure():
    """Test that supervisor decision has correct structure."""
    from langchain_core.messages import AIMessage

    mock_ai_message = AIMessage(
        content="",
        tool_calls=[
            {"name": "tech_comparator_tool", "args": {}, "id": "call_1"},
            {"name": "security_auditor_tool", "args": {}, "id": "call_2"},
        ],
    )
    mock_agent = _create_mock_agent_with_streaming([mock_ai_message])

    with (
        patch("app.workflows.nodes.supervisor._get_supervisor_agent", return_value=mock_agent),
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
        assert len(decision["agents"]) == len(decision["priority"])
        # All priorities should be 0.9 (simplified)
        assert all(p == 0.9 for p in decision["priority"])

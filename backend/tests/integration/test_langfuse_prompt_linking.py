"""Integration tests for Langfuse prompt linkage in agent invocation (Issue #564).

Tests verify that prompts fetched from Langfuse are properly linked to generation spans
during agent execution via update_current_generation, with graceful degradation when
Langfuse is unavailable.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.invocation import invoke_agent


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_in_agent_invocation(mock_get_client):
    """Test that prompt is linked to generation span during agent invocation.

    Scenario: Agent has langfuse_prompt_client in metadata
    Expected: update_current_generation is called with prompt object
    """
    # Mock Langfuse client
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Create mock prompt object (simulates Langfuse PromptClient)
    mock_prompt = MagicMock()
    mock_prompt.name = "security-auditor"
    mock_prompt.version = 42
    mock_prompt.config = {"model": "gpt-4", "temperature": 0.7}

    # Create mock agent with prompt in metadata
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Test findings"})

    # CRITICAL: Agent config with langfuse_prompt_client in metadata
    mock_config = MagicMock()
    mock_config.metadata = {
        "langfuse_prompt_client": mock_prompt,
        "agent_type": "security_auditor",
    }
    mock_agent.config = mock_config

    # Test input
    input_messages = {"messages": [{"role": "user", "content": "Analyze security"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="security_auditor",
        timeout=30.0,
    )

    # Verify prompt was linked to generation
    mock_get_client.assert_called_once()
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)

    # Verify agent was invoked successfully
    assert result == {"output": "Test findings"}
    mock_agent.ainvoke.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_graceful_degradation_langfuse_unavailable(mock_get_client):
    """Test graceful degradation when Langfuse is unavailable.

    Scenario: Langfuse raises exception during update_current_generation
    Expected: Exception is caught, agent execution continues successfully
    """
    # Mock Langfuse client that raises exception
    mock_langfuse = MagicMock()
    mock_langfuse.update_current_generation.side_effect = RuntimeError("Langfuse unavailable")
    mock_get_client.return_value = mock_langfuse

    # Create mock prompt and agent
    mock_prompt = MagicMock()
    mock_prompt.name = "tech-comparator"
    mock_prompt.version = 3

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Comparison results"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Compare React vs Vue"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should NOT raise exception
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        timeout=30.0,
    )

    # Verify agent execution succeeded despite Langfuse error
    assert result == {"output": "Comparison results"}
    mock_agent.ainvoke.assert_called_once()

    # Verify update_current_generation was attempted
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_skipped_for_cache_hits(mock_get_client):
    """Test prompt linkage is skipped when no prompt in metadata (cache hit scenario).

    Scenario: Agent has no langfuse_prompt_client in metadata (semantic cache hit)
    Expected: update_current_generation is NOT called, agent executes normally
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Create mock agent WITHOUT prompt in metadata (cache hit)
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Cached results"})
    mock_config = MagicMock()
    mock_config.metadata = {
        # No langfuse_prompt_client - simulates cache hit
        "cache_hit": True,
        "agent_type": "performance_analyst",
    }
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Analyze performance"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="performance_analyst",
        timeout=30.0,
    )

    # Verify agent executed successfully
    assert result == {"output": "Cached results"}
    mock_agent.ainvoke.assert_called_once()

    # Verify update_current_generation was NOT called (no prompt to link)
    mock_langfuse.update_current_generation.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_skipped_when_metadata_is_none(mock_get_client):
    """Test prompt linkage is skipped when config.metadata is None.

    Scenario: Agent config exists but metadata is None
    Expected: No exception, agent executes normally
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Create mock agent with None metadata
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Test output"})
    mock_config = MagicMock()
    mock_config.metadata = None  # Explicitly None
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test input"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should handle None metadata gracefully
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify agent executed successfully
    assert result == {"output": "Test output"}
    mock_agent.ainvoke.assert_called_once()

    # Verify update_current_generation was NOT called
    mock_langfuse.update_current_generation.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_skipped_when_config_missing(mock_get_client):
    """Test prompt linkage is skipped when agent has no config attribute.

    Scenario: Agent has no config attribute at all
    Expected: No exception, agent executes normally
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Create mock agent without config attribute
    mock_agent = MagicMock(spec=["ainvoke"])  # Only ainvoke, no config
    mock_agent.ainvoke = AsyncMock(return_value={"output": "No config output"})

    input_messages = {"messages": [{"role": "user", "content": "Test input"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should handle missing config gracefully
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify agent executed successfully
    assert result == {"output": "No config output"}
    mock_agent.ainvoke.assert_called_once()

    # Verify update_current_generation was NOT called
    mock_langfuse.update_current_generation.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_with_get_client_returning_none(mock_get_client):
    """Test graceful degradation when get_client returns None.

    Scenario: Langfuse is disabled (get_client returns None)
    Expected: No exception, agent executes normally
    """
    # Langfuse disabled (returns None)
    mock_get_client.return_value = None

    # Create mock agent with prompt in metadata
    mock_prompt = MagicMock()
    mock_prompt.name = "implementation-planner"

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Implementation plan"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Plan implementation"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should handle None client gracefully
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="implementation_planner",
        timeout=30.0,
    )

    # Verify agent executed successfully
    assert result == {"output": "Implementation plan"}
    mock_agent.ainvoke.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
@patch("app.domains.analysis.workflows.agents.invocation.logger")
async def test_prompt_linkage_logs_debug_message(mock_logger, mock_get_client):
    """Test that successful prompt linking logs debug message.

    Scenario: Prompt successfully linked to generation
    Expected: Debug log emitted with prompt name and agent type
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    mock_prompt = MagicMock()
    mock_prompt.name = "dependency-mapper"
    mock_prompt.version = 7

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Dependency map"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Map dependencies"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation
    await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="dependency_mapper",
        timeout=30.0,
    )

    # Verify debug log was emitted
    mock_logger.debug.assert_any_call(
        "prompt_linked_to_generation",
        prompt_name="dependency-mapper",
        agent_type="dependency_mapper",
        analysis_id=analysis_id,
    )


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_with_timeout_error(mock_get_client):
    """Test prompt linking works correctly even when agent times out.

    Scenario: Prompt is linked, then agent times out
    Expected: update_current_generation called before timeout, TimeoutError raised
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    mock_prompt = MagicMock()
    mock_prompt.name = "research-analyst"

    # Create agent that times out
    mock_agent = MagicMock()

    async def slow_invoke(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than timeout
        return {"output": "Should not reach here"}

    mock_agent.ainvoke = slow_invoke

    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Research topic"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation with short timeout
    with pytest.raises(TimeoutError):
        await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="research_analyst",
            timeout=0.5,  # Very short timeout
        )

    # Verify prompt was linked BEFORE timeout occurred
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_with_agent_execution_error(mock_get_client):
    """Test prompt linking works correctly even when agent execution fails.

    Scenario: Prompt is linked, then agent raises exception
    Expected: update_current_generation called before error, original exception raised
    """
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    mock_prompt = MagicMock()
    mock_prompt.name = "code-quality-critic"

    # Create agent that raises exception
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=ValueError("Agent execution failed"))

    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Review code"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should raise ValueError
    with pytest.raises(ValueError, match="Agent execution failed"):
        await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            timeout=30.0,
        )

    # Verify prompt was linked BEFORE agent error occurred
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)

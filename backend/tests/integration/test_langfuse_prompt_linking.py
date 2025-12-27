"""Integration tests for Langfuse prompt linkage in agent invocation (Issue #564).

Tests verify that prompts fetched from Langfuse are properly linked to generation spans
during agent execution via langfuse_prompt metadata in RunnableConfig, with graceful
degradation when Langfuse is unavailable.

The new approach (v3.11+) passes langfuse_prompt in config metadata, which the
CallbackHandler automatically picks up and links to the generation span.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.invocation import invoke_agent


# Helper to create an async side_effect that properly awaits the protected function
async def async_call_impl(f):
    """Properly await the async function passed to circuit_breaker.call()."""
    return await f()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_in_agent_invocation(
    mock_resilience, mock_create_config
):
    """Test that prompt is passed to RunnableConfig metadata during agent invocation.

    Scenario: Agent has langfuse_prompt_client in metadata
    Expected: create_runnable_config is called with langfuse_prompt parameter
    """
    # Mock resilience manager with async call that properly awaits the function
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    # Mock config creation
    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Create mock prompt object (simulates Langfuse TextPromptClient)
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

    # Verify create_runnable_config was called with the prompt
    mock_create_config.assert_called_once_with(langfuse_prompt=mock_prompt)

    # Verify agent was invoked successfully
    assert result == {"output": "Test findings"}
    mock_agent.ainvoke.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_graceful_degradation_langfuse_unavailable(
    mock_resilience, mock_create_config
):
    """Test graceful degradation when extraction raises exception.

    Scenario: Getting metadata raises exception
    Expected: Exception is caught, agent execution continues with None prompt
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    # Mock config creation
    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Create mock agent with broken config that raises on metadata access
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Results"})

    # Config that raises exception when accessing metadata
    mock_config = MagicMock()
    type(mock_config).metadata = property(lambda self: (_ for _ in ()).throw(RuntimeError("broken")))
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Analyze"}]}
    analysis_id = AnalysisID(uuid4())

    # Execute agent invocation - should NOT raise exception
    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify agent was still invoked despite metadata extraction failure
    assert result == {"output": "Results"}
    mock_agent.ainvoke.assert_called_once()

    # Verify create_runnable_config was called with None (graceful degradation)
    mock_create_config.assert_called_once_with(langfuse_prompt=None)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_skipped_for_cache_hits(mock_resilience, mock_create_config):
    """Test that prompt linkage is skipped for cache hits (None client).

    Scenario: Agent metadata has None for langfuse_prompt_client (cache hit)
    Expected: create_runnable_config called with langfuse_prompt=None
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Create agent with None prompt client (simulates L1/L2 cache hit)
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Cached results"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": None}  # Cache hit
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify create_runnable_config was called with None
    mock_create_config.assert_called_once_with(langfuse_prompt=None)
    assert result == {"output": "Cached results"}


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_skipped_when_config_missing(mock_resilience, mock_create_config):
    """Test handling when agent has no config.

    Scenario: Agent has no config attribute
    Expected: Graceful degradation, agent execution continues
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Agent without config
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Results"})
    mock_agent.config = None  # No config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify create_runnable_config was called with None
    mock_create_config.assert_called_once_with(langfuse_prompt=None)
    assert result == {"output": "Results"}


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_skipped_when_metadata_is_none(mock_resilience, mock_create_config):
    """Test handling when agent config has None metadata.

    Scenario: Agent config exists but metadata is None
    Expected: Graceful degradation, agent execution continues
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Agent with config but no metadata
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Results"})
    mock_config = MagicMock()
    mock_config.metadata = None
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify create_runnable_config was called with None
    mock_create_config.assert_called_once_with(langfuse_prompt=None)
    assert result == {"output": "Results"}


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_with_timeout_error(mock_resilience, mock_create_config):
    """Test that prompt linkage works even when agent times out.

    Scenario: Agent has prompt in metadata but times out during execution
    Expected: create_runnable_config still called with prompt, TimeoutError raised
    """
    # Mock resilience manager with timeout
    mock_circuit = MagicMock()

    async def timeout_call(f):
        raise TimeoutError("Agent timed out")

    mock_circuit.call = AsyncMock(side_effect=timeout_call)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    mock_prompt = MagicMock()
    mock_prompt.name = "timeout-test"

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Never reached"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    with pytest.raises(TimeoutError):
        await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="test_agent",
            timeout=30.0,
        )

    # Verify create_runnable_config was called with the prompt
    # (prompt extraction happens before timeout)
    mock_create_config.assert_called_once_with(langfuse_prompt=mock_prompt)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_with_agent_execution_error(mock_resilience, mock_create_config):
    """Test that prompt linkage occurs even when agent raises exception.

    Scenario: Agent has prompt but raises exception during execution
    Expected: create_runnable_config still called with prompt, exception propagated
    """
    # Mock resilience manager that propagates error
    mock_circuit = MagicMock()

    async def error_call(f):
        return await f()  # Let the agent raise its error

    mock_circuit.call = AsyncMock(side_effect=error_call)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    mock_prompt = MagicMock()
    mock_prompt.name = "error-test"

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(side_effect=ValueError("Agent failed"))
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    with pytest.raises(ValueError, match="Agent failed"):
        await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="test_agent",
            timeout=30.0,
        )

    # Verify create_runnable_config was called with the prompt
    mock_create_config.assert_called_once_with(langfuse_prompt=mock_prompt)


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
@patch("app.domains.analysis.workflows.agents.invocation.logger")
async def test_prompt_linkage_logs_debug_message(
    mock_logger, mock_resilience, mock_create_config
):
    """Test that debug log is emitted when prompt is extracted.

    Scenario: Agent has valid prompt in metadata
    Expected: Debug log with prompt name is emitted
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    mock_prompt = MagicMock()
    mock_prompt.name = "logging-test"

    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Results"})
    mock_config = MagicMock()
    mock_config.metadata = {"langfuse_prompt_client": mock_prompt}
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify debug log was called
    mock_logger.debug.assert_any_call(
        "prompt_extracted_for_linkage",
        prompt_name="logging-test",
        agent_type="test_agent",
        analysis_id=analysis_id,
    )


@pytest.mark.asyncio
@pytest.mark.integration
@patch("app.domains.analysis.workflows.agents.invocation.create_runnable_config")
@patch("app.domains.analysis.workflows.agents.invocation.get_resilience_manager")
async def test_prompt_linkage_with_get_client_returning_none(
    mock_resilience, mock_create_config
):
    """Test handling when langfuse_prompt_client key doesn't exist.

    Scenario: Agent metadata exists but has no langfuse_prompt_client key
    Expected: Graceful handling, None passed to create_runnable_config
    """
    # Mock resilience manager
    mock_circuit = MagicMock()
    mock_circuit.call = AsyncMock(side_effect=async_call_impl)
    mock_circuit.state.value = "closed"
    mock_resilience.return_value.get_circuit_breaker.return_value = mock_circuit

    mock_create_config.return_value = {"callbacks": [], "metadata": {}}

    # Agent with metadata but no langfuse_prompt_client key
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "Results"})
    mock_config = MagicMock()
    mock_config.metadata = {"other_key": "value"}  # No langfuse_prompt_client
    mock_agent.config = mock_config

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}
    analysis_id = AnalysisID(uuid4())

    result = await invoke_agent(
        agent=mock_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="test_agent",
        timeout=30.0,
    )

    # Verify create_runnable_config was called with None
    mock_create_config.assert_called_once_with(langfuse_prompt=None)
    assert result == {"output": "Results"}

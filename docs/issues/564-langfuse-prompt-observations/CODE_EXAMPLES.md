# Issue #564: Langfuse Prompt Observation Linking - Code Examples

**Status:** Design Complete
**Date:** December 27, 2025

---

## Example 1: PromptManager Enhancement

### File: `backend/app/shared/services/prompts/prompt_manager.py`

**Add new method after existing `get_prompt()` method (~line 1466):**

```python
async def get_prompt_with_langfuse_client(
    self,
    name: str,
    variables: dict[str, Any] | None = None,
    label: str = "production",
) -> tuple[str, Any | None]:
    """Get prompt content AND Langfuse client object for observation linking.

    This method enables Langfuse prompt observation linking (Issue #564) by
    returning both the compiled prompt content and the TextPromptClient object.

    Caching behavior:
    - L1/L2 cache hits: Return (content, None) - fast but no linkage
    - L3 Langfuse fetch: Return (content, TextPromptClient) - slower but linkable
    - Hardcoded fallback: Return (content, None) - offline mode

    Args:
        name: Prompt name (e.g., "analysis-agent-tech-comparator")
        variables: Variables for prompt compilation
        label: Prompt label/version (default: "production")

    Returns:
        Tuple of (compiled_prompt_string, langfuse_client_or_none)

    Raises:
        ValueError: If prompt not found in any source

    Example:
        >>> prompt, client = await manager.get_prompt_with_langfuse_client(
        ...     name="analysis-agent-tech-comparator",
        ...     variables={"skill_instructions": "..."},
        ...     label="production",
        ... )
        >>> # If client is not None, it can be linked to generation
        >>> if client:
        ...     langfuse.update_current_generation(prompt=client)

    """
    variables = variables or {}

    # L1 Cache: In-memory LRU
    cached_prompt = await self._get_from_l1_cache(name, label)
    if cached_prompt:
        self._record_prompt_observation(name, label, "l1_cache", "cached")
        return self._compile_prompt(cached_prompt, variables), None

    # L2 Cache: Redis
    cached_prompt = await self._get_from_l2_cache(name, label)
    if cached_prompt:
        # Populate L1 cache
        self.l1_cache.set(self._build_cache_key(name, label), cached_prompt)
        self._record_prompt_observation(name, label, "l2_cache", "cached")
        return self._compile_prompt(cached_prompt, variables), None

    # L3 Source: Langfuse API - CRITICAL PATH FOR LINKAGE
    prompt_obj = await self._fetch_from_langfuse(name, label)
    if prompt_obj:
        prompt_content = prompt_obj["prompt"]
        langfuse_client = prompt_obj.get("langfuse_client")  # NEW: Get client object

        # Only use Langfuse prompt if it has content
        if prompt_content and prompt_content.strip():
            # Cache content only (not client object - not serializable)
            await self._cache_prompt(name, label, prompt_content)
            self._record_prompt_observation(
                name, label, "langfuse", prompt_obj.get("version", "unknown")
            )
            # Return BOTH compiled content and client object
            return self._compile_prompt(prompt_content, variables), langfuse_client

        logger.warning(
            "prompt_langfuse_empty",
            name=name,
            label=label,
            message="Langfuse prompt is empty, falling back to hardcoded",
        )

    # Fallback: Hardcoded prompts
    hardcoded_prompt = self._get_hardcoded_prompt(name)
    if hardcoded_prompt:
        # Don't cache hardcoded prompts (they're already in memory)
        self._record_prompt_observation(name, label, "hardcoded", "embedded")
        return self._compile_prompt(hardcoded_prompt, variables), None

    # Not found anywhere
    msg = f"Prompt '{name}' not found in Langfuse or hardcoded fallbacks"
    logger.error("prompt_not_found", name=name, label=label)
    raise ValueError(msg)
```

**Modify existing `_fetch_from_langfuse()` method (~line 1205):**

```python
async def _fetch_from_langfuse(self, name: str, label: str) -> dict[str, Any] | None:
    """Fetch prompt from Langfuse API.

    Issue #564: Now returns the TextPromptClient object for observation linking.

    Args:
        name: Prompt name
        label: Prompt label

    Returns:
        Prompt object with 'prompt', 'version', 'config', and 'langfuse_client' keys,
        or None if not found

    """
    if not self.langfuse_client:
        logger.debug(
            "prompt_langfuse_disabled",
            name=name,
            label=label,
        )
        return None

    try:
        # Fetch prompt from Langfuse
        prompt_obj = self.langfuse_client.get_prompt(
            name=name,
            label=label,
        )

        if not prompt_obj:
            logger.warning(
                "prompt_langfuse_not_found",
                name=name,
                label=label,
            )
            return None

        logger.info(
            "prompt_langfuse_fetched",
            name=name,
            label=label,
            version=prompt_obj.version,
        )

        return {
            "prompt": prompt_obj.prompt,
            "version": prompt_obj.version,
            "config": prompt_obj.config,
            "langfuse_client": prompt_obj,  # NEW: Store TextPromptClient object
        }

    except Exception as e:
        logger.error(
            "prompt_langfuse_fetch_failed",
            name=name,
            label=label,
            error=str(e),
            exc_info=True,
        )
        return None
```

---

## Example 2: Agent Factory Enhancement

### File: `backend/app/domains/analysis/workflows/agents/tech_comparator.py`

**Modify `run_tech_comparator()` function (~line 110):**

```python
async def run_tech_comparator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run tech comparator agent to analyze and compare technologies.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced technology comparison

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    expectation = state.get("agent_expectation")
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))

    # Issue #564: Fetch prompt WITH Langfuse client object for observation linking
    prompt_manager = get_prompt_manager()
    system_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        name=PROMPT_NAME,
        variables={"skill_instructions": skill_instructions},
        label="production",
    )

    logger.info(
        "tech_comparator_prompt_fetched",
        analysis_id=str(analysis_id),
        has_langfuse_client=langfuse_prompt_client is not None,
        prompt_version=getattr(langfuse_prompt_client, "version", "unknown"),
    )

    # Create agent with prompt client for linkage
    agent = await create_tech_comparator_agent_with_few_shot(
        content=content,
        system_prompt=system_prompt,
        response_schema=TechComparison,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
        langfuse_prompt_client=langfuse_prompt_client,  # NEW: Pass to factory
    )

    # ... rest of the function unchanged ...
```

---

## Example 3: Factory Layer Enhancement

### File: `backend/app/domains/analysis/workflows/agents/factories.py`

**Modify `create_agent_with_optional_few_shot()` function (~line 137):**

```python
async def create_agent_with_optional_few_shot(
    agent_type: str,
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
    tools: Sequence[BaseTool] | None = None,
    tool_call_config: ToolCallConfig | None = None,
    langfuse_prompt_client: Any | None = None,  # NEW: Carry prompt object
) -> Runnable:
    """Create agent with optional few-shot prompting based on feature flags.

    This is the core factory function that all agent-specific factories delegate to.

    Args:
        agent_type: Type of agent (e.g., 'tech_comparator', 'security_auditor')
        content: Input content for analysis (used for semantic example search)
        system_prompt: Base system prompt for the agent
        response_schema: Pydantic model defining expected output structure
        analysis_id: UUID of the analysis (for deterministic variant assignment)
        session: Database session for example retrieval
        tools: Optional MCP tools for tool-enabled agents
        tool_call_config: Optional tool call configuration
        langfuse_prompt_client: Optional Langfuse TextPromptClient for observation linking

    Returns:
        Runnable: Agent instance (with or without few-shot examples)

    """
    config = get_technique_config()

    # Get variant (always "treatment" as of Dec 2025 - features always enabled)
    variant_selector = get_variant_selector()
    variant = variant_selector.select_variant(
        analysis_id=str(analysis_id),
        technique="few_shot_prompting",
    )

    logger.info(
        "few_shot_agent_creating",
        agent_type=agent_type,
        analysis_id=str(analysis_id),
        variant=variant,
        has_langfuse_prompt=langfuse_prompt_client is not None,
    )

    # Create base agent factory for few-shot wrapper
    def base_agent_factory(**kwargs: Any) -> Runnable:
        """Create baseline agent with optional prompt enhancement."""
        prompt = kwargs.get("system_prompt", system_prompt)
        if tools:
            return create_tool_enabled_agent(
                agent_type=agent_type,
                response_schema=response_schema,
                tools=tools,
                tool_call_config=tool_call_config,
                system_prompt=prompt,
            )
        return create_structured_agent(
            agent_type=agent_type,
            response_schema=response_schema,
            system_prompt=prompt,
        )

    # Create agent (with or without few-shot based on variant)
    if variant == "treatment" and config.few_shot_prompting.enabled:
        agent = await create_few_shot_agent(
            agent_type=agent_type,
            content=content,
            base_agent_factory=base_agent_factory,
            response_schema=response_schema,
            analysis_id=analysis_id,
            session=session,
            config=config.few_shot_prompting,
            system_prompt=system_prompt,
        )
    else:
        # Control variant or feature disabled
        agent = base_agent_factory(system_prompt=system_prompt)

    # Issue #564: Attach Langfuse prompt client to agent config for later linking
    if langfuse_prompt_client:
        agent = agent.with_config(
            metadata={
                "langfuse_prompt_client": langfuse_prompt_client,
                "agent_type": agent_type,
                "analysis_id": str(analysis_id),
            }
        )
        logger.debug(
            "langfuse_prompt_attached_to_agent",
            agent_type=agent_type,
            prompt_name=langfuse_prompt_client.name,
            prompt_version=langfuse_prompt_client.version,
        )

    return agent
```

**Add new helper for agent-specific factories (~line 300):**

```python
async def create_tech_comparator_agent_with_few_shot(
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
    tools: Sequence[BaseTool] | None = None,
    langfuse_prompt_client: Any | None = None,  # NEW: Accept prompt client
) -> Runnable:
    """Create tech comparator agent with optional few-shot prompting.

    Args:
        content: Input content for semantic example search
        system_prompt: Base system prompt
        response_schema: Expected output schema
        analysis_id: Analysis UUID for variant assignment
        session: Database session for example retrieval
        tools: Optional MCP tools
        langfuse_prompt_client: Optional Langfuse prompt client for observation linking

    Returns:
        Configured agent runnable

    """
    return await create_agent_with_optional_few_shot(
        agent_type="tech_comparator",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
        langfuse_prompt_client=langfuse_prompt_client,  # NEW: Pass through
    )
```

---

## Example 4: Invocation Layer Enhancement

### File: `backend/app/domains/analysis/workflows/agents/invocation.py`

**Modify `invoke_agent()` function (~line 42):**

```python
from langfuse import get_client, observe

@observe(as_type="generation", name="agent_llm_call", capture_input=True, capture_output=True)
async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, Any],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float = AGENT_TIMEOUT,
) -> Any:
    """Invoke agent with timeout and Langfuse observation tracking.

    Issue #564: Links Langfuse prompt to generation span if available.

    Args:
        agent: Agent runnable to invoke
        input_messages: Input messages for the agent
        analysis_id: Analysis UUID
        agent_type: Type of agent being invoked
        timeout: Timeout in seconds

    Returns:
        Agent output (structured response)

    Raises:
        TimeoutError: If agent execution exceeds timeout
        Exception: If agent execution fails

    """
    # Issue #564: Link prompt to generation span if available
    try:
        langfuse = get_client()
        agent_config = getattr(agent, "config", {})
        metadata = agent_config.get("metadata", {})
        prompt_client = metadata.get("langfuse_prompt_client")

        if prompt_client and langfuse:
            # Link prompt to current generation
            # This creates the prompt observation linkage in Langfuse
            langfuse.update_current_generation(prompt=prompt_client)

            logger.debug(
                "prompt_linked_to_generation",
                agent_type=agent_type,
                analysis_id=str(analysis_id),
                prompt_name=prompt_client.name,
                prompt_version=prompt_client.version,
                prompt_label=getattr(prompt_client, "label", "unknown"),
            )
        else:
            logger.debug(
                "no_prompt_client_available",
                agent_type=agent_type,
                analysis_id=str(analysis_id),
                reason="cached_prompt_or_hardcoded_fallback",
            )

    except Exception as e:  # noqa: BLE001
        # Graceful degradation - don't fail invocation if linking fails
        logger.warning(
            "prompt_linking_failed",
            agent_type=agent_type,
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True,
        )

    # Existing timeout logic (unchanged)
    try:
        result = await asyncio.wait_for(
            agent.ainvoke(input_messages),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError as exc:
        logger.exception(
            "timeout_error",
            context=f"Agent {agent_type} execution",
            timeout=timeout,
            agent_type=agent_type,
            analysis_id=analysis_id,
        )
        msg = f"Agent {agent_type} execution exceeded timeout of {timeout}s"
        raise TimeoutError(msg) from exc
```

---

## Example 5: Test Coverage

### File: `backend/tests/unit/shared/services/prompts/test_prompt_manager_langfuse_linking.py` (NEW)

```python
"""Tests for Langfuse prompt observation linking (Issue #564)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.services.prompts.prompt_manager import PromptManager


@pytest.mark.asyncio
async def test_get_prompt_with_langfuse_client_from_l1_cache():
    """L1 cache hit returns (content, None) - no client object."""
    manager = PromptManager(enable_langfuse=False, enable_redis=False)

    # Populate L1 cache
    manager.l1_cache.set("prompt:test:production", "Hello {name}")

    content, client = await manager.get_prompt_with_langfuse_client(
        name="test",
        variables={"name": "World"},
        label="production",
    )

    assert content == "Hello World"
    assert client is None  # Cache hit = no client


@pytest.mark.asyncio
@patch("app.shared.services.prompts.prompt_manager.create_redis_client")
async def test_get_prompt_with_langfuse_client_from_l2_cache(mock_redis):
    """L2 cache hit returns (content, None) - no client object."""
    # Mock Redis client
    mock_redis_instance = MagicMock()
    mock_redis_instance.get.return_value = b"Hello {name}"
    mock_redis.return_value = mock_redis_instance

    manager = PromptManager(enable_langfuse=False, enable_redis=True)

    content, client = await manager.get_prompt_with_langfuse_client(
        name="test",
        variables={"name": "World"},
        label="production",
    )

    assert content == "Hello World"
    assert client is None  # Cache hit = no client


@pytest.mark.asyncio
@patch("app.shared.services.prompts.prompt_manager.get_langfuse_service")
async def test_get_prompt_with_langfuse_client_from_langfuse(mock_get_service):
    """L3 Langfuse fetch returns (content, TextPromptClient) - linkable."""
    # Mock Langfuse client and prompt object
    mock_prompt = MagicMock()
    mock_prompt.prompt = "Hello {name}"
    mock_prompt.version = 42
    mock_prompt.config = {}
    mock_prompt.name = "test"
    mock_prompt.label = "production"

    mock_sdk_client = MagicMock()
    mock_sdk_client.get_prompt.return_value = mock_prompt

    mock_service = MagicMock()
    mock_service.sdk_client = mock_sdk_client
    mock_get_service.return_value = mock_service

    manager = PromptManager(enable_langfuse=True, enable_redis=False)

    content, client = await manager.get_prompt_with_langfuse_client(
        name="test",
        variables={"name": "World"},
        label="production",
    )

    assert content == "Hello World"
    assert client is not None  # Langfuse fetch = client provided
    assert client.name == "test"
    assert client.version == 42
    assert client.label == "production"


@pytest.mark.asyncio
async def test_get_prompt_with_langfuse_client_from_hardcoded():
    """Hardcoded fallback returns (content, None) - no client."""
    manager = PromptManager(enable_langfuse=False, enable_redis=False)

    content, client = await manager.get_prompt_with_langfuse_client(
        name="analysis-supervisor-routing",
        variables={"agent_list": "- agent1\n- agent2"},
        label="production",
    )

    assert "Analyze content and select relevant agents" in content
    assert "agent1" in content
    assert client is None  # Hardcoded = no client


@pytest.mark.asyncio
async def test_get_prompt_with_langfuse_client_not_found():
    """Prompt not found anywhere raises ValueError."""
    manager = PromptManager(enable_langfuse=False, enable_redis=False)

    with pytest.raises(ValueError, match="Prompt 'nonexistent' not found"):
        await manager.get_prompt_with_langfuse_client(
            name="nonexistent",
            label="production",
        )
```

### File: `backend/tests/integration/test_langfuse_prompt_linking.py` (NEW)

```python
"""Integration test for Langfuse prompt observation linking (Issue #564)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_in_agent_invocation(mock_get_client):
    """Test that prompt is linked to generation span during agent invocation."""

    # Mock Langfuse client
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Mock prompt client
    mock_prompt = MagicMock()
    mock_prompt.name = "analysis-agent-tech-comparator"
    mock_prompt.version = 1
    mock_prompt.label = "production"

    # Create agent with prompt client in config
    from app.core.model_factory import get_chat_model
    from app.domains.analysis.schemas.agents.tech_comparator import TechComparison

    agent = get_chat_model().with_structured_output(TechComparison, strict=True)
    agent = agent.with_config(
        metadata={
            "langfuse_prompt_client": mock_prompt,
            "agent_type": "tech_comparator",
        }
    )

    # Invoke agent
    from app.domains.analysis.workflows.agents.invocation import invoke_agent

    input_messages = {
        "messages": [
            {
                "role": "user",
                "content": "Compare React vs Vue for a new project",
            }
        ]
    }

    # Patch the actual agent invoke to avoid real LLM call
    mock_result = {
        "primary_tech": "React 18.2.0",
        "alternatives": ["Vue 3.3.4", "Svelte 4.0.0"],
        "comparison": {
            "React 18.2.0": {
                "pros": ["Large ecosystem", "Strong typing with TypeScript"],
                "cons": ["Steep learning curve"],
                "use_cases": ["Large SPAs"],
            }
        },
        "recommendation": "Use React for large teams",
        "confidence_score": 0.85,
    }

    with patch.object(agent, "ainvoke", new=AsyncMock(return_value=mock_result)):
        result = await invoke_agent(
            agent=agent,
            input_messages=input_messages,
            analysis_id="test-analysis-id",
            agent_type="tech_comparator",
        )

    # Verify that update_current_generation was called with prompt
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)

    # Verify result was returned correctly
    assert result["primary_tech"] == "React 18.2.0"
```

---

## Example 6: Full E2E Flow

Here's how the complete flow works in practice:

```python
# 1. WORKFLOW NODE CALLS AGENT
# File: backend/app/domains/analysis/workflows/nodes/agents/tech_comparator_node.py

@observe(as_type="agent", name="tech_comparator", capture_input=True, capture_output=True)
async def tech_comparator_node(state: AnalysisState) -> dict:
    """Tech comparator agent node."""
    # ... extract state data ...

    result = await run_tech_comparator(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=session,
        state=state,
        tools=None,
    )

    return {"agent_outputs": {**state.get("agent_outputs", {}), **{result["agent_type"]: result}}}


# 2. AGENT FETCHES PROMPT WITH CLIENT
# File: backend/app/domains/analysis/workflows/agents/tech_comparator.py

async def run_tech_comparator(...) -> dict[str, object]:
    prompt_manager = get_prompt_manager()

    # Fetch prompt with Langfuse client
    system_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        name="analysis-agent-tech-comparator",
        variables={"skill_instructions": skill_instructions},
        label="production",
    )

    # Create agent with prompt client
    agent = await create_tech_comparator_agent_with_few_shot(
        content=content,
        system_prompt=system_prompt,
        response_schema=TechComparison,
        analysis_id=analysis_id,
        session=session,
        langfuse_prompt_client=langfuse_prompt_client,  # Pass client
    )

    # Execute agent
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        session=session,
    )


# 3. FACTORY ATTACHES CLIENT TO AGENT
# File: backend/app/domains/analysis/workflows/agents/factories.py

async def create_agent_with_optional_few_shot(..., langfuse_prompt_client=None):
    # ... create agent ...

    # Attach prompt client to agent metadata
    if langfuse_prompt_client:
        agent = agent.with_config(
            metadata={"langfuse_prompt_client": langfuse_prompt_client}
        )

    return agent


# 4. INVOCATION LINKS PROMPT TO GENERATION
# File: backend/app/domains/analysis/workflows/agents/invocation.py

@observe(as_type="generation", name="agent_llm_call")
async def invoke_agent(agent, input_messages, analysis_id, agent_type, timeout):
    # Extract prompt client from agent config
    langfuse = get_client()
    prompt_client = agent.config.get("metadata", {}).get("langfuse_prompt_client")

    # Link prompt to current generation
    if prompt_client and langfuse:
        langfuse.update_current_generation(prompt=prompt_client)
        # ✅ THIS CREATES THE PROMPT OBSERVATION LINKAGE

    # Invoke LLM
    result = await asyncio.wait_for(agent.ainvoke(input_messages), timeout=timeout)
    return result


# 5. LANGFUSE UI NOW SHOWS OBSERVATION
# Navigate to: https://your-langfuse.com/project/XYZ/prompts/analysis-agent-tech-comparator
# ✅ Number of Observations: 142 (instead of 0)
# ✅ Click observation → see linked generation with input/output
# ✅ Compare prompt versions → A/B test results visible
```

---

## Conclusion

These code examples demonstrate:

✅ **Minimal changes** - only 4 files modified
✅ **Backward compatibility** - existing `get_prompt()` unchanged
✅ **Graceful degradation** - works with or without Langfuse
✅ **Comprehensive testing** - unit + integration coverage
✅ **Production-ready** - proper error handling and logging

**Next step:** Implement Phase 1 (PromptManager enhancement) and test with pilot agents.

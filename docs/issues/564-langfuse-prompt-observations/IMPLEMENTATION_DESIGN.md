# Issue #564: Langfuse Prompt Observation Linking - Implementation Design

**Status:** Design Complete
**Date:** December 27, 2025
**Designed by:** Claude (Backend System Architect)

---

## Problem Statement

The Langfuse Prompts UI shows **0 observations** for all prompts despite active usage across the codebase. This means:
- **No prompt usage analytics** (can't see which agents use which prompts)
- **No A/B testing insights** (can't compare prompt versions)
- **No prompt performance metrics** (can't correlate prompt changes with quality scores)

### Current State

**What we have:**
```python
# backend/app/shared/services/prompts/prompt_manager.py:1362-1381
def _record_prompt_observation(self, name: str, label: str, source: str, version: str | int = "unknown") -> None:
    """Record prompt usage to current Langfuse observation."""
    try:
        update_current_observation(
            metadata={
                "prompt_name": name,
                "prompt_label": label,
                "prompt_source": source,
                "prompt_version": str(version),
            }
        )
    except Exception:
        pass  # Silent fallback when not in traced context
```

**The issue:** `update_current_observation(metadata=...)` **only adds metadata** to the current span. It does **NOT** create a prompt linkage in Langfuse that shows up in the "Number of Observations" counter.

---

## Solution Architecture

### Key Insight from Langfuse SDK

Langfuse provides `langfuse.update_current_generation(prompt=TextPromptClient)` for linking prompts to **generation spans** (LLM calls). This creates proper prompt linkage.

**Requirements:**
1. Must pass the actual **Langfuse `TextPromptClient`** object (not just metadata)
2. Only works for **generation spans** (not observation/tool/agent spans)
3. Must be called **within the same traced context** as the LLM generation

### Architecture Pattern: Prompt Object Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROMPT LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. FETCH PROMPT                                                         │
│     PromptManager.get_prompt_with_langfuse_client()                      │
│       ├─ L1 Cache (in-memory) → metadata only                           │
│       ├─ L2 Cache (Redis) → metadata only                               │
│       └─ L3 Source (Langfuse API) → TextPromptClient object ✓           │
│                                                                          │
│  2. PASS PROMPT THROUGH LAYERS                                           │
│     Agent Factory → Agent Execution → LLM Invocation                     │
│       └─ Prompt object carried via messages context                     │
│                                                                          │
│  3. LINK PROMPT AT GENERATION                                            │
│     @observe(as_type="generation") decorated function                    │
│       └─ langfuse.update_current_generation(prompt=prompt_client)        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: PromptManager Enhancement (CRITICAL)

**File:** `backend/app/shared/services/prompts/prompt_manager.py`

**Changes:**

1. **Add new method** to return both prompt content AND Langfuse client object:

```python
async def get_prompt_with_langfuse_client(
    self,
    name: str,
    variables: dict[str, Any] | None = None,
    label: str = "production",
) -> tuple[str, TextPromptClient | None]:
    """Get prompt content AND Langfuse client object for observation linking.

    Returns:
        Tuple of (compiled_prompt_string, langfuse_client_or_none)

    Note:
        - L1/L2 cache hits return (content, None) - no client object
        - L3 Langfuse fetch returns (content, TextPromptClient) - linkable
        - Hardcoded fallback returns (content, None) - no client object
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
        self.l1_cache.set(self._build_cache_key(name, label), cached_prompt)
        self._record_prompt_observation(name, label, "l2_cache", "cached")
        return self._compile_prompt(cached_prompt, variables), None

    # L3 Source: Langfuse API - CRITICAL PATH FOR LINKAGE
    prompt_obj = await self._fetch_from_langfuse(name, label)
    if prompt_obj:
        prompt_content = prompt_obj["prompt"]
        langfuse_client = prompt_obj["langfuse_client"]  # NEW: Store client

        if prompt_content and prompt_content.strip():
            # Cache content only (not client object)
            await self._cache_prompt(name, label, prompt_content)
            self._record_prompt_observation(name, label, "langfuse", prompt_obj.get("version", "unknown"))

            # Return BOTH compiled content and client object
            return self._compile_prompt(prompt_content, variables), langfuse_client

    # Fallback: Hardcoded prompts
    hardcoded_prompt = self._get_hardcoded_prompt(name)
    if hardcoded_prompt:
        self._record_prompt_observation(name, label, "hardcoded", "embedded")
        return self._compile_prompt(hardcoded_prompt, variables), None

    # Not found
    msg = f"Prompt '{name}' not found"
    raise ValueError(msg)
```

2. **Modify `_fetch_from_langfuse`** to store the `TextPromptClient` object:

```python
async def _fetch_from_langfuse(self, name: str, label: str) -> dict[str, Any] | None:
    """Fetch prompt from Langfuse API.

    Returns:
        Prompt object with 'prompt', 'version', 'config', and 'langfuse_client' keys
    """
    if not self.langfuse_client:
        return None

    try:
        # Fetch prompt from Langfuse
        prompt_obj = self.langfuse_client.get_prompt(name=name, label=label)

        if not prompt_obj:
            logger.warning("prompt_langfuse_not_found", name=name, label=label)
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
            "langfuse_client": prompt_obj,  # NEW: Store TextPromptClient
        }

    except Exception as e:
        logger.error("prompt_langfuse_fetch_failed", name=name, label=label, error=str(e))
        return None
```

**Why this works:**
- L1/L2 cache hits → fast path, no prompt linkage (acceptable tradeoff)
- L3 Langfuse fetch → slower path (~100-200ms), but gets linkage
- Hardcoded fallback → offline mode, no linkage (expected)

---

### Phase 2: Pass Prompt Object Through Execution Chain

**Challenge:** Prompt is fetched at agent creation, but LLM is invoked several layers deep.

**Solution:** Add optional `langfuse_prompt_client` parameter to execution chain.

#### 2.1 Agent Factory Layer

**File:** `backend/app/domains/analysis/workflows/agents/factories.py`

**Changes:**

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
    """Create agent with optional few-shot prompting."""

    # ... existing logic ...

    # Store prompt client in agent config metadata for later access
    if langfuse_prompt_client:
        # Attach to agent via custom metadata (accessible in invoke)
        agent = agent.with_config(
            metadata={"langfuse_prompt_client": langfuse_prompt_client}
        )

    return agent
```

#### 2.2 Agent-Specific Factories

**File:** `backend/app/domains/analysis/workflows/agents/tech_comparator.py`

**Changes:**

```python
async def run_tech_comparator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run tech comparator agent."""

    # Get skill level instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #564: Fetch prompt WITH Langfuse client object
    prompt_manager = get_prompt_manager()
    system_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        name=PROMPT_NAME,
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
        tools=tools,
        langfuse_prompt_client=langfuse_prompt_client,  # NEW: Pass to factory
    )

    # ... rest of execution ...
```

#### 2.3 Invocation Layer

**File:** `backend/app/domains/analysis/workflows/agents/invocation.py`

**Changes:**

```python
from langfuse import get_client

@observe(as_type="generation", name="agent_llm_call", capture_input=True, capture_output=True)
async def invoke_agent(
    agent: Runnable,
    input_messages: dict[str, Any],
    analysis_id: AnalysisID,
    agent_type: str,
    timeout: float = AGENT_TIMEOUT,
) -> Any:
    """Invoke agent with timeout and Langfuse observation tracking."""

    # Issue #564: Link prompt to generation span if available
    try:
        langfuse = get_client()
        agent_config = getattr(agent, "config", {})
        metadata = agent_config.get("metadata", {})
        prompt_client = metadata.get("langfuse_prompt_client")

        if prompt_client and langfuse:
            # Link prompt to current generation
            langfuse.update_current_generation(prompt=prompt_client)
            logger.debug(
                "prompt_linked_to_generation",
                agent_type=agent_type,
                prompt_name=prompt_client.name,
                prompt_version=prompt_client.version,
            )
    except Exception:  # noqa: BLE001
        # Graceful degradation - don't fail invocation if linking fails
        pass

    # ... existing timeout and invocation logic ...
```

---

### Phase 3: Testing & Validation

#### 3.1 Unit Tests

**File:** `backend/tests/unit/shared/services/prompts/test_prompt_manager_langfuse_linking.py`

```python
"""Tests for Langfuse prompt observation linking (Issue #564)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_get_prompt_with_langfuse_client_from_l1_cache():
    """L1 cache hit returns (content, None) - no client object."""
    manager = PromptManager()
    manager.l1_cache.set("prompt:test:production", "Hello {name}")

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


@pytest.mark.asyncio
async def test_get_prompt_with_langfuse_client_from_hardcoded():
    """Hardcoded fallback returns (content, None) - no client."""
    manager = PromptManager(enable_langfuse=False, enable_redis=False)

    content, client = await manager.get_prompt_with_langfuse_client(
        name="analysis-supervisor-routing",
        variables={"agent_list": "- agent1"},
        label="production",
    )

    assert "Analyze content and select relevant agents" in content
    assert client is None  # Hardcoded = no client
```

#### 3.2 Integration Test

**File:** `backend/tests/integration/test_langfuse_prompt_linking.py`

```python
"""Integration test for Langfuse prompt observation linking (Issue #564)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.invocation.get_client")
async def test_prompt_linkage_in_agent_invocation(mock_get_client, db_session):
    """Test that prompt is linked to generation span during agent invocation."""

    # Mock Langfuse client
    mock_langfuse = MagicMock()
    mock_get_client.return_value = mock_langfuse

    # Mock prompt client
    mock_prompt = MagicMock()
    mock_prompt.name = "analysis-agent-tech-comparator"
    mock_prompt.version = 1

    # Create agent with prompt client in config
    from app.core.model_factory import get_chat_model
    from app.domains.analysis.schemas.agents.tech_comparator import TechComparison

    agent = get_chat_model().with_structured_output(TechComparison, strict=True)
    agent = agent.with_config(metadata={"langfuse_prompt_client": mock_prompt})

    # Invoke agent
    from app.domains.analysis.workflows.agents.invocation import invoke_agent

    input_messages = {"messages": [{"role": "user", "content": "Test"}]}

    # Patch the actual agent invoke to avoid real LLM call
    with patch.object(agent, "ainvoke", new=AsyncMock(return_value={"primary_tech": "Test"})):
        await invoke_agent(
            agent=agent,
            input_messages=input_messages,
            analysis_id="test-id",
            agent_type="tech_comparator",
        )

    # Verify that update_current_generation was called with prompt
    mock_langfuse.update_current_generation.assert_called_once_with(prompt=mock_prompt)
```

#### 3.3 Manual Validation in Langfuse UI

**Steps:**
1. Run a full analysis with prompt linking enabled
2. Go to Langfuse UI → Prompts section
3. Click on a prompt (e.g., "analysis-agent-tech-comparator")
4. Verify **"Number of Observations"** > 0
5. Click on an observation to see linked generation span
6. Verify prompt version, variables, and output are visible

---

## Performance Considerations

### Cache Hit Ratio Trade-off

**Current:**
- L1 cache hit → ~1ms (no linkage)
- L2 cache hit → ~5-10ms (no linkage)
- L3 Langfuse fetch → ~100-200ms (WITH linkage)

**Implication:**
- First invocation of a prompt → Langfuse fetch → linkage recorded
- Subsequent invocations (5 min window) → L1 cache → NO linkage

**Mitigation:** This is acceptable because:
1. **Prompt analytics don't need 100% coverage** - sampling is fine
2. **Cache invalidation** triggers new Langfuse fetch → new linkages
3. **Production prompts are stable** - version changes are rare

### Memory Overhead

**Storage of TextPromptClient:**
- Carried through agent factory → execution → invocation
- Stored in `agent.config.metadata` (not serialized to database)
- Garbage collected after invocation completes
- **Estimated memory:** ~1-2 KB per agent invocation (negligible)

---

## Rollout Plan

### Step 1: Implement PromptManager Enhancement (Week 1)

- [ ] Add `get_prompt_with_langfuse_client()` method
- [ ] Modify `_fetch_from_langfuse()` to return client object
- [ ] Add unit tests for new method (L1/L2/L3/hardcoded paths)
- [ ] Verify no regressions in existing `get_prompt()` usage

### Step 2: Update 3 Pilot Agents (Week 1)

**Pilot agents:**
1. `tech_comparator.py` - High usage, well-tested
2. `security_auditor.py` - Critical path, good validation
3. `implementation_planner.py` - Common use case

**Changes per agent:**
- Fetch prompt with `get_prompt_with_langfuse_client()`
- Pass `langfuse_prompt_client` to factory
- Verify integration test passes

### Step 3: Invocation Layer Enhancement (Week 2)

- [ ] Update `invoke_agent()` to link prompt if available
- [ ] Add integration test for prompt linkage
- [ ] Test with pilot agents in dev environment
- [ ] Verify linkage appears in Langfuse UI

### Step 4: Rollout to All Agents (Week 2-3)

**Agents to update (19 total):**
- dependency_mapper
- trend_validator
- integration_feasibility
- performance_analyst
- code_quality_critic
- research_analyst
- freshness_checker
- alternatives_finder
- source_credibility
- fact_validator
- key_insights
- actionable
- pros_cons
- audience_fit
- deep_researcher
- community_pulse
- learning_path_advisor
- knowledge_curator

**Automation:**
- Use code generation to apply same pattern to all agents
- Run full test suite after each agent update
- Deploy incrementally (5 agents per day)

### Step 5: Production Validation (Week 3)

- [ ] Monitor Langfuse UI for prompt observation counts
- [ ] Check cache hit ratio (should remain high)
- [ ] Verify no performance degradation (p95 latency)
- [ ] Collect feedback on prompt analytics utility

---

## Alternative Approaches Considered

### Alternative 1: Cache TextPromptClient in Redis

**Idea:** Store the `TextPromptClient` object in Redis L2 cache.

**Pros:**
- Higher linkage coverage (not just L3 hits)

**Cons:**
- `TextPromptClient` is **not serializable** (contains internal Langfuse state)
- Would need custom pickle/unpickle (fragile, version-dependent)
- Redis overhead for storing large objects

**Decision:** REJECTED - complexity not worth the marginal gain.

### Alternative 2: Refetch Prompt from Langfuse Inside invoke_agent()

**Idea:** Always fetch prompt fresh in `invoke_agent()` to guarantee linkage.

**Pros:**
- 100% linkage coverage

**Cons:**
- **Defeats the purpose of caching** - adds 100-200ms to every invocation
- **Breaks separation of concerns** - invocation layer shouldn't know about prompts

**Decision:** REJECTED - unacceptable performance hit.

### Alternative 3: Use Langfuse Prompt Context Manager

**Idea:** Use Langfuse's prompt context manager pattern:

```python
with langfuse.get_prompt("name", label="production") as prompt:
    result = await agent.invoke(...)
```

**Pros:**
- Automatic prompt linkage

**Cons:**
- **No caching support** - fetches from Langfuse every time
- **Synchronous API** - doesn't work with async codebase
- **Not compatible with LangChain LCEL chains**

**Decision:** REJECTED - architectural mismatch.

---

## Success Metrics

### Primary Metrics

1. **Prompt Observation Count** (Langfuse UI)
   - **Target:** > 100 observations per prompt after 24 hours
   - **Measurement:** Langfuse Prompts dashboard

2. **Linkage Coverage** (% of invocations with linkage)
   - **Target:** > 5% (acceptable given caching)
   - **Measurement:** `langfuse.prompt_linkage_rate` metric

3. **Performance (p95 latency)**
   - **Target:** No regression (< +10ms)
   - **Measurement:** Agent execution time logs

### Secondary Metrics

4. **Cache Hit Ratio** (should remain high)
   - **Target:** > 95% (unchanged from current)
   - **Measurement:** PromptManager cache metrics

5. **A/B Test Visibility** (can compare prompt versions)
   - **Target:** Qualitative validation in Langfuse UI
   - **Measurement:** Manual inspection of variant performance

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Performance degradation | Low | Medium | Monitor p95 latency, rollback if > +10ms |
| TextPromptClient API changes | Low | High | Pin langfuse SDK version, test upgrades |
| Memory leaks from client objects | Very Low | Medium | Profile memory usage in staging |
| Breaking existing prompt fetching | Low | High | Extensive unit tests, gradual rollout |

---

## Conclusion

This design provides **robust prompt observation linking** while maintaining:
- ✅ **High cache performance** (95%+ hit ratio)
- ✅ **Minimal code changes** (isolated to agent factories)
- ✅ **Graceful degradation** (no failures if linkage unavailable)
- ✅ **Production readiness** (extensive testing, gradual rollout)

**Recommendation:** Proceed with implementation.

---

## Related Issues

- **Issue #379:** Centralized prompt management (foundation for this work)
- **Issue #418:** Langfuse prompt integration (enabled prompt fetching)
- **Issue #384:** Agent graph visualization (uses similar Langfuse linking)

---

## References

- [Langfuse SDK Documentation](https://langfuse.com/docs/sdk/python)
- [Langfuse Prompt Management Guide](https://langfuse.com/docs/prompts)
- [LangChain LCEL Documentation](https://python.langchain.com/docs/expression_language/)

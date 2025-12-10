# Issue #232: Tool-Enabled Agent Factory - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 5 pts
**GitHub Issue:** [#232](https://github.com/ArieGoldkin/SkillForge/issues/232)
**Blocked By:** #230 (Complete), #231 (Complete)

---

## Objective

Create `create_tool_enabled_agent()` factory function that produces LangChain agents capable of calling MCP tools during their reasoning process while still producing structured output.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Function                                 │
│  (e.g., run_security_auditor)                                   │
├─────────────────────────────────────────────────────────────────┤
│ 1. Check ToolRegistry.is_tool_enabled("agent_type")             │
│ 2. If enabled:                                                   │
│    ├─ Get capabilities from ToolRegistry                        │
│    ├─ Load tools via MCPClientPool                              │
│    └─ Use create_tool_enabled_agent()  ← NEW                    │
│ 3. If disabled:                                                  │
│    └─ Use create_structured_agent()    ← EXISTING               │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               create_tool_enabled_agent()                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. get_chat_model()                                              │
│ 2. model.bind_tools(mcp_tools, parallel_tool_calls=True)        │
│ 3. _enhance_prompt_for_tools(system_prompt, mcp_tools)          │
│ 4. create_agent(..., response_format=ToolStrategy(...))         │
│ 5. Return Runnable                                               │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          run_agent_with_tracking() [UNCHANGED]                   │
│  • invoke_agent() → agent.ainvoke()                              │
│  • Agent reasons with tools (calls MCP servers)                  │
│  • Agent produces structured output                              │
│  • extract_structured_response() validates Pydantic model        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Dual Factory Approach

**Decision:** Create `create_tool_enabled_agent()` alongside existing `create_structured_agent()`

**Rationale:**
- **Backwards Compatible:** Existing agents continue working unchanged
- **Incremental Adoption:** Enable MCP tools per-agent via ToolRegistry
- **Same Execution Path:** Both factories produce Runnables compatible with existing infrastructure
- **Clear Intent:** Function name signals tool capability

### 2. Parallel Tool Calls

**Decision:** Enable `parallel_tool_calls=True` for tool-enabled agents

**Rationale:**
- Multiple tool calls can execute concurrently (e.g., check npm AND pypi)
- Reduces overall agent execution time
- Existing `create_structured_agent()` uses `False` because it has no real tools

### 3. Prompt Enhancement

**Decision:** Auto-inject tool usage guidelines into system prompt

**Rationale:**
- Consistent guidance across all tool-enabled agents
- Reduces duplication in individual agent prompts
- Includes tool descriptions, rate limits, and usage best practices

### 4. Configuration via AgentToolConfig

**Decision:** Use `max_tool_calls` and `tool_timeout` from ToolRegistry config

**Rationale:**
- Centralized configuration in ToolRegistry
- Per-agent rate limiting and timeouts
- Already defined in Issue #231

---

## Files to Create/Modify

### 1. Modify: `backend/app/workflows/agents/base.py`

**Add Functions:**
```python
def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool],
    tool_call_config: ToolCallConfig | None = None,
) -> Runnable:
    """Create agent that can call MCP tools during reasoning.

    Args:
        system_prompt: Base system prompt for the agent
        response_schema: Pydantic model for structured output
        tools: List of MCP tools (pre-filtered by ToolRegistry)
        tool_call_config: Optional config for max_calls, timeout

    Returns:
        Runnable agent with tool calling + structured output
    """

def _build_tool_enhanced_prompt(
    base_prompt: str,
    tools: Sequence[BaseTool],
    max_tool_calls: int,
) -> str:
    """Enhance system prompt with tool usage guidelines."""
```

**Add Dataclass:**
```python
@dataclass
class ToolCallConfig:
    """Configuration for tool-enabled agents."""
    max_tool_calls: int = 10
    parallel_tool_calls: bool = True
```

### 2. Create: `backend/tests/unit/workflows/agents/test_tool_enabled_agent.py`

**Test Cases:**

1. **Factory Tests**
   - test_create_tool_enabled_agent_returns_runnable
   - test_create_tool_enabled_agent_binds_tools
   - test_create_tool_enabled_agent_with_empty_tools_raises
   - test_create_tool_enabled_agent_with_config

2. **Prompt Enhancement Tests**
   - test_build_tool_enhanced_prompt_includes_tool_descriptions
   - test_build_tool_enhanced_prompt_includes_max_calls
   - test_build_tool_enhanced_prompt_preserves_base_prompt

3. **Integration Tests (mocked)**
   - test_tool_enabled_agent_invokes_with_tools
   - test_tool_enabled_agent_produces_structured_output

4. **Comparison Tests**
   - test_structured_agent_unchanged (regression)
   - test_tool_enabled_vs_structured_agent_difference

---

## Implementation Steps

### Step 1: Add ToolCallConfig dataclass
- Define configuration for tool-enabled agents
- Default max_tool_calls=10, parallel_tool_calls=True

### Step 2: Implement _build_tool_enhanced_prompt()
- Accept base prompt, tools list, max calls
- Generate tool descriptions section
- Add usage guidelines section
- Return enhanced prompt

### Step 3: Implement create_tool_enabled_agent()
- Get chat model via get_chat_model()
- Bind tools with parallel_tool_calls from config
- Enhance prompt via _build_tool_enhanced_prompt()
- Create agent with ToolStrategy response format
- Return Runnable

### Step 4: Add structured logging
- Log tool binding at INFO level
- Log prompt enhancement at DEBUG level
- Include tool count in log context

### Step 5: Update __init__.py exports
- Export create_tool_enabled_agent
- Export ToolCallConfig

### Step 6: Write comprehensive unit tests
- Test all factory behaviors
- Test prompt enhancement
- Test with mock tools
- Verify backwards compatibility

### Step 7: Run CI checks
- ruff format, ruff check, mypy
- All tests passing

---

## Prompt Enhancement Template

```python
TOOL_USAGE_TEMPLATE = '''
## Available Tools

You have access to the following tools for real-time data lookup:

{tool_descriptions}

## Tool Usage Guidelines

1. **Verify claims:** Use tools to check specific versions, CVEs, package info
2. **Be efficient:** Maximum {max_tool_calls} tool calls allowed
3. **Handle failures gracefully:** If a tool fails, note the gap in your findings
4. **Cite sources:** Reference tool results (e.g., "Per npm registry, v3.0.0...")
5. **Don't over-rely:** Trust your knowledge for concepts; use tools for facts

IMPORTANT: After completing your tool calls, you MUST produce a structured
response matching the expected schema. Tool usage is for research only.
'''
```

---

## Agent Tool Configuration Reference

From ToolRegistry (Issue #231):

| Agent | Enabled | Max Calls | Timeout | Capabilities |
|-------|---------|-----------|---------|--------------|
| security_auditor | ✓ | 15 | 30s | github:search_code, github:get_security_advisories |
| dependency_mapper | ✓ | 20 | 25s | npm:get_package, pypi:get_package, github:get_repo |
| tech_comparator | ✓ | 10 | 20s | npm:get_package, github:get_repo |
| code_quality_critic | ✓ | 12 | 25s | github:list_commits, github:get_repo |
| implementation_planner | ✗ | 0 | 0s | — |
| performance_analyst | ✗ | 0 | 0s | — |
| trend_validator | ✗ | 0 | 0s | — |
| integration_feasibility | ✗ | 0 | 0s | — |

---

## Test Cases Specification

### test_tool_enabled_agent.py

```python
class TestToolCallConfig:
    def test_config_defaults(self):
        """Verify default values."""

    def test_config_custom_values(self):
        """Test custom configuration."""

class TestBuildToolEnhancedPrompt:
    def test_includes_tool_descriptions(self):
        """Verify tool descriptions are included."""

    def test_includes_max_calls_limit(self):
        """Verify max calls is mentioned."""

    def test_preserves_base_prompt(self):
        """Base prompt content is preserved."""

    def test_handles_empty_tools(self):
        """Empty tools list handled gracefully."""

class TestCreateToolEnabledAgent:
    @pytest.fixture
    def mock_tools(self):
        """Create mock BaseTool objects."""

    def test_returns_runnable(self, mock_tools):
        """Factory returns a Runnable."""

    def test_binds_tools_to_model(self, mock_tools):
        """Tools are bound to model."""

    def test_uses_parallel_tool_calls(self, mock_tools):
        """Parallel tool calls enabled by default."""

    def test_enhances_prompt(self, mock_tools):
        """Prompt is enhanced with tool info."""

    def test_uses_tool_strategy(self, mock_tools):
        """Uses ToolStrategy for structured output."""

    def test_with_custom_config(self, mock_tools):
        """Custom ToolCallConfig is respected."""

    def test_raises_on_empty_tools(self):
        """Empty tools list raises ValueError."""

class TestBackwardsCompatibility:
    def test_create_structured_agent_unchanged(self):
        """Existing function still works."""
```

---

## Acceptance Criteria Checklist

- [ ] `create_tool_enabled_agent()` function in `backend/app/workflows/agents/base.py`
- [ ] `ToolCallConfig` dataclass for configuration
- [ ] `_build_tool_enhanced_prompt()` helper function
- [ ] Parallel tool calls enabled by default
- [ ] Prompt enhancement with tool descriptions and guidelines
- [ ] Structured output via ToolStrategy preserved
- [ ] Unit tests covering all functionality (~15 tests)
- [ ] Backwards compatibility with existing agents
- [ ] CI checks pass (ruff format, ruff check, mypy)

---

## Dependencies

**Uses:**
- `langchain.agents.create_agent` - Base agent creation
- `langchain.agents.structured_output.ToolStrategy` - Structured output
- `langchain_core.tools.BaseTool` - Tool type hints
- `app.core.model_factory.get_chat_model` - Model provider

**Does NOT directly use:**
- `MCPClientPool` - Tools are pre-loaded and passed in
- `ToolRegistry` - Filtering happens in agent functions, not factory

---

## Future Integration (Issues #233, #234)

This factory will be used by:

```python
# Future: security_auditor.py (Issue #233)
async def run_security_auditor(...):
    registry = ToolRegistry()
    if registry.is_tool_enabled("security_auditor"):
        pool = MCPClientPool(get_mcp_settings().servers)
        tools = await pool.get_tools_for_capabilities(
            registry.get_capabilities("security_auditor")
        )
        config = ToolCallConfig(
            max_tool_calls=registry.get_agent_config("security_auditor").max_tool_calls
        )
        agent = create_tool_enabled_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
            tools=tools,
            tool_call_config=config,
        )
    else:
        agent = create_structured_agent(...)
```

---

## Definition of Done

1. All acceptance criteria checked
2. 98+ tests passing (existing + new)
3. CI checks pass (ruff format, ruff check, mypy)
4. Verified in dev environment
5. Documentation created
6. Commit with proper message

---

**Last Updated:** December 10, 2025

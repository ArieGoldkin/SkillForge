# Issue #232: Tool-Enabled Agent Factory

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 5 pts
**GitHub Issue:** [#232](https://github.com/ArieGoldkin/SkillForge/issues/232)
**Blocked By:** #230 (Complete), #231 (Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Tool-Enabled Agent Factory [5 pts]

**Description:**
Create `create_tool_enabled_agent()` factory function that produces LangChain agents capable of calling MCP tools during their reasoning process while still producing structured output.

**Labels:** `backend`, `feature`, `sprint-9`, `mcp`

---

## Implementation Summary

### Tasks Completed

- [x] Researched existing agent creation patterns in codebase
- [x] Created implementation plan (`PLAN.md`)
- [x] Added `ToolCallConfig` dataclass for configuration
- [x] Implemented `_build_tool_enhanced_prompt()` helper
- [x] Implemented `create_tool_enabled_agent()` factory
- [x] Comprehensive unit tests (23 tests, 100% pass rate)
- [x] CI checks pass (ruff format, ruff check, mypy)

### Files Created/Modified

**Modified Files:**
```
backend/app/workflows/agents/base.py  # Added factory + helpers
```

**New Files:**
```
backend/tests/unit/workflows/agents/test_tool_enabled_agent.py  # 23 tests
docs/issues/232-tool-enabled-agent-factory/PLAN.md              # Implementation plan
docs/issues/232-tool-enabled-agent-factory/README.md            # This file
```

---

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Function                                 │
│  (e.g., run_security_auditor - future #233)                     │
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
│ 1. Validate tools (must not be empty)                            │
│ 2. Apply ToolCallConfig (or defaults)                            │
│ 3. Enhance prompt with tool usage guidelines                     │
│ 4. Bind tools to model (parallel_tool_calls=True)               │
│ 5. Create agent with ToolStrategy for structured output          │
│ 6. Return Runnable                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. ToolCallConfig Dataclass
```python
@dataclass
class ToolCallConfig:
    """Configuration for tool-enabled agent behavior."""
    max_tool_calls: int = 10
    parallel_tool_calls: bool = True
```

#### 2. Prompt Enhancement
The `_build_tool_enhanced_prompt()` function automatically adds:
- Tool descriptions section
- Usage guidelines (5 best practices)
- Rate limit reminder
- Instruction to produce structured output

#### 3. Factory Function
```python
def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool],
    tool_call_config: ToolCallConfig | None = None,
) -> Runnable:
```

### Key Differences: Tool-Enabled vs Structured Agent

| Aspect | `create_structured_agent()` | `create_tool_enabled_agent()` |
|--------|----------------------------|------------------------------|
| **Tools** | Optional (usually None) | Required (non-empty) |
| **parallel_tool_calls** | `False` | `True` (configurable) |
| **Prompt Enhancement** | None | Automatic tool guidelines |
| **Use Case** | No external data needed | Real-time MCP data lookup |
| **Example Agents** | trend_validator, impl_planner | security_auditor, dependency_mapper |

---

## Testing

### Test Coverage

**23 tests total, 100% pass rate**

**Test Categories:**

1. **TestToolCallConfig (4 tests)**
   - Default values validation
   - Custom max_tool_calls
   - Parallel tool calls disable
   - All custom configuration

2. **TestBuildToolEnhancedPrompt (5 tests)**
   - Tool descriptions inclusion
   - Max calls limit in text
   - Base prompt preservation
   - Empty tools handling
   - Usage guidelines presence

3. **TestCreateToolEnabledAgent (11 tests)**
   - Returns Runnable instance
   - Raises on empty/None tools
   - Default and custom config
   - Prompt enhancement
   - Logging verification
   - Parallel tool calls True/False
   - Tool passing to create_agent
   - Custom max_tool_calls

4. **TestBackwardsCompatibility (3 tests)**
   - create_structured_agent still works
   - Works with tools=None
   - Differences from tool-enabled

### Test Results

```
============================= test session starts ==============================
collected 23 items

tests/unit/workflows/agents/test_tool_enabled_agent.py       23 passed

============================== 23 passed in 0.07s ==============================
```

---

## API Reference

### ToolCallConfig

```python
@dataclass
class ToolCallConfig:
    """Configuration for tool-enabled agent behavior.

    Attributes:
        max_tool_calls: Maximum number of tool calls allowed per agent run
        parallel_tool_calls: Whether to allow parallel tool execution
    """
    max_tool_calls: int = 10
    parallel_tool_calls: bool = True
```

### create_tool_enabled_agent

```python
def create_tool_enabled_agent(
    system_prompt: str,
    response_schema: type[BaseModel],
    tools: Sequence[BaseTool],
    tool_call_config: ToolCallConfig | None = None,
) -> Runnable:
    """Create an agent with MCP tool access and structured output.

    Args:
        system_prompt: Base system prompt for the agent
        response_schema: Pydantic model defining expected output structure
        tools: List of MCP tools (pre-filtered by ToolRegistry)
        tool_call_config: Optional configuration for tool behavior

    Returns:
        Configured agent with tool calling and structured output support

    Raises:
        ValueError: If tools sequence is empty
    """
```

### Usage Example

```python
from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings
from app.workflows.agents.base import create_tool_enabled_agent, ToolCallConfig

# Get tools for agent
registry = ToolRegistry()
if registry.is_tool_enabled("security_auditor"):
    pool = MCPClientPool(get_mcp_settings().servers)
    tools = await pool.get_tools_for_capabilities(
        registry.get_capabilities("security_auditor")
    )

    # Create tool-enabled agent
    agent = create_tool_enabled_agent(
        system_prompt="Analyze security vulnerabilities...",
        response_schema=SecurityAudit,
        tools=tools,
        tool_call_config=ToolCallConfig(max_tool_calls=15),
    )

    # Execute (same as structured agent)
    result = await agent.ainvoke({"messages": [...]})
```

---

## Prompt Enhancement Template

The factory automatically appends this to the system prompt:

```markdown
## Available Tools

You have access to the following tools for real-time data lookup:

- **github_search_code**: Search GitHub repositories for code
- **github_get_security_advisories**: Get CVE and security advisory data

## Tool Usage Guidelines

1. **Verify claims:** Use tools to check specific versions, CVEs, package metadata
2. **Be efficient:** Maximum 15 tool calls allowed - prioritize wisely
3. **Handle failures gracefully:** If a tool fails, note the gap in your findings
4. **Cite sources:** Reference tool results (e.g., "Per npm registry, v3.0.0...")
5. **Don't over-rely:** Trust your training for concepts; use tools for current facts

IMPORTANT: After your tool calls, you MUST produce a structured response matching
the expected schema. Tool usage is for research - your final output must be structured.
```

---

## Verification

### CI Checks

```bash
# All checks pass
poetry run ruff format --check app/   # ✅ 220 files formatted
poetry run ruff check app/            # ✅ All checks passed
poetry run mypy app/ --ignore-missing-imports  # ✅ No issues
```

### Code Quality

- ✅ **Linting:** All checks pass (ruff)
- ✅ **Formatting:** All files formatted
- ✅ **Type Hints:** Complete typing throughout
- ✅ **Docstrings:** All public functions documented
- ✅ **Logging:** Structured logging with tool details
- ✅ **Backwards Compatibility:** Existing agents unchanged

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#230:** MCP Client Pool & Connection Management (dependency - complete)
- **#231:** Tool Registry & Agent Capability Mapping (dependency - complete)
- **#233:** Security Auditor MCP Integration (uses this factory)
- **#234:** Dependency Mapper MCP Integration (uses this factory)

---

## Acceptance Criteria Checklist

- [x] `create_tool_enabled_agent()` function in `backend/app/workflows/agents/base.py`
- [x] `ToolCallConfig` dataclass for configuration
- [x] `_build_tool_enhanced_prompt()` helper function
- [x] Parallel tool calls enabled by default
- [x] Prompt enhancement with tool descriptions and guidelines
- [x] Structured output via ToolStrategy preserved
- [x] Unit tests covering all functionality (23 tests)
- [x] Backwards compatibility with existing agents
- [x] CI checks pass (ruff format, ruff check, mypy)

---

**Last Updated:** December 10, 2025

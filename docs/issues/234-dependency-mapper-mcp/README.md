# Issue #234: Dependency Mapper MCP Integration

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#234](https://github.com/ArieGoldkin/SkillForge/issues/234)
**Blocked By:** #230 (Complete), #231 (Complete), #232 (Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Dependency Mapper MCP Integration [3 pts]

**Description:**
Integrate MCP tools (npm registry, PyPI, GitHub) into the Dependency Mapper agent, enabling real-time package version lookups and dependency validation during analysis.

**Labels:** `backend`, `feature`, `sprint-9`, `mcp`

---

## Implementation Summary

### Tasks Completed

- [x] Researched existing Dependency Mapper implementation
- [x] Created implementation plan (`PLAN.md`)
- [x] Added `tools` parameter to `run_dependency_mapper()`
- [x] Implemented conditional agent factory selection
- [x] Added MCP tool loading in `run_dependency_mapper_with_session()`
- [x] Implemented graceful degradation on MCP failures
- [x] Comprehensive unit tests (15 tests, 100% pass rate)
- [x] CI checks pass (ruff format, ruff check, mypy)

### Files Modified

**Modified Files:**
```
backend/app/workflows/agents/dependency_mapper.py  # Added tools parameter
backend/app/workflows/tasks/runners.py             # Added MCP tool loading
```

**New Files:**
```
backend/tests/unit/workflows/agents/test_dependency_mapper_mcp.py  # 15 tests
docs/issues/234-dependency-mapper-mcp/PLAN.md                      # Implementation plan
docs/issues/234-dependency-mapper-mcp/README.md                    # This file
```

---

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              run_dependency_mapper_with_session()               │
│  (backend/app/workflows/tasks/runners.py)                       │
├─────────────────────────────────────────────────────────────────┤
│ 1. Initialize ToolRegistry                                       │
│ 2. Check is_tool_enabled("dependency_mapper")                   │
│ 3. If enabled:                                                   │
│    ├─ Initialize MCPClientPool                                   │
│    ├─ Get capabilities from registry                             │
│    └─ Load tools via pool.get_tools_for_capabilities()          │
│ 4. Pass tools to run_dependency_mapper()                         │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   run_dependency_mapper()                        │
│  (backend/app/workflows/agents/dependency_mapper.py)            │
├─────────────────────────────────────────────────────────────────┤
│ 1. Build full_prompt (base + skill level)                        │
│ 2. If tools provided:                                            │
│    └─ create_tool_enabled_agent(tools=tools)                    │
│ 3. Else:                                                         │
│    └─ create_structured_agent() (fallback)                      │
│ 4. run_agent_with_tracking()                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes

#### 1. run_dependency_mapper() (dependency_mapper.py)

Added optional `tools` parameter and conditional factory selection:

```python
async def run_dependency_mapper(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,  # NEW
) -> dict[str, object]:
    # ... existing prompt building ...

    # Create agent - use tool-enabled factory if tools provided
    if tools:
        agent = create_tool_enabled_agent(
            system_prompt=full_prompt,
            response_schema=DependencyMapping,
            tools=tools,
            tool_call_config=ToolCallConfig(max_tool_calls=20),
        )
        logger.info("dependency_mapper_using_mcp_tools", ...)
    else:
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=DependencyMapping,
        )
```

#### 2. run_dependency_mapper_with_session() (runners.py)

Added MCP tool loading with graceful degradation:

```python
async def run_dependency_mapper_with_session(...):
    # Load MCP tools for dependency mapper if enabled
    tools: list[BaseTool] = []
    try:
        from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

        registry = ToolRegistry()
        if registry.is_tool_enabled("dependency_mapper"):
            settings = get_mcp_settings()
            if settings.enabled:
                pool = MCPClientPool(settings.get_enabled_servers())
                capabilities = registry.get_capabilities("dependency_mapper")
                tools = await pool.get_tools_for_capabilities(capabilities)
                logger.info("loaded_mcp_tools_for_dependency_mapper", ...)
    except Exception as e:
        logger.warning("mcp_tool_loading_failed", ...)
        tools = []  # Graceful degradation

    async with AsyncSessionLocal() as session:
        return await run_dependency_mapper(..., tools=tools)
```

---

## Graceful Degradation

The implementation supports graceful degradation at multiple levels:

| Scenario | Behavior |
|----------|----------|
| **MCP disabled globally** | Uses `create_structured_agent()` |
| **Agent not enabled in registry** | Uses `create_structured_agent()` |
| **MCP server unavailable** | Catches exception, uses `create_structured_agent()` |
| **Tool loading fails** | Logs warning, uses `create_structured_agent()` |
| **Empty tools list** | Uses `create_structured_agent()` |

---

## Testing

### Test Coverage

**15 tests total, 100% pass rate**

**Test Categories:**

1. **TestRunDependencyMapperWithTools (7 tests)**
   - Uses tool-enabled agent when tools provided
   - Passes DependencyMapping schema to tool agent
   - Enhances prompt with skill level and tools
   - Uses structured agent when no tools
   - Uses structured agent when empty tools
   - Tool call config max_calls is 20
   - Runs agent with tracking

2. **TestDependencyMapperWithSessionMCP (5 tests)**
   - Runner function has proper parameters
   - Runner imports MCP modules correctly
   - Runner has graceful degradation
   - Runner checks registry enabled
   - Runner passes tools to agent

3. **TestSkillLevelIntegration (3 tests)**
   - Beginner skill level with tools
   - Expert skill level with tools
   - Skill level without tools

### Test Results

```
============================= test session starts ==============================
collected 15 items

tests/unit/workflows/agents/test_dependency_mapper_mcp.py       15 passed

============================== 15 passed in 0.06s ==============================
```

---

## MCP Tools Available to Dependency Mapper

From ToolRegistry configuration:

```python
"dependency_mapper": AgentToolConfig(
    agent_type="dependency_mapper",
    enabled=True,
    capabilities=[
        ToolCapability("npm", "get_package"),
        ToolCapability("pypi", "get_package"),
        ToolCapability("github", "get_repo"),
    ],
    max_tool_calls=20,
    tool_timeout=25.0,
)
```

**Tools:**

| Tool | Server | Purpose |
|------|--------|---------|
| `npm_get_package` | npm | Get npm package metadata, versions, dependencies |
| `pypi_get_package` | pypi | Get PyPI package info and dependencies |
| `github_get_repo` | github | Get repository details for dependency context |

**Use Cases:**
- Verify exact package versions exist
- Check dependency compatibility
- Get latest stable versions
- Identify deprecated packages
- Validate peer dependency requirements

---

## Comparison with Security Auditor (#233)

| Aspect | Security Auditor (#233) | Dependency Mapper (#234) |
|--------|------------------------|--------------------------|
| **max_tool_calls** | 15 | 20 (more package lookups) |
| **MCP Servers** | 1 (github) | 3 (npm, pypi, github) |
| **MCP Tools** | search_code, get_security_advisories | get_package (×2), get_repo |
| **Response Schema** | SecurityAudit | DependencyMapping |
| **Primary Use** | CVE lookups, vulnerability patterns | Package version validation |

---

## API Reference

### run_dependency_mapper

```python
async def run_dependency_mapper(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run dependency mapper agent.

    Args:
        content: Analyzed content
        content_type: Type of content
        analysis_id: Analysis ID
        session: Database session
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced dependency analysis

    Returns:
        Agent findings dict
    """
```

---

## Verification

### CI Checks

```bash
# All checks pass
poetry run ruff format --check app/   # ✅ 220 files formatted
poetry run ruff check app/            # ✅ All checks passed
poetry run mypy app/ --ignore-missing-imports  # ✅ No issues found
```

### MCP Test Suite

```bash
poetry run pytest tests/unit/services/mcp/ \
    tests/unit/workflows/agents/test_tool_enabled_agent.py \
    tests/unit/workflows/agents/test_security_auditor_mcp.py \
    tests/unit/workflows/agents/test_dependency_mapper_mcp.py -v

# Result: 151 passed in 0.40s
```

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#230:** MCP Client Pool & Connection Management (dependency - complete)
- **#231:** Tool Registry & Agent Capability Mapping (dependency - complete)
- **#232:** Tool-Enabled Agent Factory (dependency - complete)
- **#233:** Security Auditor MCP Integration (same pattern - complete)
- **#236:** MCP Integration Tests (will test full flow)

---

## Acceptance Criteria Checklist

- [x] `run_dependency_mapper()` accepts optional `tools` parameter
- [x] Uses `create_tool_enabled_agent()` when tools provided
- [x] Falls back to `create_structured_agent()` when no tools
- [x] `run_dependency_mapper_with_session()` loads MCP tools
- [x] Graceful degradation on MCP failures
- [x] Unit tests for both paths (15 tests)
- [x] CI checks pass (ruff format, ruff check, mypy)

---

**Last Updated:** December 10, 2025

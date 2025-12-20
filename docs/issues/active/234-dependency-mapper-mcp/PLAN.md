# Issue #234: Dependency Mapper MCP Integration - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#234](https://github.com/ArieGoldkin/SkillForge/issues/234)
**Blocked By:** #230 (Complete), #231 (Complete), #232 (Complete)

---

## Objective

Integrate MCP tools (npm registry, PyPI, GitHub) into the Dependency Mapper agent, enabling real-time package version lookups and dependency validation during analysis.

---

## Architecture Overview

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

---

## Current State

### Dependency Mapper Configuration (from ToolRegistry)

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

### Current Flow (No Tools)

```python
# dependency_mapper.py (current)
agent = create_structured_agent(
    system_prompt=full_prompt,
    response_schema=DependencyMapping,
)
```

---

## Implementation Changes

### 1. Modify `run_dependency_mapper()` (dependency_mapper.py)

**Add tools parameter and conditional factory:**

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

    # NEW: Choose factory based on tools availability
    if tools:
        from app.workflows.agents.base import create_tool_enabled_agent, ToolCallConfig
        agent = create_tool_enabled_agent(
            system_prompt=full_prompt,
            response_schema=DependencyMapping,
            tools=tools,
            tool_call_config=ToolCallConfig(max_tool_calls=20),
        )
        logger.info("dependency_mapper_using_mcp_tools", tool_count=len(tools))
    else:
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=DependencyMapping,
        )

    # ... existing execution ...
```

### 2. Modify `run_dependency_mapper_with_session()` (runners.py)

**Add MCP tool loading:**

```python
async def run_dependency_mapper_with_session(...) -> dict[str, object]:
    # NEW: Load MCP tools if enabled
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
                logger.info("loaded_mcp_tools_for_dependency_mapper", count=len(tools))
    except Exception as e:
        logger.warning("mcp_tool_loading_failed", error=str(e))
        tools = []  # Graceful degradation

    async with AsyncSessionLocal() as session:
        return await run_dependency_mapper(
            content, content_type, analysis_id, session, state,
            tools=tools,  # NEW
        )
```

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/workflows/agents/dependency_mapper.py` | **MODIFY** | Add `tools` param, conditional factory |
| `backend/app/workflows/tasks/runners.py` | **MODIFY** | Add MCP tool loading |

## Files to Create

| File | Description |
|------|-------------|
| `backend/tests/unit/workflows/agents/test_dependency_mapper_mcp.py` | Unit tests for MCP integration |
| `docs/issues/234-dependency-mapper-mcp/README.md` | Documentation |

---

## Test Cases

### test_dependency_mapper_mcp.py

```python
class TestRunDependencyMapperWithTools:
    def test_run_dependency_mapper_with_tools(self):
        """Agent uses create_tool_enabled_agent when tools provided."""

    def test_run_dependency_mapper_without_tools(self):
        """Agent falls back to create_structured_agent when no tools."""

    def test_run_dependency_mapper_empty_tools_fallback(self):
        """Empty tools list uses structured agent (not tool-enabled)."""

    def test_tool_call_config_max_calls_is_20(self):
        """Dependency mapper uses max_tool_calls=20 for package lookups."""

    def test_passes_dependency_mapping_schema(self):
        """Tool-enabled agent receives DependencyMapping schema."""

class TestDependencyMapperWithSessionMCP:
    def test_runner_has_tools_parameter(self):
        """Verify runner function signature."""

    def test_runner_imports_mcp_modules(self):
        """Verify runner has proper MCP imports."""

    def test_runner_has_graceful_degradation(self):
        """Verify runner has exception handling for MCP failures."""

    def test_runner_checks_registry_enabled(self):
        """Verify runner checks if agent is enabled in registry."""

    def test_runner_passes_tools_to_agent(self):
        """Verify runner passes tools parameter to run_dependency_mapper."""
```

---

## MCP Tools Available

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

---

## Graceful Degradation

The implementation supports graceful degradation:

1. **MCP disabled globally** → Uses `create_structured_agent()`
2. **Agent not enabled in registry** → Uses `create_structured_agent()`
3. **MCP server unavailable** → Catches exception, uses `create_structured_agent()`
4. **Tool loading fails** → Logs warning, uses `create_structured_agent()`

---

## Acceptance Criteria

- [ ] `run_dependency_mapper()` accepts optional `tools` parameter
- [ ] Uses `create_tool_enabled_agent()` when tools provided
- [ ] Falls back to `create_structured_agent()` when no tools
- [ ] `run_dependency_mapper_with_session()` loads MCP tools
- [ ] Graceful degradation on MCP failures
- [ ] Unit tests for both paths
- [ ] CI checks pass

---

## Comparison with Issue #233 (Security Auditor)

| Aspect | Security Auditor (#233) | Dependency Mapper (#234) |
|--------|------------------------|--------------------------|
| **max_tool_calls** | 15 | 20 (more package lookups) |
| **MCP Tools** | github:search_code, github:get_security_advisories | npm:get_package, pypi:get_package, github:get_repo |
| **Response Schema** | SecurityAudit | DependencyMapping |
| **Primary Use** | CVE lookups, vulnerability patterns | Package version validation |

---

**Last Updated:** December 10, 2025

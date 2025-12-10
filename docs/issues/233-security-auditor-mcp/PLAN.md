# Issue #233: Security Auditor MCP Integration - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#233](https://github.com/ArieGoldkin/SkillForge/issues/233)
**Blocked By:** #230 (Complete), #231 (Complete), #232 (Complete)

---

## Objective

Integrate MCP tools (GitHub security advisories, code search) into the Security Auditor agent, enabling real-time CVE lookups and vulnerability pattern detection during analysis.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               run_security_auditor_with_session()               │
│  (backend/app/workflows/tasks/runners.py)                       │
├─────────────────────────────────────────────────────────────────┤
│ 1. Initialize ToolRegistry                                       │
│ 2. Check is_tool_enabled("security_auditor")                    │
│ 3. If enabled:                                                   │
│    ├─ Initialize MCPClientPool                                   │
│    ├─ Get capabilities from registry                             │
│    └─ Load tools via pool.get_tools_for_capabilities()          │
│ 4. Pass tools to run_security_auditor()                          │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   run_security_auditor()                         │
│  (backend/app/workflows/agents/security_auditor.py)             │
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

### Security Auditor Configuration (from ToolRegistry)

```python
"security_auditor": AgentToolConfig(
    agent_type="security_auditor",
    enabled=True,
    capabilities=[
        ToolCapability("github", "search_code"),
        ToolCapability("github", "get_security_advisories"),
    ],
    max_tool_calls=15,
    tool_timeout=30.0,
)
```

### Current Flow (No Tools)

```python
# security_auditor.py (current)
agent = create_structured_agent(
    system_prompt=full_prompt,
    response_schema=SecurityAudit,
)
```

---

## Implementation Changes

### 1. Modify `run_security_auditor()` (security_auditor.py)

**Add tools parameter and conditional factory:**

```python
async def run_security_auditor(
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
            response_schema=SecurityAudit,
            tools=tools,
            tool_call_config=ToolCallConfig(max_tool_calls=15),
        )
        logger.info("security_auditor_using_mcp_tools", tool_count=len(tools))
    else:
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
        )

    # ... existing execution ...
```

### 2. Modify `run_security_auditor_with_session()` (runners.py)

**Add MCP tool loading:**

```python
async def run_security_auditor_with_session(...) -> dict[str, object]:
    # NEW: Load MCP tools if enabled
    tools: list[BaseTool] = []
    try:
        from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

        registry = ToolRegistry()
        if registry.is_tool_enabled("security_auditor"):
            settings = get_mcp_settings()
            if settings.enabled:
                pool = MCPClientPool(settings.get_enabled_servers())
                capabilities = registry.get_capabilities("security_auditor")
                tools = await pool.get_tools_for_capabilities(capabilities)
                logger.info("loaded_mcp_tools_for_security_auditor", count=len(tools))
    except Exception as e:
        logger.warning("mcp_tool_loading_failed", error=str(e))
        tools = []  # Graceful degradation

    async with AsyncSessionLocal() as session:
        return await run_security_auditor(
            content, content_type, analysis_id, session, state,
            tools=tools,  # NEW
        )
```

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/workflows/agents/security_auditor.py` | **MODIFY** | Add `tools` param, conditional factory |
| `backend/app/workflows/tasks/runners.py` | **MODIFY** | Add MCP tool loading |

## Files to Create

| File | Description |
|------|-------------|
| `backend/tests/unit/workflows/agents/test_security_auditor_mcp.py` | Unit tests for MCP integration |
| `docs/issues/233-security-auditor-mcp/README.md` | Documentation |

---

## Test Cases

### test_security_auditor_mcp.py

```python
class TestSecurityAuditorMCPIntegration:
    def test_run_security_auditor_with_tools(self):
        """Agent uses create_tool_enabled_agent when tools provided."""

    def test_run_security_auditor_without_tools(self):
        """Agent falls back to create_structured_agent when no tools."""

    def test_run_security_auditor_empty_tools_fallback(self):
        """Empty tools list uses structured agent (not tool-enabled)."""

class TestSecurityAuditorWithSessionMCP:
    def test_loads_tools_when_enabled(self):
        """Loads MCP tools when registry has security_auditor enabled."""

    def test_graceful_degradation_on_mcp_failure(self):
        """Continues without tools if MCP loading fails."""

    def test_passes_tools_to_agent(self):
        """Passes loaded tools to run_security_auditor."""
```

---

## Graceful Degradation

The implementation supports graceful degradation:

1. **MCP disabled globally** → Uses `create_structured_agent()`
2. **Agent not enabled in registry** → Uses `create_structured_agent()`
3. **MCP server unavailable** → Catches exception, uses `create_structured_agent()`
4. **Tool loading fails** → Logs warning, uses `create_structured_agent()`

---

## Acceptance Criteria

- [ ] `run_security_auditor()` accepts optional `tools` parameter
- [ ] Uses `create_tool_enabled_agent()` when tools provided
- [ ] Falls back to `create_structured_agent()` when no tools
- [ ] `run_security_auditor_with_session()` loads MCP tools
- [ ] Graceful degradation on MCP failures
- [ ] Unit tests for both paths
- [ ] CI checks pass

---

**Last Updated:** December 10, 2025

# Issue #233: Security Auditor MCP Integration

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#233](https://github.com/ArieGoldkin/SkillForge/issues/233)
**Blocked By:** #230 (Complete), #231 (Complete), #232 (Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Security Auditor MCP Integration [3 pts]

**Description:**
Integrate MCP tools (GitHub security advisories, code search) into the Security Auditor agent, enabling real-time CVE lookups and vulnerability pattern detection during analysis.

**Labels:** `backend`, `feature`, `sprint-9`, `mcp`

---

## Implementation Summary

### Tasks Completed

- [x] Researched existing Security Auditor implementation
- [x] Created implementation plan (`PLAN.md`)
- [x] Added `tools` parameter to `run_security_auditor()`
- [x] Implemented conditional agent factory selection
- [x] Added MCP tool loading in `run_security_auditor_with_session()`
- [x] Implemented graceful degradation on MCP failures
- [x] Comprehensive unit tests (15 tests, 100% pass rate)
- [x] CI checks pass (ruff format, ruff check, mypy)

### Files Modified

**Modified Files:**
```
backend/app/workflows/agents/security_auditor.py  # Added tools parameter
backend/app/workflows/tasks/runners.py            # Added MCP tool loading
```

**New Files:**
```
backend/tests/unit/workflows/agents/test_security_auditor_mcp.py  # 15 tests
docs/issues/233-security-auditor-mcp/PLAN.md                      # Implementation plan
docs/issues/233-security-auditor-mcp/README.md                    # This file
```

---

## Technical Details

### Architecture

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

### Key Changes

#### 1. run_security_auditor() (security_auditor.py)

Added optional `tools` parameter and conditional factory selection:

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

    # Create agent - use tool-enabled factory if tools provided
    if tools:
        agent = create_tool_enabled_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
            tools=tools,
            tool_call_config=ToolCallConfig(max_tool_calls=15),
        )
        logger.info("security_auditor_using_mcp_tools", ...)
    else:
        agent = create_structured_agent(
            system_prompt=full_prompt,
            response_schema=SecurityAudit,
        )
```

#### 2. run_security_auditor_with_session() (runners.py)

Added MCP tool loading with graceful degradation:

```python
async def run_security_auditor_with_session(...):
    # Load MCP tools for security auditor if enabled
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
                logger.info("loaded_mcp_tools_for_security_auditor", ...)
    except Exception as e:
        logger.warning("mcp_tool_loading_failed", ...)
        tools = []  # Graceful degradation

    async with AsyncSessionLocal() as session:
        return await run_security_auditor(..., tools=tools)
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

1. **TestRunSecurityAuditorWithTools (7 tests)**
   - Uses tool-enabled agent when tools provided
   - Passes SecurityAudit schema to tool agent
   - Enhances prompt with skill level and tools
   - Uses structured agent when no tools
   - Uses structured agent when empty tools
   - Tool call config max_calls is 15
   - Runs agent with tracking

2. **TestSecurityAuditorWithSessionMCP (5 tests)**
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

tests/unit/workflows/agents/test_security_auditor_mcp.py       15 passed

============================== 15 passed in 0.05s ==============================
```

---

## MCP Tools Available to Security Auditor

From ToolRegistry configuration:

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

**Tools:**
- `github_search_code`: Search GitHub repositories for vulnerable code patterns
- `github_get_security_advisories`: Lookup CVE/security advisory information

---

## API Reference

### run_security_auditor

```python
async def run_security_auditor(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run security auditor agent to identify security risks and vulnerabilities.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced security analysis

    Returns:
        Dictionary with agent_type, findings, processing_time_ms
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
    tests/unit/workflows/agents/test_security_auditor_mcp.py -v

# Result: 136 passed in 0.37s
```

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#230:** MCP Client Pool & Connection Management (dependency - complete)
- **#231:** Tool Registry & Agent Capability Mapping (dependency - complete)
- **#232:** Tool-Enabled Agent Factory (dependency - complete)
- **#234:** Dependency Mapper MCP Integration (next - uses same pattern)
- **#236:** MCP Integration Tests (will test full flow)

---

## Acceptance Criteria Checklist

- [x] `run_security_auditor()` accepts optional `tools` parameter
- [x] Uses `create_tool_enabled_agent()` when tools provided
- [x] Falls back to `create_structured_agent()` when no tools
- [x] `run_security_auditor_with_session()` loads MCP tools
- [x] Graceful degradation on MCP failures
- [x] Unit tests for both paths (15 tests)
- [x] CI checks pass (ruff format, ruff check, mypy)

---

**Last Updated:** December 10, 2025

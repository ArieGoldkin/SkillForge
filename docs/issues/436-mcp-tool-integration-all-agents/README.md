# Issue #436: Complete MCP Tool Integration for All Agents

## Summary

Complete MCP tool integration for all 12 analysis agents. Currently 6 agents have full integration, while 6 agents are missing tool loading in their runners or lack registry configuration entirely.

## Current State

```
                    MCP TOOL INTEGRATION STATUS
    ╔═══════════════════════════════════════════════════════╗
    ║  FULLY INTEGRATED (6)    │  NEEDS INTEGRATION (6)    ║
    ╠═══════════════════════════════════════════════════════╣
    ║  ✓ security_auditor      │  Phase 1:                 ║
    ║  ✓ dependency_mapper     │    ○ trend_validator      ║
    ║  ✓ tech_comparator       │    ○ integration_feasibility ║
    ║  ✓ code_quality_critic   │  Phase 2 (Tier 1):        ║
    ║  ✓ implementation_planner│    ○ key_insights         ║
    ║  ✓ performance_analyst   │    ○ pros_cons            ║
    ║                          │    ○ actionable           ║
    ║                          │    ○ audience_fit         ║
    ╚═══════════════════════════════════════════════════════╝
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      MCP TOOL INTEGRATION FLOW                       │
└──────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │  runners.py     │
                         │  (Session Mgmt) │
                         └────────┬────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Tool Loading  │       │ Agent Function│       │ MCP Registry  │
│    Block      │       │    (*.py)     │       │ (registry.py) │
│               │       │               │       │               │
│ registry.is_  │       │ tools param   │       │ AGENT_TOOL_   │
│ tool_enabled()│◄─────►│ in signature  │◄─────►│ CONFIGS       │
│               │       │               │       │               │
│ pool.get_     │       │ create_agent_ │       │ capabilities  │
│ tools_for_    │       │ with_few_shot │       │               │
│ capabilities()│       │ (tools=tools) │       │               │
└───────────────┘       └───────────────┘       └───────────────┘

                    3 COMPONENTS MUST BE IN SYNC:
        1. Registry entry in registry.py
        2. Tool loading block in runners.py
        3. Agent function accepting tools parameter
```

## Root Cause Analysis

**Why some agents lack MCP tools:**
1. **Phase 1 agents** (`trend_validator`, `integration_feasibility`): Have registry configs but runners were never updated to load tools
2. **Phase 2 agents** (Tier 1 Universal): Added in #499 after MCP infrastructure was built - designed as "content-only" but decision made to add tool support for consistency

## Solution Approach

### Approach Options Considered

| Approach | Pros | Cons | Score |
|----------|------|------|-------|
| Option A: Keep Tier 1 Content-Only | Faster, simpler | Inconsistent patterns | 5/10 |
| **Option B: Full Integration** | Consistent, future-ready | More work upfront | 9/10 |

### Chosen Approach: Option B - Full MCP Integration for All Agents

**Rationale:**
- Consistency across all 12 agents = easier maintenance
- Prepared for ReAct pattern upgrade (#506)
- Tier 1 agents can verify claims against real docs
- Graceful degradation ensures agents work without MCP

---

## Implementation Phases

| Phase | Description | Files Changed | Estimated Time |
|-------|-------------|---------------|----------------|
| 1 | Complete partial integration | 3 files | ~1.5 hours |
| 2 | Tier 1 Universal agents | 6 files | ~3 hours |
| 3 | Testing & verification | 2 files | ~1.5 hours |

---

## Phase 1: Complete Partial Integration (2 agents)

### 1.1 trend_validator

**File:** `backend/app/domains/analysis/workflows/agents/trend_validator.py`

| Change | Location | Description |
|--------|----------|-------------|
| Add imports | Top of file | `from collections.abc import Sequence`, `from langchain_core.tools import BaseTool` |
| Update signature | Line 30-36 | Add `tools: Sequence[BaseTool] \| None = None` |
| Update factory call | Line 100-106 | Pass `tools=tools` |
| Add logging | After factory | Log tool usage if tools provided |

**File:** `backend/app/domains/analysis/workflows/tasks/runners.py`

| Change | Location | Description |
|--------|----------|-------------|
| Add tool loading block | After line 719 | MCP tool loading pattern (see below) |
| Update agent call | Line 730 | Pass `tools=tools` |

**File:** `backend/app/domains/analysis/workflows/agents/factories.py`

| Change | Location | Description |
|--------|----------|-------------|
| Update signature | Line 366-372 | Add `tools` parameter to `create_trend_validator_agent_with_few_shot` |
| Update return | Line 386-393 | Pass `tools=tools` to factory |

### 1.2 integration_feasibility

**File:** `backend/app/domains/analysis/workflows/agents/integration_feasibility.py`

| Change | Location | Description |
|--------|----------|-------------|
| Add imports | Top of file | `Sequence`, `BaseTool`, `get_logger` |
| Update signature | Line 25-31 | Add `tools: Sequence[BaseTool] \| None = None` |
| Refactor to factory | Line 71-74 | Replace `create_structured_agent` with `create_agent_with_optional_few_shot` |
| Add logging | After factory | Log tool usage |

**File:** `backend/app/domains/analysis/workflows/tasks/runners.py`

| Change | Location | Description |
|--------|----------|-------------|
| Add tool loading block | After line 305 | MCP tool loading pattern |
| Update agent call | Line 317 | Pass `tools=tools` |

---

## Phase 2: Tier 1 Universal Agents (4 agents)

### 2.1 MCP Registry Updates

**File:** `backend/app/shared/services/mcp/registry.py`

Add after line 247:

```python
# Tier 1 Universal Agents (Issue #436, #499)
"key_insights": AgentToolConfig(
    agent_type="key_insights",
    enabled=True,
    capabilities=[ARTIFACT_LOAD_CAPABILITY, MEMORY_SEARCH_CAPABILITY],
    max_tool_calls=5,
    tool_timeout=20.0,
),
"pros_cons": AgentToolConfig(
    agent_type="pros_cons",
    enabled=True,
    capabilities=[ARTIFACT_LOAD_CAPABILITY, MEMORY_SEARCH_CAPABILITY],
    max_tool_calls=5,
    tool_timeout=20.0,
),
"actionable": AgentToolConfig(
    agent_type="actionable",
    enabled=True,
    capabilities=[ARTIFACT_LOAD_CAPABILITY, MEMORY_SEARCH_CAPABILITY],
    max_tool_calls=5,
    tool_timeout=20.0,
),
"audience_fit": AgentToolConfig(
    agent_type="audience_fit",
    enabled=True,
    capabilities=[ARTIFACT_LOAD_CAPABILITY, MEMORY_SEARCH_CAPABILITY],
    max_tool_calls=5,
    tool_timeout=20.0,
),
```

### 2.2 Agent Function Updates

| Agent | File | Changes Needed |
|-------|------|----------------|
| `key_insights` | `key_insights.py` | Already has `tools` param - just update runner |
| `pros_cons` | `pros_cons.py` | Add imports, `tools` param, update factory call |
| `actionable` | `actionable.py` | Add imports, `tools` param, update factory call |
| `audience_fit` | `audience_fit.py` | Add imports, `tools` param, update factory call |

### 2.3 Runner Updates

**File:** `backend/app/domains/analysis/workflows/tasks/runners.py`

Add MCP tool loading blocks to:
- `run_key_insights_with_session` (after line 1041)
- `run_pros_cons_with_session` (after line 931)
- `run_actionable_with_session` (after line 873)
- `run_audience_fit_with_session` (after line 986)

---

## Standard MCP Tool Loading Pattern

```python
# Load MCP tools for {agent_name} if enabled
tools: list[BaseTool] = []
try:
    from app.shared.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

    registry = ToolRegistry()
    if registry.is_tool_enabled("{agent_name}"):
        settings = get_mcp_settings()
        if settings.enabled:
            pool = MCPClientPool(
                settings.get_enabled_servers(),
                settings=settings,
                analysis_id=str(analysis_id),
            )
            capabilities = registry.get_capabilities("{agent_name}")
            tools = await pool.get_tools_for_capabilities(capabilities)
            logger.info(
                "loaded_mcp_tools_for_{agent_name}",
                analysis_id=str(analysis_id),
                tool_count=len(tools),
                capabilities=capabilities,
            )
except Exception as e:  # noqa: BLE001 - Graceful degradation
    logger.warning(
        "mcp_tool_loading_failed",
        agent_type="{agent_name}",
        analysis_id=str(analysis_id),
        error=str(e),
    )
    tools = []
```

---

## File-by-File Implementation

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/shared/services/mcp/registry.py` | Modify | Add 4 Tier 1 agent configs |
| `backend/app/domains/analysis/workflows/agents/factories.py` | Modify | Update `create_trend_validator_agent_with_few_shot` |
| `backend/app/domains/analysis/workflows/agents/trend_validator.py` | Modify | Add `tools` param + logging |
| `backend/app/domains/analysis/workflows/agents/integration_feasibility.py` | Modify | Add `tools` param + refactor to factory |
| `backend/app/domains/analysis/workflows/agents/pros_cons.py` | Modify | Add `tools` param + update factory call |
| `backend/app/domains/analysis/workflows/agents/actionable.py` | Modify | Add `tools` param + update factory call |
| `backend/app/domains/analysis/workflows/agents/audience_fit.py` | Modify | Add `tools` param + update factory call |
| `backend/app/domains/analysis/workflows/tasks/runners.py` | Modify | Add 6 MCP tool loading blocks |
| `backend/tests/unit/services/mcp/test_registry.py` | Modify | Add Tier 1 agent config tests |
| `backend/tests/unit/services/mcp/test_registry_tier1_agents.py` | **New** | Comprehensive Tier 1 tests |

---

## Implementation Order

```
╔═══════════════════════════════════════════════════════════════════════╗
║                     IMPLEMENTATION SEQUENCE                           ║
╠═══════════════════════════════════════════════════════════════════════╣
║ Step 1: registry.py                                                   ║
║   └── Add Tier 1 agent configs                                        ║
║                                                                        ║
║ Step 2: factories.py                                                  ║
║   └── Update create_trend_validator_agent_with_few_shot               ║
║                                                                        ║
║ Step 3: Agent functions (5 files)                                     ║
║   ├── trend_validator.py                                              ║
║   ├── integration_feasibility.py                                      ║
║   ├── pros_cons.py                                                    ║
║   ├── actionable.py                                                   ║
║   └── audience_fit.py                                                 ║
║                                                                        ║
║ Step 4: runners.py                                                    ║
║   └── Add 6 MCP tool loading blocks                                   ║
║                                                                        ║
║ Step 5: Tests                                                         ║
║   ├── Update test_runners.py                                          ║
║   └── Create test_registry_tier1_agents.py                            ║
║                                                                        ║
║ Step 6: Validation                                                    ║
║   ├── ruff format --check app/                                        ║
║   ├── ruff check app/                                                 ║
║   ├── ty check app/ --exclude "app/evaluation/*"                      ║
║   └── pytest tests/unit/ --tb=short -v                                ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] All 12 agents have MCP tool integration
- [ ] All agents gracefully degrade when MCP servers unavailable
- [ ] Tool usage logged in Langfuse traces
- [ ] Tool results enhance agent analysis quality

### Technical Requirements
- [ ] MCP Tool Registry updated with 4 new Tier 1 agent configs
- [ ] All agent functions accept `tools: Sequence[BaseTool] | None` parameter
- [ ] All runners load MCP tools using established pattern
- [ ] No breaking changes to existing functionality

### Quality Requirements
- [ ] Unit tests for tool parameter handling
- [ ] All linting and type checks pass
- [ ] 100% backward compatibility

---

## Testing Plan

### Unit Tests

**Existing tests to update:**
- [ ] `test_runners.py` - Verify `tools=[]` passed to all 6 new agents

**New tests to create:**
- [ ] `test_registry_tier1_agents.py`:
  - [ ] Test each Tier 1 agent has config entry
  - [ ] Test each is enabled
  - [ ] Test each has ARTIFACT_LOAD_CAPABILITY
  - [ ] Test each has MEMORY_SEARCH_CAPABILITY
  - [ ] Test `is_tool_enabled()` returns True
  - [ ] Test `get_capabilities()` returns expected

### Manual Testing
- [ ] Run analysis with MCP enabled - verify tools loaded
- [ ] Run analysis with MCP disabled - verify graceful degradation
- [ ] Check Langfuse traces for tool loading logs

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Agents with MCP Tools | 6/12 (50%) | 12/12 (100%) |
| Tool Loading Pattern Consistency | Partial | Complete |
| Test Coverage for Tool Integration | Partial | Complete |

---

## References

- [GitHub Issue #436](https://github.com/ArieGoldkin/SkillForge/issues/436)
- [Tier 1 Agents PR #508](https://github.com/ArieGoldkin/SkillForge/pull/508)
- [MCP Tool Registry](backend/app/shared/services/mcp/registry.py)
- [Working Runner Pattern](backend/app/domains/analysis/workflows/tasks/runners.py#L203-L291)

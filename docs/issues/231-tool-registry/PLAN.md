# Issue #231: Tool Registry & Agent Capability Mapping - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#231](https://github.com/ArieGoldkin/SkillForge/issues/231)
**Blocked By:** #230 (Complete)

---

## Objective

Implement `ToolRegistry` for managing which MCP tools each agent can access, preventing tool overload and ensuring agents only see relevant capabilities.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         ToolRegistry                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   AGENT_TOOL_CONFIGS                        ││
│  │  ┌──────────────────┐  ┌──────────────────┐                 ││
│  │  │ security_auditor │  │ dependency_mapper│                 ││
│  │  │ enabled: True    │  │ enabled: True    │                 ││
│  │  │ capabilities:    │  │ capabilities:    │                 ││
│  │  │ - cve:search     │  │ - npm:get_package│                 ││
│  │  │ - github:alerts  │  │ - pypi:get_pkg   │                 ││
│  │  │ max_calls: 10    │  │ max_calls: 15    │                 ││
│  │  └──────────────────┘  └──────────────────┘                 ││
│  │                                                              ││
│  │  ┌──────────────────┐  ┌──────────────────┐                 ││
│  │  │ trend_validator  │  │ impl_planner     │                 ││
│  │  │ enabled: False   │  │ enabled: False   │ (no tools)     ││
│  │  │ capabilities: [] │  │ capabilities: [] │                 ││
│  │  └──────────────────┘  └──────────────────┘                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Methods:                                                        │
│  • is_tool_enabled(agent_type) -> bool                          │
│  • get_capabilities(agent_type) -> list[str]                    │
│  • get_agent_config(agent_type) -> AgentToolConfig              │
│  • filter_tools(tools, agent_type) -> list[BaseTool]            │
│  • register_agent(config) -> None                               │
│  • list_enabled_agents() -> list[str]                           │
│  • get_all_required_servers() -> set[str]                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Inventory (from codebase)

| Agent File | Agent Type | Tools Needed | MCP Servers |
|------------|------------|--------------|-------------|
| `security_auditor.py` | security_auditor | CVE search, GitHub advisories | github, cve |
| `dependency_mapper.py` | dependency_mapper | Package info, versions | npm, pypi, github |
| `tech_comparator.py` | tech_comparator | Stats (optional) | npm, github |
| `code_quality_critic.py` | code_quality_critic | Commit history (optional) | github |
| `implementation_planner.py` | implementation_planner | None | - |
| `performance_analyst.py` | performance_analyst | None | - |
| `trend_validator.py` | trend_validator | None | - |
| `integration_feasibility.py` | integration_feasibility | None | - |

---

## Files to Create

### 1. `backend/app/services/mcp/registry.py`

**Components:**
- `ToolCapability` dataclass - Describes a tool capability
- `AgentToolConfig` dataclass - Configuration for agent's tool access
- `AGENT_TOOL_CONFIGS` dict - Default agent configurations
- `ToolRegistry` class - Main registry implementation

**Methods:**
```python
class ToolRegistry:
    def __init__(agent_configs: dict | None = None)
    def get_agent_config(agent_type: str) -> AgentToolConfig
    def is_tool_enabled(agent_type: str) -> bool
    def get_capabilities(agent_type: str) -> list[str]
    def filter_tools(tools: list[BaseTool], agent_type: str) -> list[BaseTool]
    def register_agent(config: AgentToolConfig) -> None
    def list_enabled_agents() -> list[str]  # NEW
    def get_all_required_servers() -> set[str]  # NEW - for pool optimization
```

### 2. `backend/tests/unit/services/mcp/test_registry.py`

**Test Cases:**
1. ToolCapability
   - test_capability_id_format

2. AgentToolConfig
   - test_config_defaults
   - test_config_with_all_fields

3. AGENT_TOOL_CONFIGS
   - test_default_configs_exist
   - test_all_8_agents_configured

4. ToolRegistry
   - test_registry_initialization_default
   - test_registry_initialization_custom
   - test_get_agent_config_exists
   - test_get_agent_config_unknown_raises
   - test_is_tool_enabled_true
   - test_is_tool_enabled_false_disabled
   - test_is_tool_enabled_false_no_capabilities
   - test_is_tool_enabled_unknown_agent
   - test_get_capabilities_enabled
   - test_get_capabilities_disabled
   - test_get_capabilities_unknown
   - test_filter_tools_with_matching
   - test_filter_tools_none_matching
   - test_filter_tools_disabled_agent
   - test_register_agent_new
   - test_register_agent_override
   - test_list_enabled_agents
   - test_get_all_required_servers

---

## Implementation Steps

### Step 1: Create ToolCapability and AgentToolConfig dataclasses
- Define capability format validation
- Set sensible defaults for timeouts and max_calls

### Step 2: Define AGENT_TOOL_CONFIGS
- Map all 8 existing agents
- Use capability format: `server:tool_name`
- Configure appropriate limits per agent type

### Step 3: Implement ToolRegistry class
- Initialize with default or custom configs
- Implement all methods from spec
- Add structured logging

### Step 4: Update __init__.py exports
- Export ToolRegistry, AgentToolConfig, ToolCapability
- Export AGENT_TOOL_CONFIGS for testing

### Step 5: Write comprehensive tests
- Cover all methods and edge cases
- Test with mock BaseTool objects

### Step 6: Run CI checks
- ruff format, ruff check, mypy
- All tests passing

---

## Acceptance Criteria Checklist

- [ ] `ToolRegistry` class in `backend/app/services/mcp/registry.py`
- [ ] Agent-to-capability mapping configuration
- [ ] `is_tool_enabled(agent_type)` check
- [ ] `get_capabilities(agent_type)` returns capability list
- [ ] `filter_tools(tools, agent_type)` filters tool list
- [ ] Configuration via Python dict (extensible to YAML later)
- [ ] Unit tests for all registry operations

---

## Dependencies

**Uses:**
- `langchain_core.tools.BaseTool` (for type hints in filter_tools)
- `app.core.logging.get_logger` (structured logging)

**Does NOT use:**
- MCPClientPool (that's for #232)

---

## Definition of Done

1. All acceptance criteria checked
2. 66+ tests passing (existing MCP tests + new registry tests)
3. CI checks pass (ruff format, ruff check, mypy)
4. Verified in dev environment
5. Documentation created
6. Commit with proper message

---

**Last Updated:** December 10, 2025

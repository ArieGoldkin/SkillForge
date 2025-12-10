# Issue #231: Tool Registry & Agent Capability Mapping

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#231](https://github.com/ArieGoldkin/SkillForge/issues/231)
**Blocked By:** #230 (Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Tool Registry & Agent Capability Mapping [3 pts]

**Description:**
Implement `ToolRegistry` for managing which MCP tools each agent can access, preventing tool overload and ensuring agents only see relevant capabilities.

**Labels:** `backend`, `feature`, `sprint-9`, `mcp`

---

## Implementation Summary

### Tasks Completed

- [x] Created `ToolCapability` dataclass for capability identification
- [x] Created `AgentToolConfig` dataclass for agent configuration
- [x] Defined `AGENT_TOOL_CONFIGS` for all 8 content analysis agents
- [x] Implemented `ToolRegistry` class with all methods
- [x] Updated `__init__.py` exports
- [x] Comprehensive unit tests (32 tests, 100% pass rate)
- [x] CI checks pass (ruff format, ruff check, mypy)

### Files Created

**New Files:**
```
backend/app/services/mcp/registry.py   # ToolRegistry, AgentToolConfig, ToolCapability

backend/tests/unit/services/mcp/test_registry.py  # 32 tests
```

**Modified Files:**
- `backend/app/services/mcp/__init__.py` (added exports)

---

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ToolRegistry                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   AGENT_TOOL_CONFIGS                        ││
│  │  ┌──────────────────┐  ┌──────────────────┐                 ││
│  │  │ security_auditor │  │ dependency_mapper│                 ││
│  │  │ enabled: True    │  │ enabled: True    │                 ││
│  │  │ capabilities:    │  │ capabilities:    │                 ││
│  │  │ - github:search  │  │ - npm:get_package│                 ││
│  │  │ - github:alerts  │  │ - pypi:get_pkg   │                 ││
│  │  │ max_calls: 15    │  │ max_calls: 20    │                 ││
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

### Agent Tool Configurations

| Agent | Enabled | Capabilities | Max Calls | Timeout |
|-------|---------|--------------|-----------|---------|
| **security_auditor** | ✓ | github:search_code, github:get_security_advisories | 15 | 30s |
| **dependency_mapper** | ✓ | npm:get_package, pypi:get_package, github:get_repo | 20 | 25s |
| **tech_comparator** | ✓ | npm:get_package, github:get_repo | 10 | 20s |
| **code_quality_critic** | ✓ | github:list_commits, github:get_repo | 12 | 25s |
| implementation_planner | ✗ | None | 0 | 0s |
| performance_analyst | ✗ | None | 0 | 0s |
| trend_validator | ✗ | None | 0 | 0s |
| integration_feasibility | ✗ | None | 0 | 0s |

### Key Design Decisions

**1. Capability Format: `server:tool_name`**
- Consistent naming: `github:get_repo`, `npm:get_package`
- Easy parsing for filtering
- Matches MCP server structure

**2. Agent Isolation:**
- Each agent only sees relevant tools
- Prevents tool overload (agents see ~2-3 tools, not 50+)
- Security: agents can't access unauthorized tools

**3. Rate Limiting:**
- `max_tool_calls`: Prevent runaway tool usage
- `tool_timeout`: Per-tool timeout configuration
- Configurable per agent type

**4. Graceful Unknown Agent Handling:**
- `is_tool_enabled()` returns `False` for unknown agents
- `get_capabilities()` returns empty list for unknown agents
- Only `get_agent_config()` raises `KeyError` for explicit access

---

## Testing

### Test Coverage

**32 tests total, 100% pass rate**

**Test Categories:**

1. **ToolCapability Tests (3 tests)**
   - Capability ID format verification
   - Description handling
   - Equality based on capability_id

2. **AgentToolConfig Tests (4 tests)**
   - Default values validation
   - Full configuration with all fields
   - Disabled by default behavior
   - Multiple capabilities handling

3. **AGENT_TOOL_CONFIGS Tests (5 tests)**
   - Dictionary existence
   - All 8 agents configured
   - Security auditor configuration
   - Dependency mapper configuration
   - Disabled agents verification

4. **ToolRegistry Tests (20 tests)**
   - Initialization (default and custom)
   - Config retrieval (existing and unknown)
   - Tool enablement checks (4 scenarios)
   - Capabilities retrieval (3 scenarios)
   - Tool filtering (3 scenarios)
   - Agent registration (new and override)
   - Enabled agents listing (2 scenarios)
   - Required servers calculation (2 scenarios)

### Test Results

```
============================= test session starts ==============================
collected 98 items

tests/unit/services/mcp/test_client.py       31 passed
tests/unit/services/mcp/test_config.py       19 passed
tests/unit/services/mcp/test_exceptions.py   16 passed
tests/unit/services/mcp/test_registry.py     32 passed

============================== 98 passed in 0.27s ==============================
```

---

## API Reference

### ToolCapability

```python
@dataclass
class ToolCapability:
    """Describes a single MCP tool capability."""
    server: str
    tool_name: str
    description: str = ""

    @property
    def capability_id(self) -> str:
        """Return capability in server:tool format."""
```

### AgentToolConfig

```python
@dataclass
class AgentToolConfig:
    """Configuration for an agent's tool access."""
    agent_type: str
    enabled: bool = False
    capabilities: list[ToolCapability] = field(default_factory=list)
    max_tool_calls: int = 10
    tool_timeout: float = 30.0
```

### ToolRegistry

```python
class ToolRegistry:
    """Registry for managing agent tool access."""

    def __init__(self, agent_configs: dict[str, AgentToolConfig] | None = None) -> None:
        """Initialize with default or custom configurations."""

    def get_agent_config(self, agent_type: str) -> AgentToolConfig:
        """Get config for agent. Raises KeyError if unknown."""

    def is_tool_enabled(self, agent_type: str) -> bool:
        """Check if agent has tool access enabled and has capabilities."""

    def get_capabilities(self, agent_type: str) -> list[str]:
        """Get capability IDs for agent. Returns empty list if disabled/unknown."""

    def filter_tools(self, tools: list[BaseTool], agent_type: str) -> list[BaseTool]:
        """Filter tools to only those matching agent's capabilities."""

    def register_agent(self, config: AgentToolConfig) -> None:
        """Register or update agent configuration."""

    def list_enabled_agents(self) -> list[str]:
        """List agent types that have tools enabled."""

    def get_all_required_servers(self) -> set[str]:
        """Get set of all MCP servers needed by enabled agents."""
```

### Usage Example

```python
from app.services.mcp import MCPClientPool, ToolRegistry, get_mcp_settings

# Initialize
settings = get_mcp_settings()
pool = MCPClientPool(settings.servers)
registry = ToolRegistry()

# Check if agent can use tools
if registry.is_tool_enabled("security_auditor"):
    # Get filtered tools from pool
    async with pool.get_tools("github") as all_tools:
        agent_tools = registry.filter_tools(all_tools, "security_auditor")
        # Only github:search_code and github:get_security_advisories available

# Get required MCP servers
servers = registry.get_all_required_servers()
# {"github", "npm", "pypi"}
```

---

## Verification

### CI Checks

```bash
# All checks pass
poetry run ruff format --check app/services/mcp/   # ✅ 5 files formatted
poetry run ruff check app/services/mcp/            # ✅ All checks passed
poetry run mypy app/services/mcp/ --ignore-missing-imports  # ✅ No issues
```

### Code Quality

- ✅ **Linting:** All checks pass (ruff)
- ✅ **Formatting:** All files formatted
- ✅ **Type Hints:** Complete typing throughout
- ✅ **Docstrings:** All public classes/methods documented
- ✅ **Logging:** Structured logging with structlog

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#230:** MCP Client Pool & Connection Management (dependency - complete)
- **#232:** Tool-Enabled Agent Factory (uses this registry)
- **#233:** Security Auditor MCP Integration (uses this registry)
- **#234:** Dependency Mapper MCP Integration (uses this registry)

---

## Acceptance Criteria Checklist

- [x] `ToolRegistry` class in `backend/app/services/mcp/registry.py`
- [x] Agent-to-capability mapping configuration (AGENT_TOOL_CONFIGS)
- [x] `is_tool_enabled(agent_type)` check
- [x] `get_capabilities(agent_type)` returns capability list
- [x] `filter_tools(tools, agent_type)` filters tool list
- [x] Configuration via Python dict (extensible to YAML later)
- [x] Unit tests for all registry operations (32 tests)

---

**Last Updated:** December 10, 2025

# Issue #236: MCP Integration Tests - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#236](https://github.com/ArieGoldkin/SkillForge/issues/236)
**Blocked By:** #230-#235 (All Complete)

---

## Objective

Create comprehensive integration tests that validate the complete MCP flow from agent runners through ToolRegistry to MCPClientPool, ensuring end-to-end functionality and graceful degradation.

---

## Current State Analysis

### What Exists

```
┌─────────────────────────────────────────────────────────────────┐
│                    Existing Unit Test Coverage                   │
├─────────────────────────────────────────────────────────────────┤
│ ✅ test_client.py          - MCPClientPool, MCPConnection (27)  │
│ ✅ test_config.py          - MCPSettings, MCPServerConfig (20)  │
│ ✅ test_registry.py        - ToolRegistry, AgentToolConfig (20) │
│ ✅ test_exceptions.py      - MCP exception hierarchy (12)       │
│ ✅ test_error_handling.py  - Retry/timeout patterns (29)        │
│ ✅ test_security_auditor_mcp.py   - Agent MCP integration (15)  │
│ ✅ test_dependency_mapper_mcp.py  - Agent MCP integration (15)  │
│ ✅ test_tool_enabled_agent.py     - Tool-enabled factory (20)   │
├─────────────────────────────────────────────────────────────────┤
│                     Total: ~158 unit tests                       │
└─────────────────────────────────────────────────────────────────┘
```

### What's Missing

```
┌─────────────────────────────────────────────────────────────────┐
│                    Missing Integration Tests                     │
├─────────────────────────────────────────────────────────────────┤
│ ❌ End-to-end: Runner → Registry → Pool → Tools → Agent        │
│ ❌ Real tool loading lifecycle (connect → load → cache)          │
│ ❌ Graceful degradation with actual exception flows              │
│ ❌ Circuit breaker activation across multiple failures           │
│ ❌ Multi-agent concurrent MCP access                             │
│ ❌ Retry behavior under transient failures                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Integration Test Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                            │
│  │  Agent Runner   │  run_security_auditor_with_session()       │
│  │  (runners.py)   │  run_dependency_mapper_with_session()      │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  ToolRegistry   │  is_tool_enabled(), get_capabilities()     │
│  │  (registry.py)  │  filter_tools()                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ MCPClientPool   │  get_tools_for_capabilities()              │
│  │  (client.py)    │  _load_tools() with retry/timeout          │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Mock MCP Server │  Returns BaseTool mocks                    │
│  │  (fixtures)     │  Simulates failures for resilience tests   │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Test Categories

### Phase 1: Core MCP Flow (3 tests)

| Test | Description |
|------|-------------|
| `test_mcp_pool_tool_loading_lifecycle` | Connect → Load → Cache → Disconnect |
| `test_registry_filters_tools_by_agent` | Real tools matched against agent capabilities |
| `test_security_auditor_end_to_end_with_mcp` | Full flow: Runner → Tools → Agent execution |

### Phase 2: Resilience & Degradation (3 tests)

| Test | Description |
|------|-------------|
| `test_graceful_degradation_mcp_disabled` | Agent works when MCP unavailable |
| `test_circuit_breaker_after_consecutive_failures` | Connection marked ERROR after 3 failures |
| `test_retry_succeeds_after_transient_failure` | Exponential backoff recovers from failure |

### Phase 3: Multi-Agent Scenarios (2 tests)

| Test | Description |
|------|-------------|
| `test_dependency_mapper_end_to_end_with_mcp` | Full flow for dependency_mapper |
| `test_parallel_agents_share_mcp_pool` | Concurrent agents use cached tools |

---

## File Structure

```
backend/tests/integration/mcp/
├── __init__.py
├── conftest.py                           # MCP integration fixtures
├── test_mcp_pool_integration.py          # Phase 1: Pool lifecycle
├── test_registry_integration.py          # Phase 1: Registry flow
├── test_agent_mcp_end_to_end.py          # Phase 1 & 3: Agent integration
└── test_mcp_resilience.py                # Phase 2: Degradation & recovery
```

---

## Implementation Details

### 1. Fixtures (conftest.py)

```python
@pytest.fixture
def mock_github_tool():
    """Mock GitHub MCP tool for testing."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "github_search_code"
    tool.description = "Search GitHub code"
    tool.ainvoke = AsyncMock(return_value={"results": []})
    return tool

@pytest.fixture
def mock_npm_tool():
    """Mock npm MCP tool for testing."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "npm_get_package"
    tool.description = "Get npm package info"
    tool.ainvoke = AsyncMock(return_value={"name": "react"})
    return tool

@pytest.fixture
def mcp_server_configs():
    """Real MCPServerConfig objects for integration tests."""
    return {
        "github": MCPServerConfig(
            name="github",
            transport=MCPTransport.STDIO,
            command="echo",  # Mock command
            enabled=True,
            timeout=5.0,
            max_retries=2,
        ),
        "npm": MCPServerConfig(
            name="npm",
            transport=MCPTransport.STDIO,
            command="echo",
            enabled=True,
        ),
    }

@pytest.fixture
async def mcp_pool_with_mock_client(mcp_server_configs, mock_github_tool, mock_npm_tool):
    """MCPClientPool with mocked MultiServerMCPClient."""
    pool = MCPClientPool(mcp_server_configs)

    # Mock the internal client creation
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_tools = MagicMock(return_value=[mock_github_tool, mock_npm_tool])

    pool._client = mock_client
    return pool
```

### 2. Pool Integration Tests (test_mcp_pool_integration.py)

```python
class TestMCPPoolLifecycle:
    """Integration tests for MCPClientPool lifecycle."""

    @pytest.mark.asyncio
    async def test_pool_connects_and_loads_tools(self, mcp_pool_with_mock_client):
        """Pool transitions through connection states and loads tools."""
        pool = mcp_pool_with_mock_client

        # Initially disconnected
        assert pool._connections == {}

        # Load tools triggers connection
        async with pool.get_tools("github") as tools:
            assert len(tools) > 0
            conn = pool._connections.get("github")
            assert conn.state == ConnectionState.CONNECTED
            assert conn.is_healthy()

    @pytest.mark.asyncio
    async def test_pool_caches_tools_across_calls(self, mcp_pool_with_mock_client):
        """Tools are cached after first load."""
        pool = mcp_pool_with_mock_client

        # First call loads tools
        async with pool.get_tools("github") as tools1:
            first_count = len(tools1)

        # Second call uses cache
        async with pool.get_tools("github") as tools2:
            assert len(tools2) == first_count

        # Verify client.get_tools only called once (caching works)
        assert pool._client.get_tools.call_count == 1
```

### 3. Agent End-to-End Tests (test_agent_mcp_end_to_end.py)

```python
class TestSecurityAuditorMCPEndToEnd:
    """End-to-end tests for Security Auditor with MCP tools."""

    @pytest.mark.asyncio
    @pytest.mark.mcp
    async def test_security_auditor_receives_mcp_tools(
        self, mcp_pool_with_mock_client, mock_github_tool
    ):
        """Security auditor runner loads and passes MCP tools."""
        # Mock the MCP imports in runners.py
        with patch("app.services.mcp.MCPClientPool") as MockPool:
            MockPool.return_value = mcp_pool_with_mock_client

            with patch("app.services.mcp.ToolRegistry") as MockRegistry:
                mock_registry = MagicMock()
                mock_registry.is_tool_enabled.return_value = True
                mock_registry.get_capabilities.return_value = ["github:search_code"]
                MockRegistry.return_value = mock_registry

                # Verify tools would be passed to agent
                # (Full execution requires LLM, so we test the loading flow)
                ...
```

### 4. Resilience Tests (test_mcp_resilience.py)

```python
class TestGracefulDegradation:
    """Tests for MCP graceful degradation."""

    @pytest.mark.asyncio
    async def test_agent_works_when_mcp_disabled(self):
        """Agent executes via structured path when MCP unavailable."""
        with patch("app.services.mcp.get_mcp_settings") as mock_settings:
            mock_settings.return_value.enabled = False

            # Agent should still work, just without tools
            # Verify create_structured_agent is used instead of tool-enabled

    @pytest.mark.asyncio
    async def test_agent_works_when_mcp_connection_fails(self):
        """Agent falls back gracefully on MCPConnectionError."""
        with patch("app.services.mcp.MCPClientPool") as MockPool:
            MockPool.return_value.get_tools_for_capabilities = AsyncMock(
                side_effect=MCPConnectionError("Connection refused")
            )

            # Should catch exception and continue with tools=[]


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_connection_marked_error_after_3_failures(
        self, mcp_server_configs
    ):
        """Circuit breaker activates after MAX_CONSECUTIVE_ERRORS."""
        pool = MCPClientPool(mcp_server_configs)
        conn = pool._get_or_create_connection("github")

        # Simulate 3 consecutive errors
        conn.record_error("Error 1")
        conn.record_error("Error 2")
        assert conn.is_healthy()  # Still healthy at 2 errors

        conn.record_error("Error 3")
        assert not conn.is_healthy()  # Now unhealthy
        assert conn.state == ConnectionState.ERROR
```

---

## Test Markers

```python
# pytest.ini or pyproject.toml
markers = [
    "mcp: MCP-related tests",
    "mcp_integration: Full MCP integration flow",
    "slow: Slow tests (skip with -m 'not slow')",
    "requires_mcp: Tests that require MCP to be enabled",
]
```

---

## Mocking Strategy

| Level | Use Case | Implementation |
|-------|----------|----------------|
| **Level 1: Lightweight** | Basic flow validation | Mock MCPClientPool methods |
| **Level 2: Behavioral** | Tool loading behavior | Mock MultiServerMCPClient |
| **Level 3: Real** | Full validation (CI nightly) | Real MCP servers (optional) |

**Default:** Level 2 (Behavioral) - Tests real MCPClientPool logic with mocked transport layer.

---

## Execution Strategy

```bash
# Fast: Unit tests only
poetry run pytest tests/unit/services/mcp/ -v

# Medium: Unit + Integration (mocked)
poetry run pytest tests/unit/services/mcp/ tests/integration/mcp/ -v

# Full: All MCP tests including slow
poetry run pytest tests/unit/services/mcp/ tests/integration/mcp/ -v --slow

# CI default: Skip slow and external
poetry run pytest -m "not slow and not external"
```

---

## Acceptance Criteria

- [ ] `test_mcp_pool_integration.py` - Pool lifecycle tests (3+ tests)
- [ ] `test_registry_integration.py` - Registry flow tests (2+ tests)
- [ ] `test_agent_mcp_end_to_end.py` - Agent integration tests (3+ tests)
- [ ] `test_mcp_resilience.py` - Graceful degradation tests (4+ tests)
- [ ] Integration fixtures in `conftest.py`
- [ ] All tests pass with mocked MCP
- [ ] CI checks pass (ruff, mypy)

---

## Dependencies

- tenacity (already installed for retry)
- pytest-asyncio (already installed)
- unittest.mock (standard library)

---

**Last Updated:** December 10, 2025

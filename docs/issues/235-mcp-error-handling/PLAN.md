# Issue #235: MCP Error Handling & Resilience - Implementation Plan

**Status:** Planning
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#235](https://github.com/ArieGoldkin/SkillForge/issues/235)
**Blocked By:** #230 (Complete), #231 (Complete)

---

## Objective

Enhance MCP client with production-grade error handling: async timeout enforcement, exponential backoff retry logic, and improved circuit breaker behavior.

---

## Current State Analysis

### What Exists

```
┌─────────────────────────────────────────────────────────────────┐
│                    Current Error Handling                        │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Exception hierarchy (MCPError, MCPTimeoutError, etc.)        │
│ ✅ Circuit breaker state machine (DISCONNECTED→CONNECTED→ERROR) │
│ ✅ MAX_CONSECUTIVE_ERRORS = 3 threshold                          │
│ ✅ Per-server timeout config (MCPServerConfig.timeout)           │
│ ✅ Per-agent tool timeout (AgentToolConfig.tool_timeout)         │
│ ✅ max_retries config field (defined but NOT implemented)        │
│ ✅ health_check() method for manual checks                       │
└─────────────────────────────────────────────────────────────────┘
```

### What's Missing

```
┌─────────────────────────────────────────────────────────────────┐
│                      Missing Components                          │
├─────────────────────────────────────────────────────────────────┤
│ ❌ Async timeout enforcement (asyncio.timeout)                   │
│ ❌ Retry logic with exponential backoff (tenacity)               │
│ ❌ Tool call timeout wrapping                                    │
│ ❌ Connection retry on failure                                   │
│ ❌ Detailed error context (attempt counts, wait times)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCPClientPool                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Retry Decorator (tenacity)                  │    │
│  │  @retry(stop=3, wait=exponential(min=1, max=16))        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            Timeout Context Manager                       │    │
│  │  async with asyncio.timeout(tool_timeout):              │    │
│  │      result = await tool.ainvoke(...)                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Error Classification & Logging                 │    │
│  │  - MCPTimeoutError with context                          │    │
│  │  - MCPConnectionError with retry info                    │    │
│  │  - Structured logging for observability                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Changes

### 1. Add Retry Configuration Constants (constants.py or client.py)

```python
# Retry configuration
MCP_RETRY_ATTEMPTS = 3
MCP_RETRY_MIN_WAIT = 1.0  # seconds
MCP_RETRY_MAX_WAIT = 16.0  # seconds
MCP_RETRY_MULTIPLIER = 2.0  # exponential backoff multiplier
```

### 2. Create Retry Decorator Helper (client.py)

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

def create_mcp_retry_decorator(
    max_attempts: int = MCP_RETRY_ATTEMPTS,
    min_wait: float = MCP_RETRY_MIN_WAIT,
    max_wait: float = MCP_RETRY_MAX_WAIT,
):
    """Create a retry decorator for MCP operations."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=MCP_RETRY_MULTIPLIER, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((MCPConnectionError, MCPTimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
```

### 3. Add Timeout Wrapper Function (client.py)

```python
async def execute_with_timeout(
    coro: Coroutine,
    timeout_seconds: float,
    operation_name: str,
    server_name: str | None = None,
) -> Any:
    """Execute a coroutine with timeout enforcement.

    Args:
        coro: The coroutine to execute
        timeout_seconds: Maximum execution time
        operation_name: Name for logging (e.g., "tool_call", "connect")
        server_name: Optional server name for context

    Returns:
        Result of the coroutine

    Raises:
        MCPTimeoutError: If timeout exceeded
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            return await coro
    except asyncio.TimeoutError as e:
        raise MCPTimeoutError(
            f"{operation_name} timed out after {timeout_seconds}s",
            timeout_seconds=timeout_seconds,
            server_name=server_name,
        ) from e
```

### 4. Update _load_tools() with Retry (client.py)

```python
async def _load_tools(self, server_name: str) -> list[BaseTool]:
    """Load tools from server with retry logic."""
    connection = self._connections.get(server_name)
    if not connection:
        raise MCPConnectionError(f"No connection for server: {server_name}")

    config = self._server_configs.get(server_name)
    timeout = config.timeout if config else 30.0
    max_retries = config.max_retries if config else 3

    @create_mcp_retry_decorator(max_attempts=max_retries)
    async def _load_with_retry() -> list[BaseTool]:
        return await execute_with_timeout(
            self._adapter.load_tools(connection.session),
            timeout_seconds=timeout,
            operation_name="load_tools",
            server_name=server_name,
        )

    try:
        tools = await _load_with_retry()
        logger.info("loaded_tools_from_server", server=server_name, count=len(tools))
        return tools
    except Exception as e:
        connection.record_error(str(e))
        logger.error("failed_to_load_tools", server=server_name, error=str(e))
        raise
```

### 5. Update Exception Classes (exceptions.py)

```python
@dataclass
class MCPTimeoutError(MCPError):
    """Timeout during MCP operation."""
    timeout_seconds: float | None = None
    server_name: str | None = None
    operation: str | None = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.timeout_seconds:
            parts.append(f"(timeout={self.timeout_seconds}s)")
        if self.server_name:
            parts.append(f"[server={self.server_name}]")
        return " ".join(parts)


@dataclass
class MCPConnectionError(MCPError):
    """Connection error with retry context."""
    server_name: str | None = None
    attempt: int | None = None
    max_attempts: int | None = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.attempt and self.max_attempts:
            parts.append(f"(attempt {self.attempt}/{self.max_attempts})")
        if self.server_name:
            parts.append(f"[server={self.server_name}]")
        return " ".join(parts)
```

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/services/mcp/client.py` | **MODIFY** | Add retry decorator, timeout wrapper, update _load_tools |
| `backend/app/services/mcp/exceptions.py` | **MODIFY** | Enhance exception classes with context |

## Files to Create

| File | Description |
|------|-------------|
| `backend/tests/unit/services/mcp/test_error_handling.py` | Unit tests for retry/timeout |
| `docs/issues/235-mcp-error-handling/README.md` | Documentation |

---

## Test Cases

### test_error_handling.py

```python
class TestExecuteWithTimeout:
    async def test_returns_result_within_timeout(self):
        """Successful execution returns result."""

    async def test_raises_timeout_error_when_exceeded(self):
        """Raises MCPTimeoutError when timeout exceeded."""

    async def test_timeout_error_includes_context(self):
        """MCPTimeoutError includes timeout_seconds and server_name."""

class TestRetryDecorator:
    async def test_retries_on_connection_error(self):
        """Retries when MCPConnectionError raised."""

    async def test_retries_on_timeout_error(self):
        """Retries when MCPTimeoutError raised."""

    async def test_stops_after_max_attempts(self):
        """Stops retrying after max_attempts."""

    async def test_exponential_backoff_wait_times(self):
        """Wait times increase exponentially."""

    async def test_does_not_retry_on_other_errors(self):
        """Does not retry on non-retryable errors."""

class TestLoadToolsWithRetry:
    async def test_successful_load_no_retry(self):
        """Successful load doesn't trigger retry."""

    async def test_retries_on_transient_failure(self):
        """Retries and succeeds on transient failure."""

    async def test_records_error_on_final_failure(self):
        """Records error in connection on final failure."""
```

---

## Reference Implementation

From `jina_reader.py` (proven pattern in codebase):

```python
@retry(
    stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=RETRY_MULTIPLIER_JINA, min=2, max=60),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _fetch_url(self, url: str) -> str:
    ...
```

---

## Acceptance Criteria

- [ ] `execute_with_timeout()` function enforces async timeouts
- [ ] `create_mcp_retry_decorator()` provides configurable retry logic
- [ ] `_load_tools()` uses retry decorator with exponential backoff
- [ ] Exception classes include context (timeout_seconds, attempt, server_name)
- [ ] Unit tests for timeout and retry behavior
- [ ] CI checks pass

---

**Last Updated:** December 10, 2025

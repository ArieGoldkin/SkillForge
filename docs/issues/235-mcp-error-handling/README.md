# Issue #235: MCP Error Handling & Resilience

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 3 pts
**GitHub Issue:** [#235](https://github.com/ArieGoldkin/SkillForge/issues/235)
**Blocked By:** #230 (Complete), #231 (Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Error Handling & Resilience [3 pts]

**Description:**
Enhance MCP client with production-grade error handling: async timeout enforcement, exponential backoff retry logic, and improved circuit breaker behavior.

**Labels:** `backend`, `feature`, `sprint-9`, `mcp`

---

## Implementation Summary

### Tasks Completed

- [x] Researched existing error handling patterns (jina_reader.py)
- [x] Created implementation plan (`PLAN.md`)
- [x] Implemented `execute_with_timeout()` async timeout enforcement
- [x] Implemented `create_mcp_retry_decorator()` with tenacity
- [x] Updated `_load_tools()` with retry and timeout logic
- [x] Enhanced exception classes with context (already existed from #230)
- [x] Comprehensive unit tests (29 tests, 100% pass rate)
- [x] CI checks pass (ruff format, ruff check, mypy)

### Files Modified

**Modified Files:**
```
backend/app/services/mcp/client.py      # Added timeout/retry functions, updated _load_tools
backend/app/services/mcp/__init__.py    # Exported new functions and constants
```

**New Files:**
```
backend/tests/unit/services/mcp/test_error_handling.py  # 29 tests
docs/issues/235-mcp-error-handling/PLAN.md              # Implementation plan
docs/issues/235-mcp-error-handling/README.md            # This file
```

---

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCPClientPool._load_tools()                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         create_mcp_retry_decorator(max_attempts=3)       │    │
│  │  @retry(stop=3, wait=exponential(min=1, max=16))        │    │
│  │  retry_if_exception_type(MCPConnectionError|Timeout)     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         execute_with_timeout(coro, timeout_seconds)      │    │
│  │  async with asyncio.timeout(config.timeout):            │    │
│  │      result = await client.get_tools()                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Error Classification & Recovery                │    │
│  │  - MCPTimeoutError with context (timeout_seconds)       │    │
│  │  - MCPConnectionError with retry info (attempt/max)     │    │
│  │  - Structured logging for observability                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes

#### 1. Retry Configuration Constants (client.py)

```python
# Retry configuration constants
MCP_RETRY_ATTEMPTS = 3
MCP_RETRY_MIN_WAIT = 1.0  # seconds
MCP_RETRY_MAX_WAIT = 16.0  # seconds
MCP_RETRY_MULTIPLIER = 2.0  # exponential backoff multiplier
```

#### 2. execute_with_timeout() (client.py)

```python
async def execute_with_timeout[T](
    coro: Awaitable[T],
    timeout_seconds: float,
    operation_name: str,
    server_name: str | None = None,
) -> T:
    """Execute an awaitable with timeout enforcement.

    Wraps any async operation with asyncio.timeout to ensure it completes
    within the specified time limit. Converts TimeoutError to MCPTimeoutError
    with rich context for debugging and monitoring.
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            return await coro
    except TimeoutError as e:
        msg = f"{operation_name} timed out after {timeout_seconds}s"
        raise MCPTimeoutError(
            msg,
            server_name=server_name,
            tool_name=operation_name,
            timeout_seconds=timeout_seconds,
        ) from e
```

#### 3. create_mcp_retry_decorator() (client.py)

```python
def create_mcp_retry_decorator(
    max_attempts: int = MCP_RETRY_ATTEMPTS,
    min_wait: float = MCP_RETRY_MIN_WAIT,
    max_wait: float = MCP_RETRY_MAX_WAIT,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Create a retry decorator for MCP operations.

    Returns a tenacity retry decorator configured for MCP-specific error
    handling with exponential backoff. Only retries on transient errors.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=MCP_RETRY_MULTIPLIER, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((MCPConnectionError, MCPTimeoutError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
```

#### 4. Updated _load_tools() (client.py)

```python
async def _load_tools(self, conn: MCPConnection) -> None:
    """Load tools from MCP server into connection with retry logic."""
    conn.state = ConnectionState.CONNECTING

    # Get timeout and max_retries from config
    timeout = conn.config.timeout if conn.config else 30.0
    max_retries = conn.config.max_retries if conn.config else MCP_RETRY_ATTEMPTS

    # Create retry decorator with config-based settings
    retry_decorator = create_mcp_retry_decorator(max_attempts=max_retries)

    @retry_decorator
    async def _load_with_retry() -> list[BaseTool]:
        client = await self._ensure_client()

        async def _do_load() -> list[BaseTool]:
            async with client:
                tools: list[BaseTool] = client.get_tools()
                return tools

        tools = await execute_with_timeout(
            _do_load(),
            timeout_seconds=timeout,
            operation_name="load_tools",
            server_name=conn.server_name,
        )
        # ... filter tools by server ...
        return server_tools

    try:
        conn.tools = await _load_with_retry()
        conn.state = ConnectionState.CONNECTED
        conn.record_success()
    except (MCPConnectionError, MCPTimeoutError) as e:
        conn.state = ConnectionState.ERROR
        conn.record_error(str(e))
        raise
```

---

## Exponential Backoff Behavior

| Attempt | Wait Time | Notes |
|---------|-----------|-------|
| 1 | 1.0s (min) | First retry |
| 2 | 2.0s | Doubles |
| 3 | 4.0s | Doubles again |
| 4+ | 8.0s, 16.0s (max) | Capped at max_wait |

**Pattern:** `min(max_wait, min_wait * multiplier^attempt)`

---

## Testing

### Test Coverage

**29 tests total, 100% pass rate**

**Test Categories:**

1. **TestRetryConstants (4 tests)**
   - Retry attempts is 3
   - Minimum wait is 1 second
   - Maximum wait is 16 seconds
   - Multiplier is 2.0

2. **TestExecuteWithTimeout (6 tests)**
   - Returns result within timeout
   - Raises MCPTimeoutError when exceeded
   - Error includes timeout_seconds
   - Error includes server_name
   - Error includes tool_name
   - Preserves original exception as __cause__

3. **TestRetryDecorator (7 tests)**
   - Retries on connection error
   - Retries on timeout error
   - Stops after max attempts
   - Does not retry on other errors
   - Re-raises final exception
   - Custom max_attempts works
   - Decorator returns callable

4. **TestLoadToolsWithRetry (6 tests)**
   - Uses config timeout
   - Uses config max_retries
   - Uses retry decorator
   - Uses execute_with_timeout
   - Handles MCPTimeoutError
   - Has graceful error handling

5. **TestExceptionContext (4 tests)**
   - MCPConnectionError with attempt info
   - MCPTimeoutError with context
   - MCPConnectionError without retry info
   - MCPConnectionError without server

6. **TestBackoffTiming (2 tests)**
   - Exponential backoff configuration
   - Wait sequence is exponential

### Test Results

```
============================= test session starts ==============================
collected 29 items

tests/unit/services/mcp/test_error_handling.py       29 passed

============================= 29 passed in 46.25s ==============================
```

### Full MCP Test Suite

```
============================= test session starts ==============================
collected 127 items

tests/unit/services/mcp/                             127 passed

============================= 127 passed in 46.40s =============================
```

---

## Reference Implementation

Pattern inspired by `jina_reader.py`:

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

## Error Flow Diagram

```
┌─────────────────┐
│  Tool Loading   │
│    Request      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     timeout exceeded
│ execute_with_   │─────────────────────────┐
│ timeout()       │                          │
└────────┬────────┘                          ▼
         │ success                   ┌───────────────┐
         │                           │MCPTimeoutError│
         ▼                           │ (retryable)   │
┌─────────────────┐                  └───────┬───────┘
│    Tool Load    │                          │
│    Attempt      │                          │
└────────┬────────┘                          │
         │                                    │
         │ failure                           │
         ▼                                    ▼
┌─────────────────┐              ┌────────────────────┐
│MCPConnectionErr │◄─────────────│   Retry Logic      │
│ (retryable)     │              │ (exponential back) │
└────────┬────────┘              └────────────────────┘
         │                                    │
         │ max attempts                       │
         ▼                                    │
┌─────────────────┐                          │
│ Final Exception │◄─────────────────────────┘
│ (re-raised)     │
└─────────────────┘
```

---

## API Reference

### execute_with_timeout

```python
async def execute_with_timeout[T](
    coro: Awaitable[T],
    timeout_seconds: float,
    operation_name: str,
    server_name: str | None = None,
) -> T:
    """Execute an awaitable with timeout enforcement.

    Args:
        coro: The awaitable to execute
        timeout_seconds: Maximum execution time in seconds
        operation_name: Name for logging (e.g., "load_tools", "tool_call")
        server_name: Optional MCP server name for context

    Returns:
        Result of the awaitable

    Raises:
        MCPTimeoutError: If timeout exceeded
    """
```

### create_mcp_retry_decorator

```python
def create_mcp_retry_decorator(
    max_attempts: int = MCP_RETRY_ATTEMPTS,
    min_wait: float = MCP_RETRY_MIN_WAIT,
    max_wait: float = MCP_RETRY_MAX_WAIT,
) -> Callable[...]:
    """Create a retry decorator for MCP operations.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        min_wait: Minimum wait time between retries (default: 1.0)
        max_wait: Maximum wait time between retries (default: 16.0)

    Returns:
        Configured tenacity retry decorator
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

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#230:** MCP Client Pool & Connection Management (dependency - complete)
- **#231:** Tool Registry & Agent Capability Mapping (dependency - complete)
- **#232:** Tool-Enabled Agent Factory (complete)
- **#233:** Security Auditor MCP Integration (complete)
- **#234:** Dependency Mapper MCP Integration (complete)
- **#236:** MCP Integration Tests (will test full flow)

---

## Acceptance Criteria Checklist

- [x] `execute_with_timeout()` function enforces async timeouts
- [x] `create_mcp_retry_decorator()` provides configurable retry logic
- [x] `_load_tools()` uses retry decorator with exponential backoff
- [x] Exception classes include context (timeout_seconds, attempt, server_name)
- [x] Unit tests for timeout and retry behavior (29 tests)
- [x] CI checks pass

---

**Last Updated:** December 10, 2025

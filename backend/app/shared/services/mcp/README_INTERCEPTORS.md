# MCP Tool Call Interceptors

This module implements interceptors for `langchain-mcp-adapters 0.2` to provide cross-cutting concerns for MCP tool calls.

## Overview

Interceptors use the chain-of-responsibility pattern to wrap MCP tool execution with functionality like:
- **Authentication**: Inject auth headers from configuration
- **Retry Logic**: Exponential backoff retry for transient failures
- **Result Enrichment**: Add timing and trace correlation metadata
- **Logging**: Structured logging with Langfuse trace correlation

## Quick Start

```python
from app.shared.services.mcp.config import get_mcp_settings
from app.shared.services.mcp.interceptors import create_default_interceptors
from langchain_mcp_adapters.client import MultiServerMCPClient

# Get MCP configuration
settings = get_mcp_settings()

# Create interceptor chain (all enabled by default)
interceptors = create_default_interceptors(settings)

# Create MCP client with interceptors
client = MultiServerMCPClient(
    connections={name: cfg.to_langchain_config() for name, cfg in settings.servers.items()},
    tool_interceptors=interceptors,
)

# Use tools - interceptors automatically handle auth, retry, logging
tools = await client.get_tools(server_name="github")
result = await tools[0].ainvoke({"repo": "langchain-ai/langchain"})
```

## Available Interceptors

### 1. AuthInterceptor

Injects authentication headers from server configuration.

```python
from app.shared.services.mcp.interceptors import AuthInterceptor

# Create auth interceptor
auth = AuthInterceptor(settings)

# Headers from settings.servers["github"].headers will be injected
# into all tool calls to the "github" server
```

**Configuration:**
- Headers defined in `MCPServerConfig.headers`
- Merges with existing request headers (auth headers take precedence)
- Only affects servers with configured headers

### 2. RetryInterceptor

Retries tool calls on transient failures with exponential backoff.

```python
from app.shared.services.mcp.interceptors import RetryInterceptor

# Create retry interceptor
retry = RetryInterceptor(settings)

# Automatically retries on:
# - MCPConnectionError (connection failures)
# - MCPTimeoutError (timeout errors)
#
# Does NOT retry on:
# - Permanent errors (ValueError, TypeError, etc.)
```

**Configuration:**
- Max retries from `MCPServerConfig.max_retries` (default: 3)
- Exponential backoff: 1s, 2s, 4s, 8s, 16s (capped)
- Logs warnings before each retry

### 3. ResultEnrichmentInterceptor

Adds observability metadata to tool call results.

```python
from app.shared.services.mcp.interceptors import ResultEnrichmentInterceptor

# Create enrichment interceptor
enrichment = ResultEnrichmentInterceptor()

# Logs metadata:
# - Server name (for routing/debugging)
# - Duration in seconds
# - Trace correlation ID (UUID)
# - Success/failure status
```

**Logged Fields:**
- `server`: Server name
- `tool`: Tool name
- `duration_seconds`: Execution time
- `trace_id`: Correlation UUID
- `success`: True/False

### 4. LoggingInterceptor

Structured logging for all tool calls with Langfuse trace correlation.

```python
from app.shared.services.mcp.interceptors import LoggingInterceptor

# Create logging interceptor
# log_arguments=False (default) - only log argument keys (privacy)
# log_arguments=True - log full arguments (may contain sensitive data)
logging = LoggingInterceptor(log_arguments=False)

# Logs events:
# - mcp_tool_call_start (when tool call begins)
# - mcp_tool_call_complete (when tool call succeeds)
# - mcp_tool_call_error (when tool call fails)
```

**Logged Fields:**
- `server`: Server name
- `tool`: Tool name
- `args`: Argument keys (or full args if `log_arguments=True`)
- `duration_seconds`: Execution time
- `langfuse_trace_id`: Trace ID from LangGraph runtime (if available)

## Customization

### Using InterceptorConfig

```python
from app.shared.services.mcp.interceptors import InterceptorConfig, create_default_interceptors

# Customize which interceptors to enable
config = InterceptorConfig(
    enable_auth=True,
    enable_retry=True,
    enable_enrichment=False,  # Disable enrichment
    enable_logging=True,
    log_arguments=False,  # Privacy: don't log sensitive data
)

interceptors = create_default_interceptors(settings, config)
```

### Custom Interceptor Chain

```python
from app.shared.services.mcp.interceptors import AuthInterceptor, LoggingInterceptor

# Build custom chain (order matters!)
interceptors = [
    LoggingInterceptor(log_arguments=False),  # Outermost
    AuthInterceptor(settings),                # Inner
]

client = MultiServerMCPClient(
    connections=server_configs,
    tool_interceptors=interceptors,
)
```

## Interceptor Execution Order

Interceptors compose in "onion" pattern where the **first interceptor is outermost**:

```
Request Flow:
  Request
    → Logging (outermost - sees request first)
      → Auth (injects headers)
        → Retry (handles failures)
          → Enrichment (adds metadata)
            → Handler (actual tool execution)
              → Enrichment (adds metadata)
            → Retry (handles failures)
          → Auth (returns result)
        → Logging (logs result)
      → Result

Default Order:
  1. LoggingInterceptor (logs all requests/responses)
  2. AuthInterceptor (injects auth headers)
  3. RetryInterceptor (retries transient failures)
  4. ResultEnrichmentInterceptor (adds observability metadata)
```

**Why this order?**
- Logging sees everything (including retries)
- Auth happens before retry (no need to re-inject on retry)
- Retry wraps the actual call
- Enrichment is closest to handler (accurate timing)

## Writing Custom Interceptors

Implement the `ToolCallInterceptor` protocol:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from langchain_mcp_adapters.interceptors import (
        MCPToolCallRequest,
        MCPToolCallResult,
    )

class MyCustomInterceptor:
    """Example custom interceptor."""

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        """Intercept tool execution.

        Args:
            request: Tool call request with:
                - name: Tool name
                - args: Tool arguments
                - server_name: MCP server (read-only context)
                - headers: HTTP headers (modifiable)
                - runtime: LangGraph runtime (read-only context)
            handler: Next interceptor or actual tool execution

        Returns:
            Result from handler (or short-circuit)
        """
        # Before handler: modify request
        print(f"Calling {request.server_name}:{request.name}")

        # Optionally modify request
        if request.server_name == "special":
            modified_request = request.override(
                headers={**(request.headers or {}), "X-Custom": "value"}
            )
            result = await handler(modified_request)
        else:
            result = await handler(request)

        # After handler: process result
        print(f"Got result from {request.name}")
        return result
```

## Testing

All interceptors have comprehensive unit tests in `tests/unit/shared/services/mcp/test_interceptors.py`:

```bash
# Run interceptor tests
poetry run pytest tests/unit/shared/services/mcp/test_interceptors.py -v

# Test specific interceptor
poetry run pytest tests/unit/shared/services/mcp/test_interceptors.py::test_auth_interceptor_injects_headers_for_configured_server -v
```

## Configuration Reference

### MCPServerConfig

```python
from app.shared.services.mcp.config import MCPServerConfig, MCPTransport

config = MCPServerConfig(
    name="github",
    transport=MCPTransport.STDIO,
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    headers={"Authorization": "Bearer TOKEN"},  # Used by AuthInterceptor
    max_retries=3,  # Used by RetryInterceptor
    timeout=30.0,
)
```

### Environment Variables

```bash
# Enable/disable MCP globally
MCP_ENABLED=true

# Default timeout for all operations
MCP_DEFAULT_TIMEOUT=30.0

# GitHub token (injected into headers)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx
```

## Best Practices

1. **Privacy**: Use `log_arguments=False` to avoid logging sensitive data
2. **Order**: Place logging interceptors outermost to see all activity
3. **Retry**: Only retry transient errors (connection/timeout), not permanent errors
4. **Headers**: Use `MCPServerConfig.headers` for auth tokens, not hardcoded in code
5. **Testing**: Test custom interceptors with mock handlers

## Performance Considerations

- **Logging**: Minimal overhead (~1ms), structured logs batch automatically
- **Retry**: Only retries on transient errors, exponential backoff prevents thundering herd
- **Enrichment**: Metadata logged separately, doesn't modify result object
- **Auth**: Headers merged once per request, no additional overhead

## Troubleshooting

### Interceptors not being called

- Check that interceptors are passed to `MultiServerMCPClient` constructor
- Verify server name in `MCPServerConfig` matches tool call server name

### Retry not working

- Ensure error is `MCPConnectionError` or `MCPTimeoutError`
- Check `max_retries` in server config (must be > 1)
- Look for `mcp_tool_retry` log events

### Auth headers not injected

- Verify `headers` configured in `MCPServerConfig`
- Check that server name matches (case-sensitive)
- Look for `mcp_auth_injected` log event

### Logs missing

- Ensure `enable_logging=True` in `InterceptorConfig`
- Check log level (must be INFO or DEBUG)
- Verify structlog is configured (`app.core.logging.setup_logging()`)

## References

- [langchain-mcp-adapters 0.2 Documentation](https://github.com/langchain-ai/langchain-mcp-adapters)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Tenacity Retry Library](https://tenacity.readthedocs.io/)
- [Structlog Documentation](https://www.structlog.org/)

# MCP 0.2 Future Recommendations

> Document created: December 2025
> Status: Post-implementation recommendations from MCP 0.2 upgrade

## Overview

This document outlines future improvements identified during the langchain-mcp-adapters 0.2 upgrade. These are not blockers but would enhance production readiness.

---

## 1. Race Condition Mitigation

### Current State
```python
# client.py:get_tools()
async with self._lock:
    if self._client is None:
        await self._ensure_client()
    # Lock released here, but tools loaded outside lock
tools = await self._load_tools(conn)  # Race condition window
```

### Problem
Multiple concurrent calls to `get_tools()` for the same server could:
- Load tools multiple times
- Result in inconsistent connection states
- Cause unnecessary MCP server calls

### Recommended Fix
```python
async def get_tools(self, server_name: str) -> Sequence[BaseTool]:
    """Thread-safe tool loading with per-connection locking."""
    async with self._lock:
        conn = self._get_or_create_connection(server_name)

        # Use per-connection lock for finer granularity
        async with conn.lock:
            if conn.state == ConnectionState.CONNECTED and conn.tools:
                return conn.tools

            # Load tools while holding connection lock
            await self._load_tools(conn)
            return conn.tools
```

### Implementation Effort
- **Complexity**: Low
- **Files**: `client.py`
- **Tests**: Add concurrent access tests
- **Priority**: Medium (affects high-load scenarios)

---

## 2. Callback Test Coverage

### Current State
- `callbacks.py` has 515 lines of code
- `test_interceptors.py` exists with 738 lines
- **Missing**: `test_callbacks.py`

### Recommended Coverage
```
tests/unit/shared/services/mcp/
├── test_callbacks.py        # NEW - Target 80%+ coverage
├── test_client.py           # ✅ Exists
├── test_config.py           # ✅ Exists
└── test_interceptors.py     # ✅ Exists
```

### Test Scenarios to Add
1. **MCPCallbacks initialization**
   - With/without broadcaster
   - With/without Langfuse trace_id

2. **on_progress callback**
   - Progress percentages (0%, 50%, 100%)
   - Error scenarios
   - SSE publishing verification

3. **on_logging_message callback**
   - Log levels (debug, info, warning, error)
   - Langfuse event logging
   - Data sanitization

4. **Integration with MCPClientPool**
   - Callbacks passed to MultiServerMCPClient
   - Callbacks triggered during tool execution

### Implementation Effort
- **Complexity**: Medium
- **Lines**: ~400-500 lines
- **Priority**: High (production observability)

---

## 3. Log Sanitization for Sensitive Data

### Current State
```python
# interceptors.py:LoggingInterceptor
"args": str(request.args)[:500],  # May contain sensitive data
```

### Problem
Sensitive data (API keys, tokens, passwords) could be logged to Langfuse.

### Recommended Fix
```python
SENSITIVE_KEYS = frozenset({
    "api_key", "token", "password", "secret", "auth",
    "authorization", "bearer", "credential", "private_key",
})

def sanitize_args(args: dict) -> dict:
    """Redact sensitive values from arguments."""
    if not isinstance(args, dict):
        return args

    result = {}
    for key, value in args.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = sanitize_args(value)
        else:
            result[key] = value
    return result
```

### Implementation Effort
- **Complexity**: Low
- **Files**: `interceptors.py`, add tests
- **Priority**: High (security best practice)

---

## 4. Security Scanning (pip-audit)

### Current State
No automated dependency vulnerability scanning in CI.

### Recommendation
Add pip-audit to CI pipeline:

```yaml
# .github/workflows/ci.yml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Install pip-audit
      run: pip install pip-audit
    - name: Run security scan
      run: pip-audit --strict
```

### Benefits
- Catches known CVEs in dependencies
- Runs on every PR
- Blocks merge if critical vulnerabilities found

### Implementation Effort
- **Complexity**: Low
- **Files**: `.github/workflows/ci.yml`
- **Priority**: Medium (security hygiene)

---

## 5. Connection Health Monitoring

### Current State
```python
def is_healthy(self) -> bool:
    """Check if connection is healthy."""
    return (
        self.state == ConnectionState.CONNECTED
        and self.error_count < MAX_CONSECUTIVE_ERRORS
    )
```

### Enhancement: Add heartbeat/ping mechanism
```python
async def check_health(self) -> bool:
    """Active health check with ping."""
    if not self.is_healthy():
        return False

    try:
        # Ping the MCP server
        await asyncio.wait_for(
            self._ping_server(),
            timeout=5.0
        )
        self.last_health_check = time.monotonic()
        return True
    except Exception:
        self.record_error("Health check failed")
        return False
```

### Benefits
- Proactive connection validation
- Faster failure detection
- Better observability

### Implementation Effort
- **Complexity**: Medium
- **Files**: `client.py`
- **Priority**: Low (nice-to-have)

---

## 6. Metrics & Observability Enhancements

### Current Langfuse Integration
- ✅ Trace correlation
- ✅ Tool call logging
- ✅ Error tracking

### Missing Metrics
1. **Tool call latency histogram**
2. **Connection pool utilization**
3. **Cache hit/miss rates**
4. **Error rates by server**

### Recommended: Add Prometheus metrics
```python
from prometheus_client import Histogram, Counter, Gauge

MCP_TOOL_LATENCY = Histogram(
    'mcp_tool_call_duration_seconds',
    'MCP tool call latency',
    ['server', 'tool']
)

MCP_ERRORS = Counter(
    'mcp_tool_errors_total',
    'MCP tool call errors',
    ['server', 'error_type']
)

MCP_CONNECTIONS = Gauge(
    'mcp_connections_active',
    'Active MCP connections',
    ['server', 'state']
)
```

### Implementation Effort
- **Complexity**: Medium
- **Dependencies**: `prometheus-client`
- **Priority**: Medium (production observability)

---

## Priority Matrix

| Recommendation | Impact | Effort | Priority |
|----------------|--------|--------|----------|
| Log Sanitization | High | Low | P1 |
| Callback Tests | Medium | Medium | P1 |
| Race Condition Fix | Medium | Low | P2 |
| pip-audit CI | Medium | Low | P2 |
| Health Monitoring | Low | Medium | P3 |
| Prometheus Metrics | Medium | Medium | P3 |

---

## Implementation Timeline

### Sprint N+1 (P1 items)
- [ ] Add log sanitization to interceptors
- [ ] Create test_callbacks.py with 80%+ coverage

### Sprint N+2 (P2 items)
- [ ] Fix race condition with per-connection locks
- [ ] Add pip-audit to CI pipeline

### Backlog (P3 items)
- [ ] Implement connection health monitoring
- [ ] Add Prometheus metrics integration

---

## References

- [langchain-mcp-adapters 0.2 Docs](https://github.com/langchain-ai/langchain-mcp-adapters)
- [MCP 0.2 Upgrade Plan](./MCP_0.1_TO_0.2_UPGRADE_PLAN.md)
- [Langfuse Observability Skill](../.claude/skills/langfuse-observability/SKILL.md)
- [OWASP Logging Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

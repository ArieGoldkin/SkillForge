# Issue #243: MCP Bulk Operations Support

**Status:** In Progress
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 2 pts
**GitHub Issue:** [#243](https://github.com/ArieGoldkin/SkillForge/issues/243)
**Blocked By:** #231, #233, #234 (All Complete)

---

## Problem Statement

When an agent needs to check multiple dependencies or vulnerabilities:

```python
# Current: 3 separate tool calls = 3x latency, 3x token overhead
check_dependency("react")      # 1 LLM round-trip
check_dependency("lodash")     # 1 LLM round-trip
check_dependency("express")    # 1 LLM round-trip
```

This is inefficient - wastes tokens on repeated tool schemas and increases latency.

## Solution: Batch APIs

```python
# Efficient: 1 tool call for multiple items
check_dependencies(["react", "lodash", "express"])

# Returns structured results with partial failure handling
{
    "total": 3,
    "successful": [...],
    "failed": [...],
    "errors": [...]  # Each error is actionable
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Batch Operations Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 app/services/mcp/batch.py                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                           │  │
│  │  BatchInput[T]          - Generic input for batch ops     │  │
│  │  BatchResult[T]         - Generic result container        │  │
│  │  SuccessItem[T]         - Individual success entry        │  │
│  │  FailedItem             - Individual failure entry        │  │
│  │  ActionableError        - Error with suggestion           │  │
│  │                                                           │  │
│  │  async def execute_batch() - Core batch execution logic   │  │
│  │  def partition_results()   - Split success/failure        │  │
│  │  def make_actionable()     - Create actionable errors     │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Batch Tool Functions                         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                                                           │  │
│  │  batch_check_dependencies(packages: list[str])            │  │
│  │    - Uses MCPClientPool to call npm/pypi tools            │  │
│  │    - Returns BatchResult[PackageInfo]                     │  │
│  │                                                           │  │
│  │  batch_check_vulnerabilities(cve_ids: list[str])          │  │
│  │    - Uses MCPClientPool to call github security tools     │  │
│  │    - Returns BatchResult[VulnerabilityInfo]               │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              MCPClientPool (existing)                     │  │
│  │              - get_tools()                                │  │
│  │              - get_tools_for_capabilities()               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Task 1: Create Batch Models and Utilities

**File:** `backend/app/services/mcp/batch.py`

```python
from dataclasses import dataclass, field
from typing import TypeVar, Generic

T = TypeVar("T")

MAX_BATCH_SIZE = 50

@dataclass
class SuccessItem(Generic[T]):
    """Individual successful result."""
    item: str  # Original input identifier
    result: T  # Result data

@dataclass
class FailedItem:
    """Individual failed result."""
    item: str  # Original input identifier
    error: str  # Error message

@dataclass
class ActionableError:
    """Error with actionable suggestion."""
    item: str           # Original input that failed
    reason: str         # What went wrong
    suggestion: str     # How to fix it

@dataclass
class BatchResult(Generic[T]):
    """Result container for batch operations."""
    total: int
    successful: list[SuccessItem[T]] = field(default_factory=list)
    failed: list[FailedItem] = field(default_factory=list)
    errors: list[ActionableError] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)
```

### Task 2: Core Batch Execution Logic

```python
async def execute_batch[T](
    items: list[str],
    operation: Callable[[str], Awaitable[T]],
    max_concurrent: int = 10,
) -> BatchResult[T]:
    """Execute operation on multiple items with controlled concurrency.

    Uses asyncio.Semaphore for rate limiting and asyncio.gather
    for parallel execution with return_exceptions=True.
    """
    if len(items) > MAX_BATCH_SIZE:
        msg = f"Batch size {len(items)} exceeds max {MAX_BATCH_SIZE}"
        raise ValueError(msg)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_operation(item: str) -> tuple[str, T | Exception]:
        async with semaphore:
            try:
                result = await operation(item)
                return (item, result)
            except Exception as e:
                return (item, e)

    results = await asyncio.gather(
        *[bounded_operation(item) for item in items]
    )

    return partition_results(results)
```

### Task 3: Batch Dependency Checking

```python
@dataclass
class PackageInfo:
    """Package metadata result."""
    name: str
    version: str
    vulnerabilities: int
    ecosystem: str  # npm or pypi

async def batch_check_dependencies(
    packages: list[str],
    pool: MCPClientPool,
) -> BatchResult[PackageInfo]:
    """Check multiple packages in a single batch operation.

    Determines ecosystem from package name patterns and calls
    appropriate MCP tool (npm:get_package or pypi:get_package).
    """
```

### Task 4: Batch Vulnerability Checking

```python
@dataclass
class VulnerabilityInfo:
    """Vulnerability metadata result."""
    cve_id: str
    severity: str
    summary: str
    affected_packages: list[str]

async def batch_check_vulnerabilities(
    cve_ids: list[str],
    pool: MCPClientPool,
) -> BatchResult[VulnerabilityInfo]:
    """Check multiple CVEs in a single batch operation.

    Uses github:get_security_advisories MCP tool.
    """
```

### Task 5: Unit Tests

**File:** `backend/tests/unit/services/mcp/test_batch.py`

Test scenarios:
- All items succeed
- All items fail
- Partial success/failure
- Max batch size enforcement
- Rate limiting with semaphore
- Actionable error generation

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/mcp/batch.py` | Create | Batch models and execution logic |
| `backend/app/services/mcp/__init__.py` | Modify | Export batch utilities |
| `backend/tests/unit/services/mcp/test_batch.py` | Create | Unit tests |
| `docs/issues/243-mcp-bulk-operations/PLAN.md` | Create | This plan |
| `docs/issues/243-mcp-bulk-operations/README.md` | Create | Documentation |

---

## Acceptance Criteria

- [x] BatchResult generic model with successful/failed/errors
- [x] execute_batch with rate limiting (semaphore)
- [x] batch_check_dependencies accepts array of package names
- [x] batch_check_vulnerabilities accepts array of CVE IDs
- [x] All batch tools return { successful, failed, errors } structure
- [x] Partial failures don't block successful results
- [x] Each error in errors array is actionable (includes suggestion)
- [x] Maximum batch size enforced (50 items)
- [x] Unit tests for all scenarios
- [x] CI checks pass (ruff format, ruff check, mypy)

---

## Implementation Notes

1. **No MCP Server Creation Required**: This issue creates helper utilities that
   wrap existing MCP tool calls with batch semantics, not new MCP server endpoints.

2. **Rate Limiting**: Use `asyncio.Semaphore(10)` for controlled concurrency to
   avoid overwhelming MCP servers.

3. **Graceful Degradation**: Partial failures should not prevent successful results
   from being returned. Use `return_exceptions=True` with `asyncio.gather`.

4. **Actionable Errors**: Each error should include a suggestion for how to fix it:
   - "Package not found" → "Did you mean 'express-js'? Try: check_dependencies(['express-js'])"
   - "Rate limited" → "Reduce batch size or wait before retrying"

---

**Last Updated:** December 10, 2025

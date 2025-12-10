# Issue #243: MCP Bulk Operations Support

**Status:** Complete
**Assignee:** Yonatan
**Sprint:** Sprint 9 - MCP Integration
**Story Points:** 2 pts
**GitHub Issue:** [#243](https://github.com/ArieGoldkin/SkillForge/issues/243)
**Blocked By:** #231, #233, #234 (All Complete)

---

## Issue Overview

**Title:** [Backend][MCP] Bulk Operations Support [2 pts]

**Description:**
Implement bulk/batch operation patterns for MCP tools to reduce token usage, latency, and cost when agents need to perform multiple similar operations.

**Labels:** `backend`, `mcp`, `sprint-9`

---

## Implementation Summary

### Tasks Completed

- [x] Created implementation plan (`PLAN.md`)
- [x] Batch models with PEP 695 type parameters
- [x] `execute_batch()` core function with rate limiting
- [x] `batch_check_dependencies()` for package lookups
- [x] `batch_check_vulnerabilities()` for CVE lookups
- [x] Actionable error generation with suggestions
- [x] Unit tests (32 tests)
- [x] CI checks pass (ruff format, ruff check)

### Files Created/Modified

```
backend/app/services/mcp/
├── batch.py           # New: Batch operation utilities
└── __init__.py        # Modified: Export batch utilities

backend/tests/unit/services/mcp/
└── test_batch.py      # New: 32 unit tests

docs/issues/243-mcp-bulk-operations/
├── PLAN.md            # Implementation plan
└── README.md          # This file
```

---

## Technical Details

### Problem Solved

When an agent needs to check multiple dependencies:

```python
# Before: 3 separate tool calls = 3x latency, 3x token overhead
check_dependency("react")      # 1 LLM round-trip
check_dependency("lodash")     # 1 LLM round-trip
check_dependency("express")    # 1 LLM round-trip
```

### Solution: Batch APIs

```python
# After: 1 tool call for multiple items
result = await batch_check_dependencies(
    ["react", "lodash", "express"],
    pool=mcp_pool,
)

# Returns structured results with partial failure handling
print(result.total)          # 3
print(result.success_count)  # 2
print(result.failure_count)  # 1
print(result.errors[0].suggestion)  # "Package 'express' not found..."
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Batch Operations Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: ["react", "lodash", "nonexistent"]                      │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              execute_batch[T]()                           │  │
│  │  - Validates batch size (max 50)                         │  │
│  │  - Deduplicates items                                    │  │
│  │  - Rate limits with asyncio.Semaphore                    │  │
│  │  - Uses asyncio.gather for parallel execution            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              partition_results[T]()                       │  │
│  │  - Separates successes from failures                     │  │
│  │  - Creates ActionableError for each failure              │  │
│  │  - Returns BatchResult[T]                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  Output: BatchResult[PackageInfo]                               │
│    - successful: [SuccessItem, ...]                             │
│    - failed: [FailedItem, ...]                                  │
│    - errors: [ActionableError, ...]                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. BatchResult[T] - Generic Result Container

```python
@dataclass
class BatchResult[T]:
    total: int
    successful: list[SuccessItem[T]]
    failed: list[FailedItem]
    errors: list[ActionableError]

    @property
    def all_succeeded(self) -> bool: ...

    @property
    def all_failed(self) -> bool: ...
```

#### 2. ActionableError - Errors with Suggestions

```python
@dataclass
class ActionableError:
    item: str           # Original input
    reason: str         # What went wrong
    suggestion: str     # How to fix it

# Example suggestions:
# - "Package 'foo' not found. Check spelling..."
# - "Rate limited. Reduce batch size..."
# - "Network error. Check connectivity..."
```

#### 3. execute_batch[T] - Core Execution Engine

```python
async def execute_batch[T](
    items: list[str],
    operation: Callable[[str], Awaitable[T]],
    max_concurrent: int = 10,
) -> BatchResult[T]:
    """
    - Enforces MAX_BATCH_SIZE (50 items)
    - Uses asyncio.Semaphore for rate limiting
    - Handles partial failures gracefully
    """
```

---

## Test Results

```
============================= test session starts ==============================
collected 32 items

tests/unit/services/mcp/test_batch.py::TestBatchResultModel::test_empty_result PASSED
tests/unit/services/mcp/test_batch.py::TestBatchResultModel::test_all_successful PASSED
tests/unit/services/mcp/test_batch.py::TestBatchResultModel::test_all_failed PASSED
tests/unit/services/mcp/test_batch.py::TestBatchResultModel::test_partial_failure PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_not_found_error PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_rate_limit_error PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_timeout_error PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_connection_error PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_permission_error PASSED
tests/unit/services/mcp/test_batch.py::TestActionableErrors::test_generic_error PASSED
tests/unit/services/mcp/test_batch.py::TestPartitionResults::test_all_success PASSED
tests/unit/services/mcp/test_batch.py::TestPartitionResults::test_all_failures PASSED
tests/unit/services/mcp/test_batch.py::TestPartitionResults::test_mixed_results PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_empty_batch PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_all_succeed PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_all_fail PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_partial_failure PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_max_batch_size_enforced PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_exactly_max_batch_size_allowed PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_duplicates_removed PASSED
tests/unit/services/mcp/test_batch.py::TestExecuteBatch::test_concurrent_limit_respected PASSED
tests/unit/services/mcp/test_batch.py::TestDetectEcosystem::test_scoped_npm_package PASSED
tests/unit/services/mcp/test_batch.py::TestDetectEcosystem::test_python_indicators PASSED
tests/unit/services/mcp/test_batch.py::TestDetectEcosystem::test_npm_default PASSED
tests/unit/services/mcp/test_batch.py::TestPackageInfo::test_create_package_info PASSED
tests/unit/services/mcp/test_batch.py::TestVulnerabilityInfo::test_create_vulnerability_info PASSED
tests/unit/services/mcp/test_batch.py::TestVulnerabilityInfo::test_default_empty_affected_packages PASSED
tests/unit/services/mcp/test_batch.py::TestBatchCheckDependencies::test_batch_check_single_package PASSED
tests/unit/services/mcp/test_batch.py::TestBatchCheckDependencies::test_batch_check_multiple_packages PASSED
tests/unit/services/mcp/test_batch.py::TestBatchCheckDependencies::test_batch_check_with_failure PASSED
tests/unit/services/mcp/test_batch.py::TestBatchCheckVulnerabilities::test_batch_check_single_cve PASSED
tests/unit/services/mcp/test_batch.py::TestBatchCheckVulnerabilities::test_batch_check_multiple_cves PASSED

============================== 32 passed in 0.21s ==============================
```

---

## Usage Examples

### Basic Batch Execution

```python
from app.services.mcp import execute_batch, BatchResult

async def check_url(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return {"status": response.status}

result: BatchResult[dict] = await execute_batch(
    items=["https://example.com", "https://google.com"],
    operation=check_url,
    max_concurrent=5,
)

for item in result.successful:
    print(f"{item.item}: {item.result['status']}")
```

### Batch Dependency Checking

```python
from app.services.mcp import batch_check_dependencies, MCPClientPool

pool = MCPClientPool(server_configs)

result = await batch_check_dependencies(
    ["react", "lodash", "nonexistent-pkg"],
    pool=pool,
)

print(f"Checked {result.total} packages")
print(f"Successful: {result.success_count}")
print(f"Failed: {result.failure_count}")

for err in result.errors:
    print(f"  {err.item}: {err.suggestion}")
```

### Batch Vulnerability Checking

```python
from app.services.mcp import batch_check_vulnerabilities, MCPClientPool

pool = MCPClientPool(server_configs)

result = await batch_check_vulnerabilities(
    ["CVE-2024-1234", "CVE-2023-5678"],
    pool=pool,
)

for item in result.successful:
    vuln = item.result
    print(f"{vuln.cve_id}: {vuln.severity} - {vuln.summary}")
```

---

## Acceptance Criteria Checklist

- [x] `batch_check_dependencies` accepts array of package names
- [x] `batch_check_vulnerabilities` accepts array of CVE IDs
- [x] All batch tools return `{ successful, failed, errors }` structure
- [x] Partial failures don't block successful results
- [x] Each error in `errors` array is actionable (includes suggestion)
- [x] Rate limiting handled internally (semaphore with max_concurrent)
- [x] Maximum batch size enforced (50 items)
- [x] Unit tests for all scenarios (32 tests)
- [x] CI checks pass (ruff format, ruff check)

---

## Related Issues

- **#229:** MCP Integration Epic (parent)
- **#231:** Tool Registry & Agent Capability Mapping (dependency)
- **#233:** Security Auditor MCP Integration (dependency)
- **#234:** Dependency Mapper MCP Integration (dependency)

---

## References

- [Building Tools That Actually Work For AI Agents and MCP Servers](https://medium.com/elementor-engineers/building-tools-that-actually-work-for-ai-agents-and-mcp-servers-a2ba05b2440b) - Elementor Engineers

---

**Last Updated:** December 10, 2025

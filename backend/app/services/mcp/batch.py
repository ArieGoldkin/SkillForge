"""Batch operations for MCP tool calls.

Provides utilities for executing multiple similar MCP operations in a single
batch call, reducing token usage, latency, and cost.

Features:
- Generic BatchResult container with successful/failed/errors
- Rate-limited concurrent execution with asyncio.Semaphore
- Partial failure handling (success doesn't block on individual failures)
- Actionable error messages with suggestions

Architecture:
    BatchInput → execute_batch() → BatchResult
                      ↓
              asyncio.gather (with return_exceptions=True)
                      ↓
              partition_results() → BatchResult

Example:
    >>> result = await batch_check_dependencies(
    ...     ["react", "lodash", "nonexistent-pkg"],
    ...     pool=mcp_pool,
    ... )
    >>> print(result.success_count)  # 2
    >>> print(result.errors[0].suggestion)  # "Did you mean..."

Source: https://medium.com/elementor-engineers/building-tools-that-actually-work-for-ai-agents-and-mcp-servers

"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

    from app.services.mcp.client import MCPClientPool

logger = get_logger(__name__)

# Maximum items allowed in a single batch operation
MAX_BATCH_SIZE = 50

# Default concurrent operations for rate limiting
DEFAULT_MAX_CONCURRENT = 10


@dataclass
class SuccessItem[T]:
    """Individual successful result from batch operation.

    Attributes:
        item: Original input identifier (e.g., package name, CVE ID)
        result: Result data of type T

    """

    item: str
    result: T


@dataclass
class FailedItem:
    """Individual failed result from batch operation.

    Attributes:
        item: Original input identifier that failed
        error: Error message describing what went wrong

    """

    item: str
    error: str


@dataclass
class ActionableError:
    """Error with actionable suggestion for recovery.

    Each error provides guidance on how to fix the issue,
    making it easy for agents to self-correct.

    Attributes:
        item: Original input that caused the error
        reason: What went wrong
        suggestion: How to fix it (must be actionable)

    """

    item: str
    reason: str
    suggestion: str


@dataclass
class BatchResult[T]:
    """Container for batch operation results.

    Follows the pattern from the Elementor blog post for MCP tools:
    - Total count of items processed
    - Successful results with full data
    - Failed items with error messages
    - Actionable errors with suggestions

    Attributes:
        total: Total number of items in the batch
        successful: List of successful results
        failed: List of failed items
        errors: List of actionable errors with suggestions

    Example:
        >>> result = BatchResult(
        ...     total=3,
        ...     successful=[SuccessItem("react", PackageInfo(...))],
        ...     failed=[FailedItem("bad-pkg", "Not found")],
        ...     errors=[ActionableError("bad-pkg", "Not found", "Try 'react'")],
        ... )

    """

    total: int
    successful: list[SuccessItem[T]] = field(default_factory=list)
    failed: list[FailedItem] = field(default_factory=list)
    errors: list[ActionableError] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Number of successful results."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed results."""
        return len(self.failed)

    @property
    def all_succeeded(self) -> bool:
        """Whether all items succeeded."""
        return self.failure_count == 0 and self.success_count == self.total

    @property
    def all_failed(self) -> bool:
        """Whether all items failed."""
        return self.success_count == 0 and self.failure_count == self.total


def make_actionable_error(item: str, exception: Exception) -> ActionableError:
    """Convert an exception into an actionable error with suggestion.

    Analyzes the exception type and message to provide helpful
    suggestions for recovery.

    Args:
        item: The input that caused the error
        exception: The exception that was raised

    Returns:
        ActionableError with reason and suggestion

    """
    error_str = str(exception).lower()
    reason = str(exception)

    # Determine suggestion based on error type/message
    if "not found" in error_str or "404" in error_str:
        suggestion = (
            f"Package '{item}' not found. Check spelling or try searching for similar packages."
        )
    elif "rate limit" in error_str or "429" in error_str:
        suggestion = "Rate limited by upstream service. Reduce batch size or wait before retrying."
    elif "timeout" in error_str:
        suggestion = (
            f"Operation timed out for '{item}'. The service may be slow. "
            "Try again or reduce batch size."
        )
    elif "connection" in error_str or "network" in error_str:
        suggestion = (
            "Network error occurred. Check connectivity and retry. "
            "If persistent, the MCP server may be down."
        )
    elif "permission" in error_str or "401" in error_str or "403" in error_str:
        suggestion = (
            "Permission denied. Check that API credentials are configured "
            "correctly for this MCP server."
        )
    else:
        suggestion = (
            f"Unexpected error for '{item}'. Check the error message and "
            "retry. If persistent, report this issue."
        )

    return ActionableError(item=item, reason=reason, suggestion=suggestion)


def partition_results[T](
    results: list[tuple[str, T | Exception]],
) -> BatchResult[T]:
    """Partition batch results into successful and failed.

    Takes raw results from asyncio.gather (with return_exceptions=True)
    and separates them into successful results, failed items, and
    actionable errors.

    Args:
        results: List of (item, result_or_exception) tuples

    Returns:
        BatchResult with partitioned results

    """
    successful: list[SuccessItem[T]] = []
    failed: list[FailedItem] = []
    errors: list[ActionableError] = []

    for item, result in results:
        if isinstance(result, Exception):
            failed.append(FailedItem(item=item, error=str(result)))
            errors.append(make_actionable_error(item, result))
        else:
            successful.append(SuccessItem(item=item, result=result))

    return BatchResult(
        total=len(results),
        successful=successful,
        failed=failed,
        errors=errors,
    )


async def execute_batch[T](
    items: list[str],
    operation: Callable[[str], Awaitable[T]],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> BatchResult[T]:
    """Execute an operation on multiple items with controlled concurrency.

    Uses asyncio.Semaphore for rate limiting and asyncio.gather with
    return_exceptions=True to handle partial failures gracefully.

    Args:
        items: List of items to process
        operation: Async function to apply to each item
        max_concurrent: Maximum concurrent operations (default: 10)

    Returns:
        BatchResult containing successful and failed results

    Raises:
        ValueError: If batch size exceeds MAX_BATCH_SIZE

    Example:
        >>> async def check_package(name: str) -> PackageInfo:
        ...     async with pool.get_tools("npm") as tools:
        ...         return await tools[0].ainvoke({"package": name})
        >>> result = await execute_batch(
        ...     ["react", "lodash", "express"],
        ...     check_package,
        ...     max_concurrent=5,
        ... )

    """
    if not items:
        return BatchResult(total=0)

    if len(items) > MAX_BATCH_SIZE:
        msg = f"Batch size {len(items)} exceeds maximum of {MAX_BATCH_SIZE}"
        raise ValueError(msg)

    # Remove duplicates while preserving order
    unique_items = list(dict.fromkeys(items))

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_operation(item: str) -> tuple[str, T | Exception]:
        """Execute operation with semaphore for rate limiting."""
        async with semaphore:
            try:
                result = await operation(item)
                return (item, result)
            except Exception as e:  # noqa: BLE001 - Intentionally catch all for partial failure
                logger.warning(
                    "batch_item_failed",
                    item=item,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return (item, e)

    logger.info(
        "batch_operation_started",
        total_items=len(unique_items),
        max_concurrent=max_concurrent,
    )

    results = await asyncio.gather(
        *[bounded_operation(item) for item in unique_items],
        return_exceptions=False,  # We handle exceptions in bounded_operation
    )

    batch_result = partition_results(results)

    logger.info(
        "batch_operation_completed",
        total=batch_result.total,
        successful=batch_result.success_count,
        failed=batch_result.failure_count,
    )

    return batch_result


# ============================================================================
# Package/Dependency Data Models
# ============================================================================


@dataclass
class PackageInfo:
    """Package metadata from npm or PyPI.

    Attributes:
        name: Package name
        version: Latest version
        vulnerabilities: Number of known vulnerabilities
        ecosystem: Source ecosystem (npm or pypi)

    """

    name: str
    version: str
    vulnerabilities: int
    ecosystem: str  # "npm" or "pypi"


@dataclass
class VulnerabilityInfo:
    """Security vulnerability information.

    Attributes:
        cve_id: CVE identifier (e.g., CVE-2024-1234)
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        summary: Brief description of the vulnerability
        affected_packages: List of affected package names

    """

    cve_id: str
    severity: str
    summary: str
    affected_packages: list[str] = field(default_factory=list)


# ============================================================================
# Batch Tool Functions
# ============================================================================


def _detect_ecosystem(package_name: str) -> str:
    """Detect package ecosystem from naming conventions.

    Args:
        package_name: Package name to analyze

    Returns:
        "npm" or "pypi" based on heuristics

    """
    # PyPI-style packages often have underscores or hyphen-cased-names
    # npm packages often have @scope/name format or lowercase with hyphens

    if package_name.startswith("@"):
        return "npm"  # Scoped npm package

    # Common Python package patterns
    python_indicators = ["_", "python", "py", "django", "flask", "fastapi"]
    if any(ind in package_name.lower() for ind in python_indicators):
        return "pypi"

    # Default to npm for typical web packages
    return "npm"


async def _check_single_package(
    package_name: str,
    pool: MCPClientPool,
    tools_cache: dict[str, list[BaseTool]],
) -> PackageInfo:
    """Check a single package using appropriate MCP tool.

    Args:
        package_name: Name of the package to check
        pool: MCP client pool for tool access
        tools_cache: Cache of loaded tools to avoid repeated loads

    Returns:
        PackageInfo with package metadata

    Raises:
        MCPConnectionError: If MCP server unavailable
        ValueError: If tool not found or package lookup fails

    """
    ecosystem = _detect_ecosystem(package_name)
    server_name = ecosystem  # npm or pypi server

    # Get tools from cache or load
    if server_name not in tools_cache:
        async with pool.get_tools(server_name) as tools:
            tools_cache[server_name] = list(tools)

    tools = tools_cache[server_name]

    # Find get_package tool
    get_package_tool = next(
        (t for t in tools if "get_package" in t.name.lower()),
        None,
    )

    if not get_package_tool:
        msg = f"get_package tool not found for {ecosystem}"
        raise ValueError(msg)

    # Call the tool
    result = await get_package_tool.ainvoke({"package": package_name})

    # Parse result (format depends on MCP server)
    if isinstance(result, dict):
        return PackageInfo(
            name=result.get("name", package_name),
            version=result.get("version", "unknown"),
            vulnerabilities=result.get("vulnerabilities", 0),
            ecosystem=ecosystem,
        )

    # Fallback for string results
    return PackageInfo(
        name=package_name,
        version="unknown",
        vulnerabilities=0,
        ecosystem=ecosystem,
    )


async def batch_check_dependencies(
    packages: list[str],
    pool: MCPClientPool,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> BatchResult[PackageInfo]:
    """Check multiple packages in a single batch operation.

    More efficient than individual check_dependency calls - reduces
    token overhead and latency by batching requests.

    Args:
        packages: List of package names to check (max 50)
        pool: MCP client pool for tool access
        max_concurrent: Maximum concurrent checks (default: 10)

    Returns:
        BatchResult containing PackageInfo for each package

    Example:
        >>> result = await batch_check_dependencies(
        ...     ["react", "lodash", "nonexistent"],
        ...     pool=mcp_pool,
        ... )
        >>> for item in result.successful:
        ...     print(f"{item.result.name}: {item.result.version}")

    """
    # Cache tools to avoid repeated loading
    tools_cache: dict[str, list[BaseTool]] = {}

    async def check_package(name: str) -> PackageInfo:
        return await _check_single_package(name, pool, tools_cache)

    return await execute_batch(
        items=packages,
        operation=check_package,
        max_concurrent=max_concurrent,
    )


async def _check_single_vulnerability(
    cve_id: str,
    pool: MCPClientPool,
    tools_cache: dict[str, list[BaseTool]],
) -> VulnerabilityInfo:
    """Check a single CVE using GitHub security advisory tool.

    Args:
        cve_id: CVE identifier (e.g., CVE-2024-1234)
        pool: MCP client pool for tool access
        tools_cache: Cache of loaded tools

    Returns:
        VulnerabilityInfo with CVE details

    """
    server_name = "github"

    # Get tools from cache or load
    if server_name not in tools_cache:
        async with pool.get_tools(server_name) as tools:
            tools_cache[server_name] = list(tools)

    tools = tools_cache[server_name]

    # Find security advisory tool
    advisory_tool = next(
        (t for t in tools if "security" in t.name.lower() or "advisory" in t.name.lower()),
        None,
    )

    if not advisory_tool:
        msg = "Security advisory tool not found for github"
        raise ValueError(msg)

    # Call the tool
    result = await advisory_tool.ainvoke({"cve_id": cve_id})

    # Parse result
    if isinstance(result, dict):
        return VulnerabilityInfo(
            cve_id=cve_id,
            severity=result.get("severity", "UNKNOWN"),
            summary=result.get("summary", "No description available"),
            affected_packages=result.get("affected_packages", []),
        )

    return VulnerabilityInfo(
        cve_id=cve_id,
        severity="UNKNOWN",
        summary=str(result) if result else "No information available",
        affected_packages=[],
    )


async def batch_check_vulnerabilities(
    cve_ids: list[str],
    pool: MCPClientPool,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
) -> BatchResult[VulnerabilityInfo]:
    """Check multiple CVEs in a single batch operation.

    More efficient than individual vulnerability checks - batches
    requests to GitHub security advisory API.

    Args:
        cve_ids: List of CVE identifiers to check (max 50)
        pool: MCP client pool for tool access
        max_concurrent: Maximum concurrent checks (default: 10)

    Returns:
        BatchResult containing VulnerabilityInfo for each CVE

    Example:
        >>> result = await batch_check_vulnerabilities(
        ...     ["CVE-2024-1234", "CVE-2023-5678"],
        ...     pool=mcp_pool,
        ... )
        >>> for item in result.successful:
        ...     print(f"{item.result.cve_id}: {item.result.severity}")

    """
    tools_cache: dict[str, list[BaseTool]] = {}

    async def check_cve(cve_id: str) -> VulnerabilityInfo:
        return await _check_single_vulnerability(cve_id, pool, tools_cache)

    return await execute_batch(
        items=cve_ids,
        operation=check_cve,
        max_concurrent=max_concurrent,
    )

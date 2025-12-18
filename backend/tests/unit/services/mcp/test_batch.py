"""Unit tests for MCP batch operations.

Tests cover:
- BatchResult model and properties
- execute_batch with various scenarios
- Partial failure handling
- Rate limiting with semaphore
- Actionable error generation
- batch_check_dependencies and batch_check_vulnerabilities
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.services.mcp.batch import (
    MAX_BATCH_SIZE,
    ActionableError,
    BatchResult,
    FailedItem,
    PackageInfo,
    SuccessItem,
    VulnerabilityInfo,
    _detect_ecosystem,
    batch_check_dependencies,
    batch_check_vulnerabilities,
    execute_batch,
    make_actionable_error,
    partition_results,
)

# ============================================================================
# TestBatchResultModel
# ============================================================================


class TestBatchResultModel:
    """Test BatchResult dataclass and properties."""

    def test_empty_result(self):
        """Empty result has correct counts."""
        result: BatchResult[str] = BatchResult(total=0)

        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.all_succeeded is True  # Vacuously true
        assert result.all_failed is True  # Vacuously true

    def test_all_successful(self):
        """All items succeeded."""
        result: BatchResult[str] = BatchResult(
            total=3,
            successful=[
                SuccessItem(item="a", result="A"),
                SuccessItem(item="b", result="B"),
                SuccessItem(item="c", result="C"),
            ],
            failed=[],
            errors=[],
        )

        assert result.total == 3
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.all_succeeded is True
        assert result.all_failed is False

    def test_all_failed(self):
        """All items failed."""
        result: BatchResult[str] = BatchResult(
            total=2,
            successful=[],
            failed=[
                FailedItem(item="x", error="Error X"),
                FailedItem(item="y", error="Error Y"),
            ],
            errors=[
                ActionableError(item="x", reason="Error X", suggestion="Try again"),
                ActionableError(item="y", reason="Error Y", suggestion="Try again"),
            ],
        )

        assert result.total == 2
        assert result.success_count == 0
        assert result.failure_count == 2
        assert result.all_succeeded is False
        assert result.all_failed is True

    def test_partial_failure(self):
        """Some items succeeded, some failed."""
        result: BatchResult[str] = BatchResult(
            total=3,
            successful=[
                SuccessItem(item="a", result="A"),
                SuccessItem(item="b", result="B"),
            ],
            failed=[
                FailedItem(item="c", error="Error C"),
            ],
            errors=[
                ActionableError(item="c", reason="Error C", suggestion="Fix it"),
            ],
        )

        assert result.total == 3
        assert result.success_count == 2
        assert result.failure_count == 1
        assert result.all_succeeded is False
        assert result.all_failed is False


# ============================================================================
# TestActionableErrors
# ============================================================================


class TestActionableErrors:
    """Test actionable error generation."""

    def test_not_found_error(self):
        """Not found error suggests checking spelling."""
        exc = ValueError("Package 'nonexistent' not found")
        error = make_actionable_error("nonexistent", exc)

        assert error.item == "nonexistent"
        assert "not found" in error.reason.lower()
        assert "spelling" in error.suggestion.lower()

    def test_rate_limit_error(self):
        """Rate limit error suggests reducing batch size."""
        exc = Exception("Rate limit exceeded (429)")
        error = make_actionable_error("react", exc)

        assert error.item == "react"
        assert "batch size" in error.suggestion.lower()

    def test_timeout_error(self):
        """Timeout error suggests retrying."""
        exc = TimeoutError("Operation timeout after 30s")
        error = make_actionable_error("lodash", exc)

        assert error.item == "lodash"
        assert "retry" in error.suggestion.lower() or "batch size" in error.suggestion.lower()

    def test_connection_error(self):
        """Connection error suggests checking connectivity."""
        exc = ConnectionError("Network unreachable")
        error = make_actionable_error("express", exc)

        assert error.item == "express"
        assert "connectivity" in error.suggestion.lower() or "network" in error.suggestion.lower()

    def test_permission_error(self):
        """Permission error suggests checking credentials."""
        exc = PermissionError("401 Unauthorized")
        error = make_actionable_error("private-pkg", exc)

        assert error.item == "private-pkg"
        assert "credential" in error.suggestion.lower() or "permission" in error.suggestion.lower()

    def test_generic_error(self):
        """Unknown error type gives generic suggestion."""
        exc = Exception("Something unexpected")
        error = make_actionable_error("unknown", exc)

        assert error.item == "unknown"
        assert "retry" in error.suggestion.lower()


# ============================================================================
# TestPartitionResults
# ============================================================================


class TestPartitionResults:
    """Test partition_results function."""

    def test_all_success(self):
        """All results are successful."""
        results: list[tuple[str, str | Exception]] = [
            ("a", "Result A"),
            ("b", "Result B"),
        ]

        batch = partition_results(results)

        assert batch.total == 2
        assert batch.success_count == 2
        assert batch.failure_count == 0
        assert batch.successful[0].item == "a"
        assert batch.successful[0].result == "Result A"

    def test_all_failures(self):
        """All results are failures."""
        results: list[tuple[str, str | Exception]] = [
            ("x", ValueError("Error X")),
            ("y", RuntimeError("Error Y")),
        ]

        batch = partition_results(results)

        assert batch.total == 2
        assert batch.success_count == 0
        assert batch.failure_count == 2
        assert len(batch.errors) == 2

    def test_mixed_results(self):
        """Mix of successes and failures."""
        results: list[tuple[str, str | Exception]] = [
            ("a", "Result A"),
            ("b", ValueError("Not found")),
            ("c", "Result C"),
        ]

        batch = partition_results(results)

        assert batch.total == 3
        assert batch.success_count == 2
        assert batch.failure_count == 1


# ============================================================================
# TestExecuteBatch
# ============================================================================


class TestExecuteBatch:
    """Test execute_batch function."""

    @pytest.mark.asyncio
    async def test_empty_batch(self):
        """Empty batch returns empty result."""

        async def operation(item: str) -> str:
            return item.upper()

        result = await execute_batch([], operation)

        assert result.total == 0
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_all_succeed(self):
        """All items succeed."""

        async def operation(item: str) -> str:
            return item.upper()

        result = await execute_batch(["a", "b", "c"], operation)

        assert result.total == 3
        assert result.success_count == 3
        assert result.all_succeeded is True
        assert [s.result for s in result.successful] == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_all_fail(self):
        """All items fail."""

        async def operation(item: str) -> str:
            msg = f"Failed: {item}"
            raise ValueError(msg)

        result = await execute_batch(["x", "y"], operation)

        assert result.total == 2
        assert result.failure_count == 2
        assert result.all_failed is True

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """Some items fail, others succeed."""

        async def operation(item: str) -> str:
            if item == "bad":
                msg = "Bad item"
                raise ValueError(msg)
            return item.upper()

        result = await execute_batch(["good", "bad", "also_good"], operation)

        assert result.total == 3
        assert result.success_count == 2
        assert result.failure_count == 1
        assert result.failed[0].item == "bad"

    @pytest.mark.asyncio
    async def test_max_batch_size_enforced(self):
        """Batch size over MAX_BATCH_SIZE raises ValueError."""

        async def operation(item: str) -> str:
            return item

        items = [f"item_{i}" for i in range(MAX_BATCH_SIZE + 1)]

        with pytest.raises(ValueError) as exc_info:
            await execute_batch(items, operation)

        assert "exceeds maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exactly_max_batch_size_allowed(self):
        """Batch size exactly at MAX_BATCH_SIZE is allowed."""

        async def operation(item: str) -> str:
            return item

        items = [f"item_{i}" for i in range(MAX_BATCH_SIZE)]

        result = await execute_batch(items, operation)

        assert result.total == MAX_BATCH_SIZE

    @pytest.mark.asyncio
    async def test_duplicates_removed(self):
        """Duplicate items are deduplicated."""

        async def operation(item: str) -> str:
            return item.upper()

        result = await execute_batch(["a", "b", "a", "c", "b"], operation)

        # Only 3 unique items processed
        assert result.total == 3
        assert result.success_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_limit_respected(self):
        """Semaphore limits concurrent operations."""
        import asyncio

        max_concurrent = 2
        concurrent_count = 0
        max_observed = 0

        async def operation(item: str) -> str:
            nonlocal concurrent_count, max_observed
            concurrent_count += 1
            max_observed = max(max_observed, concurrent_count)
            await asyncio.sleep(0.01)  # Simulate work
            concurrent_count -= 1
            return item

        result = await execute_batch(
            ["a", "b", "c", "d", "e"],
            operation,
            max_concurrent=max_concurrent,
        )

        assert result.success_count == 5
        assert max_observed <= max_concurrent


# ============================================================================
# TestDetectEcosystem
# ============================================================================


class TestDetectEcosystem:
    """Test package ecosystem detection."""

    def test_scoped_npm_package(self):
        """Scoped packages are npm."""
        assert _detect_ecosystem("@types/react") == "npm"
        assert _detect_ecosystem("@angular/core") == "npm"

    def test_python_indicators(self):
        """Python-style packages detected as pypi."""
        assert _detect_ecosystem("python-dateutil") == "pypi"
        assert _detect_ecosystem("django_rest_framework") == "pypi"
        assert _detect_ecosystem("flask-cors") == "pypi"
        assert _detect_ecosystem("fastapi") == "pypi"

    def test_npm_default(self):
        """Typical web packages default to npm."""
        assert _detect_ecosystem("react") == "npm"
        assert _detect_ecosystem("lodash") == "npm"
        assert _detect_ecosystem("express") == "npm"


# ============================================================================
# TestPackageInfo
# ============================================================================


class TestPackageInfo:
    """Test PackageInfo dataclass."""

    def test_create_package_info(self):
        """PackageInfo created correctly."""
        pkg = PackageInfo(
            name="react",
            version="18.2.0",
            vulnerabilities=0,
            ecosystem="npm",
        )

        assert pkg.name == "react"
        assert pkg.version == "18.2.0"
        assert pkg.vulnerabilities == 0
        assert pkg.ecosystem == "npm"


# ============================================================================
# TestVulnerabilityInfo
# ============================================================================


class TestVulnerabilityInfo:
    """Test VulnerabilityInfo dataclass."""

    def test_create_vulnerability_info(self):
        """VulnerabilityInfo created correctly."""
        vuln = VulnerabilityInfo(
            cve_id="CVE-2024-1234",
            severity="HIGH",
            summary="XSS vulnerability",
            affected_packages=["lodash", "underscore"],
        )

        assert vuln.cve_id == "CVE-2024-1234"
        assert vuln.severity == "HIGH"
        assert vuln.summary == "XSS vulnerability"
        assert len(vuln.affected_packages) == 2

    def test_default_empty_affected_packages(self):
        """Affected packages defaults to empty list."""
        vuln = VulnerabilityInfo(
            cve_id="CVE-2024-0000",
            severity="LOW",
            summary="Minor issue",
        )

        assert vuln.affected_packages == []


# ============================================================================
# TestBatchCheckDependencies
# ============================================================================


class TestBatchCheckDependencies:
    """Test batch_check_dependencies function."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock MCPClientPool."""
        pool = MagicMock()
        return pool

    @pytest.fixture
    def mock_npm_tool(self):
        """Create mock npm get_package tool."""
        tool = MagicMock()
        tool.name = "get_package"
        tool.ainvoke = AsyncMock(
            return_value={
                "name": "react",
                "version": "18.2.0",
                "vulnerabilities": 0,
            }
        )
        return tool

    @pytest.mark.asyncio
    async def test_batch_check_single_package(self, mock_pool, mock_npm_tool):
        """Check single package returns correct result."""
        # Setup mock context manager
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=[mock_npm_tool])
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_tools = MagicMock(return_value=mock_context)

        result = await batch_check_dependencies(["react"], mock_pool)

        assert result.total == 1
        assert result.success_count == 1
        assert result.successful[0].result.name == "react"
        assert result.successful[0].result.ecosystem == "npm"

    @pytest.mark.asyncio
    async def test_batch_check_multiple_packages(self, mock_pool, mock_npm_tool):
        """Check multiple packages."""
        # Track which package is being checked
        call_count = 0

        async def get_package(args):
            nonlocal call_count
            call_count += 1
            pkg_name = args.get("package", f"pkg_{call_count}")
            return {
                "name": pkg_name,
                "version": "1.0.0",
                "vulnerabilities": call_count - 1,
            }

        mock_npm_tool.ainvoke = AsyncMock(side_effect=get_package)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=[mock_npm_tool])
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_tools = MagicMock(return_value=mock_context)

        result = await batch_check_dependencies(["react", "lodash"], mock_pool)

        assert result.total == 2
        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_batch_check_with_failure(self, mock_pool, mock_npm_tool):
        """Check packages with one failure."""

        async def get_package(args):
            pkg_name = args.get("package", "unknown")
            if pkg_name == "nonexistent":
                msg = "Package not found"
                raise ValueError(msg)
            return {"name": pkg_name, "version": "1.0.0", "vulnerabilities": 0}

        mock_npm_tool.ainvoke = AsyncMock(side_effect=get_package)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=[mock_npm_tool])
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_tools = MagicMock(return_value=mock_context)

        result = await batch_check_dependencies(["react", "nonexistent"], mock_pool)

        assert result.total == 2
        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.failed[0].item == "nonexistent"


# ============================================================================
# TestBatchCheckVulnerabilities
# ============================================================================


class TestBatchCheckVulnerabilities:
    """Test batch_check_vulnerabilities function."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock MCPClientPool."""
        pool = MagicMock()
        return pool

    @pytest.fixture
    def mock_security_tool(self):
        """Create mock GitHub security advisory tool."""
        tool = MagicMock()
        tool.name = "get_security_advisories"
        tool.ainvoke = AsyncMock(
            return_value={
                "cve_id": "CVE-2024-1234",
                "severity": "HIGH",
                "summary": "XSS vulnerability",
                "affected_packages": ["lodash"],
            }
        )
        return tool

    @pytest.mark.asyncio
    async def test_batch_check_single_cve(self, mock_pool, mock_security_tool):
        """Check single CVE returns correct result."""
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=[mock_security_tool])
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_tools = MagicMock(return_value=mock_context)

        result = await batch_check_vulnerabilities(["CVE-2024-1234"], mock_pool)

        assert result.total == 1
        assert result.success_count == 1
        assert result.successful[0].result.cve_id == "CVE-2024-1234"
        assert result.successful[0].result.severity == "HIGH"

    @pytest.mark.asyncio
    async def test_batch_check_multiple_cves(self, mock_pool, mock_security_tool):
        """Check multiple CVEs."""
        call_count = 0

        async def check_cve(args):
            nonlocal call_count
            call_count += 1
            cve_id = args.get("cve_id", f"CVE-2024-{call_count:04d}")
            return {
                "cve_id": cve_id,
                "severity": "HIGH" if call_count == 1 else "MEDIUM",
                "summary": f"Vulnerability {call_count}",
                "affected_packages": [],
            }

        mock_security_tool.ainvoke = AsyncMock(side_effect=check_cve)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=[mock_security_tool])
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.get_tools = MagicMock(return_value=mock_context)

        result = await batch_check_vulnerabilities(
            ["CVE-2024-1111", "CVE-2024-2222"],
            mock_pool,
        )

        assert result.total == 2
        assert result.success_count == 2

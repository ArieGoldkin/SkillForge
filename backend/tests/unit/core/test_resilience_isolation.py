"""Test isolation verification for resilience infrastructure.

Issue #574 (GAP 2): These tests verify that the async-safe reset functions
properly prevent test pollution in parallel test runs.

The resilience infrastructure uses singletons (ResilienceManager, BulkheadRegistry)
with state that can persist between tests:
- Circuit breakers stay OPEN for 60s after failures
- Bulkheads can have acquired semaphores

These tests verify:
1. Reset functions properly clear all state
2. Async locks prevent concurrent reset race conditions
3. Production safety guards prevent accidental production usage
4. Circuit breakers are explicitly reset to CLOSED state
5. Semaphores are properly recreated (not just cleared)
"""

import asyncio
import sys

import pytest

from app.core.bulkhead import (
    BulkheadRegistry,
    Tier,
    get_bulkhead_registry,
    reset_bulkhead_registry,
)
from app.core.circuit_breaker import CircuitBreakerOpenError, CircuitState
from app.core.resilience import (
    ResilienceManager,
    get_resilience_manager,
    reset_resilience_manager,
)


class TestResilienceManagerReset:
    """Verify reset_resilience_manager properly clears state."""

    @pytest.mark.asyncio
    async def test_reset_clears_circuit_breakers(self):
        """Circuit breakers should be cleared after reset."""
        manager = get_resilience_manager()

        # Create some circuit breakers
        cb1 = manager.get_circuit_breaker("test_service_1")
        cb2 = manager.get_circuit_breaker("test_service_2")

        # Verify they exist on the instance (not class - class vars can race with autouse)
        assert cb1 is not None
        assert cb2 is not None
        assert cb1.name == "test_service_1"
        assert cb2.name == "test_service_2"

        # Reset
        await reset_resilience_manager()

        # Verify new manager doesn't have the old circuit breakers
        new_manager = get_resilience_manager()
        # Getting a "new" circuit breaker should create a fresh one
        new_cb = new_manager.get_circuit_breaker("test_service_1")
        assert new_cb is not cb1  # Different instance

    @pytest.mark.asyncio
    async def test_reset_closes_open_circuit_breakers(self):
        """OPEN circuit breakers should be reset to CLOSED before clearing."""
        manager = get_resilience_manager()
        cb = manager.get_circuit_breaker("test_open_cb")

        # Force circuit breaker to OPEN state by triggering failures
        for _ in range(5):  # Exceed failure threshold
            try:

                async def failing_call():
                    raise RuntimeError("Simulated failure")

                await cb.call(failing_call)
            except (RuntimeError, CircuitBreakerOpenError):
                pass

        # Verify it's OPEN
        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True

        # Reset
        await reset_resilience_manager()

        # Get fresh manager - should have no circuit breakers
        new_manager = get_resilience_manager()
        new_cb = new_manager.get_circuit_breaker("test_open_cb")

        # Verify new CB is CLOSED (not polluted by previous OPEN state)
        assert new_cb.state == CircuitState.CLOSED
        assert new_cb.is_open is False

    @pytest.mark.asyncio
    async def test_reset_clears_singleton_instance(self):
        """Singleton instance should be cleared after reset."""
        manager1 = get_resilience_manager()
        instance_id_before = id(manager1)

        await reset_resilience_manager()

        manager2 = get_resilience_manager()
        instance_id_after = id(manager2)

        # Should be different instances
        assert instance_id_before != instance_id_after

    @pytest.mark.asyncio
    async def test_reset_is_idempotent(self):
        """Multiple resets should not cause errors."""
        # First reset
        await reset_resilience_manager()

        # Second reset should also work
        await reset_resilience_manager()

        # Third reset should also work
        await reset_resilience_manager()

        # Should be able to use manager after multiple resets
        manager = get_resilience_manager()
        cb = manager.get_circuit_breaker("test")
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_resets_are_safe(self):
        """Multiple concurrent resets should not cause race conditions."""
        manager = get_resilience_manager()
        for i in range(10):
            manager.get_circuit_breaker(f"cb_{i}")

        # Run multiple resets concurrently
        tasks = [reset_resilience_manager() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should be properly reset
        assert len(ResilienceManager._circuit_breakers) == 0
        assert ResilienceManager._instance is None


class TestBulkheadRegistryReset:
    """Verify reset_bulkhead_registry properly clears state."""

    @pytest.mark.asyncio
    async def test_reset_clears_bulkheads(self):
        """Bulkheads should be cleared after reset."""
        registry = get_bulkhead_registry()

        # Create some bulkheads
        bh_critical = registry.get_or_create("test_critical", Tier.CRITICAL)
        bh_standard = registry.get_or_create("test_standard", Tier.STANDARD)

        # Verify they exist on the instance (not class - class vars can race with autouse)
        assert bh_critical is not None
        assert bh_standard is not None
        assert bh_critical.tier == Tier.CRITICAL
        assert bh_standard.tier == Tier.STANDARD

        # Reset
        await reset_bulkhead_registry()

        # Verify new registry doesn't have the old bulkheads
        new_registry = get_bulkhead_registry()
        new_bh = new_registry.get_or_create("test_critical", Tier.CRITICAL)
        assert new_bh is not bh_critical  # Different instance

    @pytest.mark.asyncio
    async def test_reset_recreates_semaphores(self):
        """Semaphores should be recreated, not just cleared."""
        registry = get_bulkhead_registry()
        bulkhead = registry.get_or_create("test_bulkhead", Tier.STANDARD)

        # Acquire semaphore (simulate in-progress operation)
        acquired = await bulkhead._semaphore.acquire()
        assert acquired is True

        # Original semaphore has one less slot
        original_semaphore_id = id(bulkhead._semaphore)

        # Reset
        await reset_bulkhead_registry()

        # Get fresh bulkhead
        new_registry = get_bulkhead_registry()
        new_bulkhead = new_registry.get_or_create("test_bulkhead", Tier.STANDARD)

        # Should be fresh semaphore with full capacity
        assert id(new_bulkhead._semaphore) != original_semaphore_id

    @pytest.mark.asyncio
    async def test_reset_clears_stats(self):
        """BulkheadStats should be reset to defaults."""
        registry = get_bulkhead_registry()
        bulkhead = registry.get_or_create("stats_test", Tier.STANDARD)

        # Simulate some activity
        bulkhead.stats.total_calls = 100
        bulkhead.stats.successful_calls = 90
        bulkhead.stats.rejected_calls = 10

        # Reset
        await reset_bulkhead_registry()

        # Get fresh bulkhead
        new_registry = get_bulkhead_registry()
        new_bulkhead = new_registry.get_or_create("stats_test", Tier.STANDARD)

        # Stats should be defaults
        assert new_bulkhead.stats.total_calls == 0
        assert new_bulkhead.stats.successful_calls == 0
        assert new_bulkhead.stats.rejected_calls == 0

    @pytest.mark.asyncio
    async def test_reset_clears_singleton_instance(self):
        """Singleton instance should be cleared after reset."""
        registry1 = get_bulkhead_registry()
        instance_id_before = id(registry1)

        await reset_bulkhead_registry()

        registry2 = get_bulkhead_registry()
        instance_id_after = id(registry2)

        # Should be different instances
        assert instance_id_before != instance_id_after

    @pytest.mark.asyncio
    async def test_concurrent_resets_are_safe(self):
        """Multiple concurrent resets should not cause race conditions."""
        registry = get_bulkhead_registry()
        for tier in [Tier.CRITICAL, Tier.STANDARD, Tier.OPTIONAL]:
            registry.get_or_create(f"tier_{tier.name}", tier)

        # Run multiple resets concurrently
        tasks = [reset_bulkhead_registry() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should be properly reset
        assert len(BulkheadRegistry._bulkheads) == 0
        assert BulkheadRegistry._instance is None


class TestProductionSafetyGuards:
    """Verify reset functions cannot be called in production."""

    @pytest.mark.asyncio
    async def test_resilience_reset_only_works_in_pytest(self):
        """reset_resilience_manager should raise if pytest not loaded."""
        # Temporarily remove pytest from sys.modules
        original_pytest = sys.modules.get("pytest")
        try:
            del sys.modules["pytest"]

            with pytest.raises(RuntimeError, match="only be called during tests"):
                await reset_resilience_manager()
        finally:
            # Restore pytest
            if original_pytest:
                sys.modules["pytest"] = original_pytest

    @pytest.mark.asyncio
    async def test_bulkhead_reset_only_works_in_pytest(self):
        """reset_bulkhead_registry should raise if pytest not loaded."""
        # Temporarily remove pytest from sys.modules
        original_pytest = sys.modules.get("pytest")
        try:
            del sys.modules["pytest"]

            with pytest.raises(RuntimeError, match="only be called during tests"):
                await reset_bulkhead_registry()
        finally:
            # Restore pytest
            if original_pytest:
                sys.modules["pytest"] = original_pytest


class TestCrossTestIsolation:
    """Simulate cross-test pollution scenarios."""

    @pytest.mark.asyncio
    async def test_first_test_opens_circuit_breaker(self):
        """First test creates an OPEN circuit breaker."""
        manager = get_resilience_manager()
        cb = manager.get_circuit_breaker("shared_service")

        # Force to OPEN
        for _ in range(5):
            try:

                async def fail():
                    raise RuntimeError("Fail")

                await cb.call(fail)
            except (RuntimeError, CircuitBreakerOpenError):
                pass

        # Verify OPEN
        assert cb.is_open is True

    @pytest.mark.asyncio
    async def test_second_test_gets_fresh_circuit_breaker(self):
        """Second test should get CLOSED circuit breaker (not polluted)."""
        # Due to autouse cleanup fixture, this should be fresh
        manager = get_resilience_manager()
        cb = manager.get_circuit_breaker("shared_service")

        # Should be CLOSED, not OPEN from previous test
        assert cb.is_open is False
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_first_test_acquires_semaphore(self):
        """First test acquires a bulkhead semaphore."""
        registry = get_bulkhead_registry()
        bulkhead = registry.get_or_create("shared_bulkhead", Tier.STANDARD)

        # Acquire semaphore
        await bulkhead._semaphore.acquire()

        # Active count should reflect acquisition
        # (Note: this is internal state, normally tracked via execute())
        bulkhead._active = 1
        bulkhead.stats.current_active = 1

    @pytest.mark.asyncio
    async def test_second_test_gets_fresh_bulkhead(self):
        """Second test should get fresh bulkhead (not polluted)."""
        # Due to autouse cleanup fixture, this should be fresh
        registry = get_bulkhead_registry()
        bulkhead = registry.get_or_create("shared_bulkhead", Tier.STANDARD)

        # Should be clean, not polluted from previous test
        assert bulkhead._active == 0
        assert bulkhead.stats.current_active == 0
        assert bulkhead.stats.total_calls == 0

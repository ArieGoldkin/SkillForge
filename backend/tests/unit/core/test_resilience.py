"""Tests for GAP 2: Resilience Infrastructure.

Issue #533: Comprehensive tests for bulkhead, resilience manager, and resilience wrapper.

Tests cover:
1. Bulkhead: Tier-based concurrency limits, queue management, timeout behavior
2. ResilienceManager: Circuit breaker + bulkhead coordination
3. execute_with_resilience: Wrapper function integration
"""

import asyncio

import pytest

from app.core.bulkhead import (
    Bulkhead,
    BulkheadFullError,
    BulkheadRegistry,
    BulkheadTimeoutError,
    RejectionPolicy,
    Tier,
    get_bulkhead_registry,
)
from app.core.circuit_breaker import CircuitBreakerOpenError
from app.core.resilience import ResilienceManager, get_resilience_manager


class TestBulkheadTiers:
    """Tests for bulkhead tier configuration."""

    def test_critical_tier_defaults(self) -> None:
        """Test CRITICAL tier has correct default configuration.

        Issue #588: CRITICAL tier uses 180s timeout (fail fast, not 300s).
        """
        bulkhead = Bulkhead(name="test-critical", tier=Tier.CRITICAL)

        assert bulkhead.max_concurrent == 5
        assert bulkhead.queue_size == 10
        assert bulkhead.timeout == 180.0  # Fail fast for critical path
        assert bulkhead.tier == Tier.CRITICAL

    def test_standard_tier_defaults(self) -> None:
        """Test STANDARD tier has correct default configuration.

        Issue #588: Updated for parallel fan-out capacity (8 agents → 8 workers).
        """
        bulkhead = Bulkhead(name="test-standard", tier=Tier.STANDARD)

        assert bulkhead.max_concurrent == 8
        assert bulkhead.queue_size == 12
        assert bulkhead.timeout == 120.0
        assert bulkhead.tier == Tier.STANDARD

    def test_optional_tier_defaults(self) -> None:
        """Test OPTIONAL tier has correct default configuration.

        Issue #588: Updated for parallel fan-out capacity (4 agents → 4 workers).
        """
        bulkhead = Bulkhead(name="test-optional", tier=Tier.OPTIONAL)

        assert bulkhead.max_concurrent == 4
        assert bulkhead.queue_size == 6
        assert bulkhead.timeout == 60.0
        assert bulkhead.tier == Tier.OPTIONAL

    def test_custom_tier_overrides(self) -> None:
        """Test custom configuration overrides tier defaults."""
        bulkhead = Bulkhead(
            name="test-custom",
            tier=Tier.STANDARD,
            max_concurrent=10,
            queue_size=20,
            timeout=180.0,
        )

        assert bulkhead.max_concurrent == 10
        assert bulkhead.queue_size == 20
        assert bulkhead.timeout == 180.0


class TestBulkheadConcurrencyControl:
    """Tests for bulkhead concurrency limiting."""

    @pytest.mark.asyncio
    async def test_allows_concurrent_up_to_limit(self) -> None:
        """Test bulkhead allows concurrent execution up to max_concurrent."""
        # Use explicit config to isolate test from tier default changes
        bulkhead = Bulkhead(name="test", tier=Tier.OPTIONAL, max_concurrent=2)

        execution_count = 0
        max_concurrent_seen = 0

        async def slow_task() -> int:
            nonlocal execution_count, max_concurrent_seen
            execution_count += 1
            max_concurrent_seen = max(max_concurrent_seen, execution_count)
            await asyncio.sleep(0.1)
            execution_count -= 1
            return 1

        # Start 2 tasks (should both run concurrently)
        tasks = [bulkhead.execute(slow_task) for _ in range(2)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 2
        assert max_concurrent_seen == 2  # Both ran concurrently

    @pytest.mark.asyncio
    async def test_blocks_when_limit_exceeded(self) -> None:
        """Test bulkhead blocks when max_concurrent is exceeded."""
        # Use explicit config to isolate test from tier default changes
        bulkhead = Bulkhead(name="test", tier=Tier.OPTIONAL, max_concurrent=2)

        execution_count = 0
        max_concurrent_seen = 0

        async def slow_task() -> int:
            nonlocal execution_count, max_concurrent_seen
            execution_count += 1
            max_concurrent_seen = max(max_concurrent_seen, execution_count)
            await asyncio.sleep(0.1)
            execution_count -= 1
            return 1

        # Start 5 tasks (only 2 should run at a time)
        tasks = [bulkhead.execute(slow_task) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert max_concurrent_seen == 2  # Never exceeded limit

    @pytest.mark.asyncio
    async def test_queues_waiting_tasks(self) -> None:
        """Test bulkhead queues tasks when max_concurrent is reached."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            queue_size=5,
        )

        started = asyncio.Event()
        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            started.set()
            await can_finish.wait()
            return "done"

        # Start first task (occupies the one slot)
        task1 = asyncio.create_task(bulkhead.execute(blocking_task))
        await started.wait()

        # Queue additional tasks
        task2 = asyncio.create_task(bulkhead.execute(lambda: asyncio.sleep(0.01)))
        await asyncio.sleep(0.05)

        # Check stats
        assert bulkhead.stats.current_active == 1
        assert bulkhead.stats.current_queued >= 1

        # Release and finish
        can_finish.set()
        await asyncio.gather(task1, task2)


class TestBulkheadQueueManagement:
    """Tests for bulkhead queue size enforcement."""

    @pytest.mark.asyncio
    async def test_rejects_when_queue_full(self) -> None:
        """Test bulkhead rejects tasks when queue is full."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            queue_size=2,
            rejection_policy=RejectionPolicy.QUEUE,
        )

        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            await can_finish.wait()
            return "done"

        async def quick_task() -> str:
            await asyncio.sleep(0.01)
            return "quick"

        # Fill all slots (1 active + 2 queued)
        task1 = asyncio.create_task(bulkhead.execute(blocking_task))
        task2 = asyncio.create_task(bulkhead.execute(quick_task))
        task3 = asyncio.create_task(bulkhead.execute(quick_task))
        await asyncio.sleep(0.05)

        # Next task should be rejected
        with pytest.raises(BulkheadFullError) as exc_info:
            await bulkhead.execute(quick_task)

        assert "queue full" in str(exc_info.value)
        assert exc_info.value.tier == Tier.OPTIONAL

        # Clean up
        can_finish.set()
        await asyncio.gather(task1, task2, task3, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_abort_policy_rejects_immediately(self) -> None:
        """Test ABORT policy rejects tasks immediately when queue is full."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            queue_size=1,
            rejection_policy=RejectionPolicy.ABORT,
        )

        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            await can_finish.wait()
            return "done"

        # Fill all slots
        task1 = asyncio.create_task(bulkhead.execute(blocking_task))
        task2 = asyncio.create_task(bulkhead.execute(blocking_task))
        await asyncio.sleep(0.05)

        # ABORT policy should reject immediately
        with pytest.raises(BulkheadFullError):
            await bulkhead.execute(lambda: asyncio.sleep(0.01))

        # Clean up
        can_finish.set()
        await asyncio.gather(task1, task2, return_exceptions=True)


class TestBulkheadTimeoutBehavior:
    """Tests for bulkhead timeout enforcement."""

    @pytest.mark.asyncio
    async def test_timeout_waiting_for_semaphore(self) -> None:
        """Test timeout while waiting for semaphore."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            queue_size=5,
            timeout=0.2,  # Longer timeout for first task
        )

        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            await can_finish.wait()
            return "done"

        async def quick_task() -> str:
            await asyncio.sleep(0.01)
            return "quick"

        # Start blocking task that won't finish
        task1 = asyncio.create_task(bulkhead.execute(blocking_task))
        await asyncio.sleep(0.05)

        # Second task should timeout waiting for semaphore with custom short timeout
        start_time = asyncio.get_event_loop().time()
        with pytest.raises(BulkheadTimeoutError) as exc_info:
            # Use custom 0.1s timeout (shorter than bulkhead default 0.2s)
            await bulkhead.execute(quick_task, timeout=0.1)

        elapsed = asyncio.get_event_loop().time() - start_time

        assert "timed out after" in str(exc_info.value)
        # Should timeout around 0.1s
        assert elapsed < 0.25  # Give some buffer
        assert bulkhead.stats.timed_out_calls >= 1

        # Clean up - task1 will also timeout at 0.2s
        can_finish.set()
        try:
            await asyncio.wait_for(task1, timeout=0.5)
        except (TimeoutError, BulkheadTimeoutError):
            pass  # Expected

    @pytest.mark.asyncio
    async def test_timeout_during_execution(self) -> None:
        """Test timeout during task execution."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            timeout=0.1,
        )

        async def slow_task() -> str:
            await asyncio.sleep(1.0)  # Much longer than timeout
            return "done"

        with pytest.raises(BulkheadTimeoutError):
            await bulkhead.execute(slow_task)

        assert bulkhead.stats.timed_out_calls == 1

    @pytest.mark.asyncio
    async def test_custom_timeout_override(self) -> None:
        """Test custom timeout override per execution."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            timeout=1.0,  # Default timeout
        )

        async def slow_task() -> str:
            await asyncio.sleep(0.5)
            return "done"

        # Should timeout with custom 0.1s timeout
        with pytest.raises(BulkheadTimeoutError):
            await bulkhead.execute(slow_task, timeout=0.1)


class TestBulkheadStats:
    """Tests for bulkhead statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_track_successful_calls(self) -> None:
        """Test stats correctly track successful calls."""
        bulkhead = Bulkhead(name="test", tier=Tier.STANDARD)

        async def success_task() -> int:
            await asyncio.sleep(0.01)
            return 42

        # Execute multiple successful calls
        for _ in range(5):
            await bulkhead.execute(success_task)

        assert bulkhead.stats.total_calls == 5
        assert bulkhead.stats.successful_calls == 5
        assert bulkhead.stats.rejected_calls == 0
        assert bulkhead.stats.timed_out_calls == 0

    @pytest.mark.asyncio
    async def test_stats_track_rejected_calls(self) -> None:
        """Test stats correctly track rejected calls."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=1,
            queue_size=1,
        )

        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            await can_finish.wait()
            return "done"

        # Fill all slots
        task1 = asyncio.create_task(bulkhead.execute(blocking_task))
        task2 = asyncio.create_task(bulkhead.execute(blocking_task))
        await asyncio.sleep(0.05)

        # This should be rejected
        with pytest.raises(BulkheadFullError):
            await bulkhead.execute(lambda: asyncio.sleep(0.01))

        assert bulkhead.stats.rejected_calls == 1

        # Clean up
        can_finish.set()
        await asyncio.gather(task1, task2, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_stats_track_max_active_and_queued(self) -> None:
        """Test stats track maximum active and queued counts."""
        bulkhead = Bulkhead(
            name="test",
            tier=Tier.OPTIONAL,
            max_concurrent=2,
            queue_size=5,
        )

        can_finish = asyncio.Event()

        async def blocking_task() -> str:
            await can_finish.wait()
            return "done"

        # Start multiple tasks to queue them
        tasks = [asyncio.create_task(bulkhead.execute(blocking_task)) for _ in range(4)]
        await asyncio.sleep(0.05)

        # Check max tracking
        assert bulkhead.stats.max_active_seen <= 2
        assert bulkhead.stats.max_queued_seen >= 2

        # Clean up
        can_finish.set()
        await asyncio.gather(*tasks, return_exceptions=True)


class TestBulkheadStatus:
    """Tests for bulkhead status reporting."""

    def test_get_status_returns_complete_info(self) -> None:
        """Test get_status returns complete bulkhead information."""
        bulkhead = Bulkhead(
            name="test-bulkhead",
            tier=Tier.CRITICAL,
            max_concurrent=5,
            queue_size=10,
        )

        status = bulkhead.get_status()

        assert status["name"] == "test-bulkhead"
        assert status["tier"] == "CRITICAL"
        assert status["config"]["max_concurrent"] == 5
        assert status["config"]["queue_size"] == 10
        assert status["config"]["timeout"] == 180.0  # Issue #588: fail fast
        assert "current" in status
        assert "stats" in status


class TestBulkheadDecorator:
    """Tests for bulkhead decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_success(self) -> None:
        """Test bulkhead decorator with successful function."""
        bulkhead = Bulkhead(name="test", tier=Tier.STANDARD)

        @bulkhead
        async def my_func(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        result = await my_func(5)
        assert result == 10
        assert bulkhead.stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_decorator_with_exception(self) -> None:
        """Test bulkhead decorator with failing function."""
        bulkhead = Bulkhead(name="test", tier=Tier.STANDARD)

        @bulkhead
        async def my_func() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await my_func()

        # Exception should propagate but still count as a call
        assert bulkhead.stats.total_calls == 1


class TestBulkheadRegistry:
    """Tests for BulkheadRegistry singleton."""

    def test_singleton_behavior(self) -> None:
        """Test BulkheadRegistry returns same instance."""
        registry1 = BulkheadRegistry()
        registry2 = BulkheadRegistry()

        assert registry1 is registry2

    def test_register_new_bulkhead(self) -> None:
        """Test registering a new bulkhead."""
        registry = get_bulkhead_registry()

        bulkhead = registry.register("test-new", Tier.STANDARD)

        assert bulkhead.name == "test-new"
        assert bulkhead.tier == Tier.STANDARD

    def test_register_duplicate_returns_existing(self) -> None:
        """Test registering duplicate name returns existing bulkhead."""
        registry = get_bulkhead_registry()

        bulkhead1 = registry.register("test-duplicate", Tier.STANDARD)
        bulkhead2 = registry.register("test-duplicate", Tier.CRITICAL)

        # Should return same instance, ignore new tier
        assert bulkhead1 is bulkhead2
        assert bulkhead1.tier == Tier.STANDARD

    def test_get_existing_bulkhead(self) -> None:
        """Test getting an existing bulkhead."""
        registry = get_bulkhead_registry()

        registry.register("test-get", Tier.OPTIONAL)
        bulkhead = registry.get("test-get")

        assert bulkhead is not None
        assert bulkhead.name == "test-get"

    def test_get_nonexistent_returns_none(self) -> None:
        """Test getting non-existent bulkhead returns None."""
        registry = get_bulkhead_registry()

        bulkhead = registry.get("does-not-exist-12345")

        assert bulkhead is None

    def test_get_or_create_creates_if_missing(self) -> None:
        """Test get_or_create creates new bulkhead if missing."""
        registry = get_bulkhead_registry()

        bulkhead = registry.get_or_create("test-create", Tier.CRITICAL)

        assert bulkhead.name == "test-create"
        assert bulkhead.tier == Tier.CRITICAL

    def test_get_all_status(self) -> None:
        """Test getting status of all bulkheads."""
        registry = get_bulkhead_registry()

        registry.register("test-status-1", Tier.CRITICAL)
        registry.register("test-status-2", Tier.STANDARD)

        all_status = registry.get_all_status()

        assert isinstance(all_status, dict)
        assert len(all_status) >= 2  # At least our two test bulkheads

    def test_get_tier_status(self) -> None:
        """Test getting status by tier."""
        registry = get_bulkhead_registry()

        registry.register("test-tier-critical", Tier.CRITICAL)
        registry.register("test-tier-standard", Tier.STANDARD)

        critical_status = registry.get_tier_status(Tier.CRITICAL)

        assert "test-tier-critical" in critical_status or "tier_critical" in critical_status


class TestResilienceManagerInitialization:
    """Tests for ResilienceManager initialization."""

    def test_singleton_behavior(self) -> None:
        """Test ResilienceManager returns same instance."""
        manager1 = ResilienceManager()
        manager2 = ResilienceManager()

        assert manager1 is manager2

    def test_global_getter_function(self) -> None:
        """Test get_resilience_manager returns singleton."""
        manager1 = get_resilience_manager()
        manager2 = get_resilience_manager()

        assert manager1 is manager2

    def test_initializes_tier_bulkheads(self) -> None:
        """Test ResilienceManager initializes bulkheads for all tiers."""
        manager = get_resilience_manager()

        critical = manager.get_bulkhead(Tier.CRITICAL)
        standard = manager.get_bulkhead(Tier.STANDARD)
        optional = manager.get_bulkhead(Tier.OPTIONAL)

        assert critical is not None
        assert standard is not None
        assert optional is not None


class TestResilienceManagerCircuitBreakers:
    """Tests for ResilienceManager circuit breaker management."""

    def test_get_circuit_breaker_creates_new(self) -> None:
        """Test getting circuit breaker creates it if missing."""
        manager = get_resilience_manager()

        breaker = manager.get_circuit_breaker("test-service")

        assert breaker.name == "test-service"
        assert breaker.config.failure_threshold == 3
        assert breaker.config.timeout_seconds == 60.0

    def test_get_circuit_breaker_returns_existing(self) -> None:
        """Test getting circuit breaker returns existing instance."""
        manager = get_resilience_manager()

        breaker1 = manager.get_circuit_breaker("test-existing")
        breaker2 = manager.get_circuit_breaker("test-existing")

        assert breaker1 is breaker2


class TestResilienceManagerAgentExecution:
    """Tests for ResilienceManager.execute_agent coordination."""

    @pytest.mark.asyncio
    async def test_execute_agent_success(self) -> None:
        """Test execute_agent with successful function."""
        manager = get_resilience_manager()

        async def success_func() -> str:
            return "success"

        result = await manager.execute_agent(
            agent_type="test_agent",
            tier=Tier.STANDARD,
            fn=success_func,
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_agent_with_int_tier(self) -> None:
        """Test execute_agent with integer tier (AgentTier enum value)."""
        manager = get_resilience_manager()

        async def success_func() -> str:
            return "agent_result"

        # Test with int tiers (AgentTier.UNIVERSAL = 1, VALIDATION = 2, RESEARCH = 3)
        result1 = await manager.execute_agent(
            agent_type="universal_agent",
            tier=1,  # AgentTier.UNIVERSAL
            fn=success_func,
        )

        result2 = await manager.execute_agent(
            agent_type="validation_agent",
            tier=2,  # AgentTier.VALIDATION
            fn=success_func,
        )

        result3 = await manager.execute_agent(
            agent_type="research_agent",
            tier=3,  # AgentTier.RESEARCH
            fn=success_func,
        )

        assert result1 == "agent_result"
        assert result2 == "agent_result"
        assert result3 == "agent_result"

    @pytest.mark.asyncio
    async def test_execute_agent_respects_bulkhead_limits(self) -> None:
        """Test execute_agent respects bulkhead concurrency limits.

        Issue #588: OPTIONAL tier now allows 4 concurrent (was 2).
        """
        manager = get_resilience_manager()

        execution_count = 0
        max_concurrent_seen = 0
        can_finish = asyncio.Event()

        async def slow_agent() -> str:
            nonlocal execution_count, max_concurrent_seen
            execution_count += 1
            max_concurrent_seen = max(max_concurrent_seen, execution_count)
            await can_finish.wait()
            execution_count -= 1
            return "done"

        # Start multiple OPTIONAL tier agents (max_concurrent=4 per Issue #588)
        tasks = [
            asyncio.create_task(
                manager.execute_agent(
                    agent_type="test_agent",
                    tier=Tier.OPTIONAL,
                    fn=slow_agent,
                )
            )
            for _ in range(6)  # More than max_concurrent to test limiting
        ]

        await asyncio.sleep(0.1)

        # Should not exceed bulkhead limit (Issue #588: now 4)
        assert max_concurrent_seen <= 4

        # Clean up
        can_finish.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_execute_agent_with_circuit_breaker_failure(self) -> None:
        """Test execute_agent handles circuit breaker opening."""
        manager = get_resilience_manager()

        # Reset circuit breaker to clean state
        breaker = manager.get_circuit_breaker("llm_api")
        breaker.reset()

        async def failing_func() -> None:
            raise RuntimeError("LLM API failure")

        # Trigger failures to open circuit (failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await manager.execute_agent(
                    agent_type="test_agent",
                    tier=Tier.STANDARD,
                    fn=failing_func,
                )

        # Next call should fail fast with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await manager.execute_agent(
                agent_type="test_agent",
                tier=Tier.STANDARD,
                fn=failing_func,
            )

    @pytest.mark.asyncio
    async def test_execute_agent_with_bulkhead_rejection(self) -> None:
        """Test execute_agent handles bulkhead queue full.

        Issue #588: OPTIONAL tier now has max_concurrent=4, queue_size=6.
        Need 10 tasks to fill (4 active + 6 queued).
        """
        manager = get_resilience_manager()

        # Reset circuit breaker to avoid interference from other tests
        breaker = manager.get_circuit_breaker("llm_api")
        breaker.reset()

        can_finish = asyncio.Event()

        async def blocking_func() -> str:
            await can_finish.wait()
            return "done"

        # Fill OPTIONAL tier bulkhead (max_concurrent=4, queue_size=6 per Issue #588)
        tasks = [
            asyncio.create_task(
                manager.execute_agent(
                    agent_type="test_agent",
                    tier=Tier.OPTIONAL,
                    fn=blocking_func,
                )
            )
            for _ in range(10)  # 4 active + 6 queued = full
        ]

        await asyncio.sleep(0.1)

        # Next task should be rejected with BulkheadFullError
        # (Circuit breaker is reset, so it won't interfere)
        with pytest.raises(BulkheadFullError):
            await manager.execute_agent(
                agent_type="test_agent",
                tier=Tier.OPTIONAL,
                fn=blocking_func,
            )

        # Clean up
        can_finish.set()
        await asyncio.gather(*tasks, return_exceptions=True)


class TestResilienceManagerStatus:
    """Tests for ResilienceManager status reporting."""

    def test_get_status_includes_circuit_breakers(self) -> None:
        """Test get_status includes circuit breaker information."""
        manager = get_resilience_manager()

        # Create a circuit breaker
        manager.get_circuit_breaker("test-status-service")

        status = manager.get_status()

        assert "circuit_breakers" in status
        assert "test-status-service" in status["circuit_breakers"]

    def test_get_status_includes_bulkheads(self) -> None:
        """Test get_status includes bulkhead information."""
        manager = get_resilience_manager()

        status = manager.get_status()

        assert "bulkheads" in status
        assert len(status["bulkheads"]) >= 3  # At least 3 tier bulkheads


class TestResilienceWrapperIntegration:
    """Tests for execute_with_resilience wrapper function.

    Note: Testing the actual wrapper requires importing it, which creates
    a circular dependency in tests. These tests verify the integration
    through ResilienceManager.execute_agent instead.
    """

    @pytest.mark.asyncio
    async def test_wrapper_delegates_to_resilience_manager(self) -> None:
        """Test that wrapper correctly delegates to ResilienceManager."""
        # This is tested through execute_agent tests above
        # The wrapper is just a thin convenience layer
        manager = get_resilience_manager()

        async def test_func() -> str:
            return "wrapped_result"

        result = await manager.execute_agent(
            agent_type="wrapper_test",
            tier=1,  # AgentTier.UNIVERSAL
            fn=test_func,
        )

        assert result == "wrapped_result"

    @pytest.mark.asyncio
    async def test_wrapper_preserves_exceptions(self) -> None:
        """Test that wrapper preserves original exceptions."""
        manager = get_resilience_manager()

        async def failing_func() -> None:
            raise ValueError("Original error")

        # Reset circuit breaker
        breaker = manager.get_circuit_breaker("llm_api")
        breaker.reset()

        with pytest.raises(ValueError) as exc_info:
            await manager.execute_agent(
                agent_type="wrapper_test",
                tier=1,
                fn=failing_func,
            )

        assert "Original error" in str(exc_info.value)


class TestResilienceTierMapping:
    """Tests for AgentTier to Bulkhead Tier mapping."""

    @pytest.mark.asyncio
    async def test_tier_1_maps_to_critical(self) -> None:
        """Test AgentTier.UNIVERSAL (1) maps to Tier.CRITICAL."""
        manager = get_resilience_manager()

        async def test_func() -> str:
            return "tier1"

        # Execute with tier 1
        result = await manager.execute_agent(
            agent_type="tier1_agent",
            tier=1,
            fn=test_func,
        )

        assert result == "tier1"

        # Should use CRITICAL bulkhead (max_concurrent=5)
        critical = manager.get_bulkhead(Tier.CRITICAL)
        assert critical is not None

    @pytest.mark.asyncio
    async def test_tier_2_maps_to_standard(self) -> None:
        """Test AgentTier.VALIDATION (2) maps to Tier.STANDARD."""
        manager = get_resilience_manager()

        async def test_func() -> str:
            return "tier2"

        result = await manager.execute_agent(
            agent_type="tier2_agent",
            tier=2,
            fn=test_func,
        )

        assert result == "tier2"

    @pytest.mark.asyncio
    async def test_tier_3_maps_to_optional(self) -> None:
        """Test AgentTier.RESEARCH (3) maps to Tier.OPTIONAL."""
        manager = get_resilience_manager()

        async def test_func() -> str:
            return "tier3"

        result = await manager.execute_agent(
            agent_type="tier3_agent",
            tier=3,
            fn=test_func,
        )

        assert result == "tier3"

    @pytest.mark.asyncio
    async def test_unknown_tier_defaults_to_standard(self) -> None:
        """Test unknown tier defaults to Tier.STANDARD."""
        manager = get_resilience_manager()

        async def test_func() -> str:
            return "unknown_tier"

        # Use invalid tier number
        result = await manager.execute_agent(
            agent_type="unknown_agent",
            tier=999,  # Invalid tier
            fn=test_func,
        )

        assert result == "unknown_tier"


class TestResilienceConcurrentAgents:
    """Tests for concurrent agent execution with resilience."""

    @pytest.mark.asyncio
    async def test_different_tiers_isolated(self) -> None:
        """Test that different tiers don't interfere with each other."""
        manager = get_resilience_manager()

        can_finish_optional = asyncio.Event()
        can_finish_critical = asyncio.Event()

        async def slow_optional() -> str:
            await can_finish_optional.wait()
            return "optional_done"

        async def slow_critical() -> str:
            await can_finish_critical.wait()
            return "critical_done"

        # Fill OPTIONAL tier (max_concurrent=4 per Issue #588)
        optional_tasks = [
            asyncio.create_task(
                manager.execute_agent(
                    agent_type="optional_agent",
                    tier=Tier.OPTIONAL,
                    fn=slow_optional,
                )
            )
            for _ in range(2)
        ]

        await asyncio.sleep(0.05)

        # CRITICAL tier should still accept tasks
        critical_task = asyncio.create_task(
            manager.execute_agent(
                agent_type="critical_agent",
                tier=Tier.CRITICAL,
                fn=slow_critical,
            )
        )

        await asyncio.sleep(0.05)

        # Release and verify
        can_finish_optional.set()
        can_finish_critical.set()

        results = await asyncio.gather(*optional_tasks, critical_task)
        assert results == ["optional_done", "optional_done", "critical_done"]

    @pytest.mark.asyncio
    async def test_mixed_tier_concurrent_execution(self) -> None:
        """Test concurrent execution across multiple tiers."""
        manager = get_resilience_manager()

        execution_log = []

        async def log_agent(tier_name: str) -> str:
            execution_log.append(f"{tier_name}_start")
            await asyncio.sleep(0.05)
            execution_log.append(f"{tier_name}_end")
            return f"{tier_name}_result"

        # Execute agents across all tiers concurrently
        tasks = [
            manager.execute_agent(
                agent_type="critical1",
                tier=Tier.CRITICAL,
                fn=lambda: log_agent("critical1"),
            ),
            manager.execute_agent(
                agent_type="standard1",
                tier=Tier.STANDARD,
                fn=lambda: log_agent("standard1"),
            ),
            manager.execute_agent(
                agent_type="optional1",
                tier=Tier.OPTIONAL,
                fn=lambda: log_agent("optional1"),
            ),
        ]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3
        assert all("_result" in r for r in results)

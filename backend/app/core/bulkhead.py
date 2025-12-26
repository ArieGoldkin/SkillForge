"""Bulkhead Pattern Implementation for Tier-Based Isolation.

Issue #533: Provides tier-based resource isolation to prevent cascade failures
across agent tiers. Based on the resilience-patterns skill templates.

The bulkhead pattern isolates failures by partitioning resources:
- Tier 1 (UNIVERSAL): 5 workers, 10 queue, 300s timeout - Critical agents
- Tier 2 (VALIDATION): 3 workers, 5 queue, 120s timeout - Standard agents
- Tier 3 (RESEARCH): 2 workers, 3 queue, 60s timeout - Optional agents

This prevents a slow/failing Tier 3 agent from exhausting resources
and blocking critical Tier 1 agents.

Example:
    >>> from app.core.bulkhead import get_bulkhead_for_tier
    >>> from app.domains.analysis.agents.registry import AgentTier
    >>>
    >>> bulkhead = get_bulkhead_for_tier(AgentTier.UNIVERSAL)
    >>> result = await bulkhead.execute(lambda: agent.run())

References:
    - .claude/skills/resilience-patterns/templates/bulkhead.py
    - Martin Fowler: Bulkhead Pattern

"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, ClassVar, ParamSpec, TypeVar

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)

# Type variables for generic decorator
P = ParamSpec("P")
T = TypeVar("T")


class Tier(Enum):
    """Bulkhead tiers for resource prioritization."""

    CRITICAL = 1  # Tier 1: Universal agents (always run)
    STANDARD = 2  # Tier 2: Validation agents (Standard mode+)
    OPTIONAL = 3  # Tier 3: Research agents (Deep Dive mode)


class RejectionPolicy(Enum):
    """Policy when bulkhead is full."""

    ABORT = "abort"  # Raise exception immediately
    QUEUE = "queue"  # Wait in bounded queue (default)


@dataclass
class BulkheadStats:
    """Bulkhead statistics."""

    total_calls: int = 0
    successful_calls: int = 0
    rejected_calls: int = 0
    timed_out_calls: int = 0
    current_active: int = 0
    current_queued: int = 0
    max_active_seen: int = 0
    max_queued_seen: int = 0


class BulkheadFullError(Exception):
    """Raised when bulkhead queue is full."""

    def __init__(self, name: str, tier: Tier, queue_size: int) -> None:
        """Initialize bulkhead full error."""
        self.name = name
        self.tier = tier
        self.queue_size = queue_size
        super().__init__(f"Bulkhead '{name}' (tier={tier.name}) queue full ({queue_size} waiting)")


class BulkheadTimeoutError(Exception):
    """Raised when bulkhead operation times out."""

    def __init__(self, name: str, timeout: float) -> None:
        """Initialize bulkhead timeout error."""
        self.name = name
        self.timeout = timeout
        super().__init__(f"Bulkhead '{name}' operation timed out after {timeout}s")


# Default tier configurations (matches SkillForge agent tiers)
TIER_DEFAULTS = {
    Tier.CRITICAL: {"max_concurrent": 5, "queue_size": 10, "timeout": 300.0},
    Tier.STANDARD: {"max_concurrent": 3, "queue_size": 5, "timeout": 120.0},
    Tier.OPTIONAL: {"max_concurrent": 2, "queue_size": 3, "timeout": 60.0},
}


class Bulkhead:
    """Semaphore-based bulkhead for resource isolation.

    Isolates operations by limiting concurrency, preventing one
    slow/failing component from exhausting all resources.

    Example:
        >>> bulkhead = Bulkhead(name="analysis", tier=Tier.STANDARD)
        >>> result = await bulkhead.execute(lambda: analyze_content())

    """

    def __init__(  # noqa: PLR0913 - Factory pattern needs all params
        self,
        name: str,
        tier: Tier = Tier.STANDARD,
        max_concurrent: int | None = None,
        queue_size: int | None = None,
        timeout: float | None = None,
        rejection_policy: RejectionPolicy = RejectionPolicy.QUEUE,
    ) -> None:
        """Initialize bulkhead.

        Args:
            name: Identifier for logging and metrics
            tier: Resource tier (CRITICAL, STANDARD, OPTIONAL)
            max_concurrent: Override default max concurrent operations
            queue_size: Override default queue size
            timeout: Override default timeout in seconds
            rejection_policy: How to handle queue full (default: QUEUE)

        """
        self.name = name
        self.tier = tier

        # Get defaults for tier
        defaults = TIER_DEFAULTS[tier]
        self.max_concurrent = max_concurrent or int(defaults["max_concurrent"])
        self.queue_size = queue_size or int(defaults["queue_size"])
        self.timeout = timeout or float(defaults["timeout"])
        self.rejection_policy = rejection_policy

        # Semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # Track queue depth
        self._waiting = 0
        self._active = 0
        self._lock = asyncio.Lock()

        # Stats
        self.stats = BulkheadStats()

        logger.info(
            "bulkhead_initialized",
            name=name,
            tier=tier.name,
            max_concurrent=self.max_concurrent,
            queue_size=self.queue_size,
            timeout=self.timeout,
        )

    async def execute(
        self,
        fn: Callable[[], Awaitable[T]],
        timeout: float | None = None,  # noqa: ASYNC109 - Internal timeout param
    ) -> T:
        """Execute function within bulkhead constraints.

        Args:
            fn: Async function to execute (no args, use lambda if needed)
            timeout: Optional override for timeout

        Returns:
            Result from fn

        Raises:
            BulkheadFullError: If queue is full and policy is ABORT
            BulkheadTimeoutError: If operation times out

        """
        effective_timeout = timeout or self.timeout

        # Check queue capacity
        async with self._lock:
            if self._waiting >= self.queue_size:
                return await self._handle_rejection()

            self._waiting += 1
            self.stats.total_calls += 1
            self.stats.current_queued = self._waiting
            self.stats.max_queued_seen = max(self.stats.max_queued_seen, self._waiting)

        try:
            # Wait for semaphore with timeout
            try:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=effective_timeout,
                )
            except TimeoutError:
                async with self._lock:
                    self._waiting -= 1
                    self.stats.current_queued = self._waiting
                return await self._handle_timeout(effective_timeout)

            # Got semaphore, update counters
            async with self._lock:
                self._waiting -= 1
                self._active += 1
                self.stats.current_queued = self._waiting
                self.stats.current_active = self._active
                self.stats.max_active_seen = max(self.stats.max_active_seen, self._active)

            # Execute with timeout
            try:
                result = await asyncio.wait_for(fn(), timeout=effective_timeout)
                self.stats.successful_calls += 1
                return result
            except TimeoutError:
                return await self._handle_timeout(effective_timeout)
            finally:
                self._semaphore.release()
                async with self._lock:
                    self._active -= 1
                    self.stats.current_active = self._active

        except Exception:
            async with self._lock:
                if self._waiting > 0:
                    self._waiting -= 1
                    self.stats.current_queued = self._waiting
            raise

    async def _handle_rejection(self) -> T:
        """Handle queue full situation based on policy."""
        self.stats.rejected_calls += 1

        logger.warning(
            "bulkhead_rejecting_request",
            bulkhead=self.name,
            tier=self.tier.name,
            queue_size=self.queue_size,
            policy=self.rejection_policy.value,
        )

        if self.rejection_policy == RejectionPolicy.ABORT:
            raise BulkheadFullError(self.name, self.tier, self.queue_size)

        # QUEUE policy but queue is full, so abort
        raise BulkheadFullError(self.name, self.tier, self.queue_size)

    async def _handle_timeout(self, timeout: float) -> T:  # noqa: ASYNC109
        """Handle timeout situation."""
        self.stats.timed_out_calls += 1

        logger.warning(
            "bulkhead_operation_timeout",
            bulkhead=self.name,
            tier=self.tier.name,
            timeout_seconds=timeout,
        )

        raise BulkheadTimeoutError(self.name, timeout)

    def get_status(self) -> dict[str, object]:
        """Get current bulkhead status."""
        return {
            "name": self.name,
            "tier": self.tier.name,
            "config": {
                "max_concurrent": self.max_concurrent,
                "queue_size": self.queue_size,
                "timeout": self.timeout,
                "rejection_policy": self.rejection_policy.value,
            },
            "current": {
                "active": self.stats.current_active,
                "queued": self.stats.current_queued,
                "utilization": self.stats.current_active / self.max_concurrent,
            },
            "stats": {
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "rejected_calls": self.stats.rejected_calls,
                "timed_out_calls": self.stats.timed_out_calls,
                "max_active_seen": self.stats.max_active_seen,
                "max_queued_seen": self.stats.max_queued_seen,
            },
        }

    def __call__(self, fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """Use as decorator."""

        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.execute(lambda: fn(*args, **kwargs))

        return wrapper


class BulkheadRegistry:
    """Registry for managing multiple bulkheads.

    Singleton pattern to ensure tier bulkheads are shared across all agents.
    """

    _instance: ClassVar[BulkheadRegistry | None] = None
    _bulkheads: ClassVar[dict[str, Bulkhead]] = {}

    def __new__(cls) -> BulkheadRegistry:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._bulkheads = {}
        return cls._instance

    def register(
        self,
        name: str,
        tier: Tier,
        **kwargs: object,
    ) -> Bulkhead:
        """Register a new bulkhead."""
        if name in self._bulkheads:
            logger.debug("bulkhead_already_registered", name=name)
            return self._bulkheads[name]

        bulkhead = Bulkhead(name=name, tier=tier, **kwargs)  # type: ignore[arg-type]
        self._bulkheads[name] = bulkhead
        return bulkhead

    def get(self, name: str) -> Bulkhead | None:
        """Get bulkhead by name."""
        return self._bulkheads.get(name)

    def get_or_create(
        self,
        name: str,
        tier: Tier = Tier.STANDARD,
        **kwargs: object,
    ) -> Bulkhead:
        """Get existing or create new bulkhead."""
        if name not in self._bulkheads:
            return self.register(name, tier, **kwargs)
        return self._bulkheads[name]

    def get_all_status(self) -> dict[str, dict[str, object]]:
        """Get status of all bulkheads."""
        return {name: b.get_status() for name, b in self._bulkheads.items()}

    def get_tier_status(self, tier: Tier) -> dict[str, dict[str, object]]:
        """Get status of bulkheads in a specific tier."""
        return {name: b.get_status() for name, b in self._bulkheads.items() if b.tier == tier}


def get_bulkhead_registry() -> BulkheadRegistry:
    """Get global bulkhead registry."""
    return BulkheadRegistry()


# Lock for thread-safe reset operations
_bulkhead_reset_lock: asyncio.Lock | None = None


def _get_bulkhead_reset_lock() -> asyncio.Lock:
    """Get or create the reset lock (lazy init for event loop compatibility)."""
    global _bulkhead_reset_lock  # noqa: PLW0603 - Required for lazy initialization
    if _bulkhead_reset_lock is None:
        _bulkhead_reset_lock = asyncio.Lock()
    return _bulkhead_reset_lock


async def reset_bulkhead_registry() -> None:
    """Async-safe reset of bulkhead registry singleton for testing.

    This function:
    1. Acquires a lock to prevent concurrent reset operations
    2. Properly cleans up semaphores by releasing any waiting tasks
    3. Clears all singleton state to prevent test pollution

    Bulkheads with acquired semaphores can cause subsequent tests
    to fail with BulkheadTimeoutError if not properly cleaned up.

    Raises:
        RuntimeError: If called outside of pytest (production safety guard)

    Note:
        Only use in test fixtures via @pytest_asyncio.fixture, never in production.

    """
    # Production safety guard - prevent accidental production usage
    if "pytest" not in sys.modules:
        msg = "reset_bulkhead_registry() can only be called during tests"
        raise RuntimeError(msg)

    async with _get_bulkhead_reset_lock():
        # Clean up each bulkhead's internal state
        for name, bulkhead in BulkheadRegistry._bulkheads.items():
            # Reset counters to allow semaphore cleanup
            bulkhead._waiting = 0
            bulkhead._active = 0
            bulkhead.stats = BulkheadStats()

            # Create fresh semaphore (old one may have waiters)
            bulkhead._semaphore = asyncio.Semaphore(bulkhead.max_concurrent)

            logger.debug(
                "bulkhead_cleaned",
                name=name,
                tier=bulkhead.tier.name,
            )

        # Clear all bulkheads and singleton
        BulkheadRegistry._bulkheads = {}
        BulkheadRegistry._instance = None
        logger.debug("bulkhead_registry_reset", reason="test_cleanup")

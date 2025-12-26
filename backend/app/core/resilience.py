"""Resilience Registry for Circuit Breakers and Bulkheads.

Issue #533: Provides a unified interface for resilience patterns across the
multi-agent workflow. Combines circuit breakers (for LLM API failures) with
tier-based bulkheads (for resource isolation).

This module acts as the coordination layer between:
- CircuitBreaker: Fast-fail on repeated LLM API failures
- Bulkhead: Tier-based concurrency limits to prevent cascade failures
- AgentTier: Agent registry tier classification

Usage:
    >>> from app.core.resilience import get_resilience_manager
    >>>
    >>> manager = get_resilience_manager()
    >>> await manager.execute_agent(
    ...     agent_type="key_insights",
    ...     tier=AgentTier.UNIVERSAL,
    ...     fn=lambda: agent.run(),
    ... )

This wraps the agent execution with:
1. Circuit breaker for LLM API calls
2. Tier-based bulkhead for resource isolation
3. Graceful error handling

References:
    - .claude/skills/resilience-patterns/SKILL.md
    - app/core/circuit_breaker.py (existing)
    - app/core/bulkhead.py (new)

"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, TypeVar

from app.core.bulkhead import Bulkhead, BulkheadRegistry, Tier, get_bulkhead_registry
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)

T = TypeVar("T")


# Map AgentTier to Bulkhead Tier
# Avoids circular import by using int values
AGENT_TIER_TO_BULKHEAD_TIER = {
    1: Tier.CRITICAL,  # AgentTier.UNIVERSAL
    2: Tier.STANDARD,  # AgentTier.VALIDATION
    3: Tier.OPTIONAL,  # AgentTier.RESEARCH
}


class ResilienceManager:
    """Manages circuit breakers and bulkheads for multi-agent workflows.

    Singleton pattern to ensure shared resilience state across all agents.

    Example:
        >>> manager = ResilienceManager()
        >>> await manager.execute_agent(
        ...     agent_type="tech_comparator",
        ...     tier=AgentTier.VALIDATION,
        ...     fn=lambda: run_agent(),
        ... )

    """

    _instance: ClassVar[ResilienceManager | None] = None
    _circuit_breakers: ClassVar[dict[str, CircuitBreaker]] = {}
    _bulkhead_registry: ClassVar[BulkheadRegistry | None] = None

    def __new__(cls) -> ResilienceManager:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._circuit_breakers = {}
            cls._instance._bulkhead_registry = get_bulkhead_registry()
            # Initialize tier bulkheads
            cls._instance._initialize_tier_bulkheads()
        return cls._instance

    def _initialize_tier_bulkheads(self) -> None:
        """Initialize bulkheads for each tier."""
        if self._bulkhead_registry is None:
            return

        # Register bulkheads for each tier
        self._bulkhead_registry.get_or_create("tier_critical", Tier.CRITICAL)
        self._bulkhead_registry.get_or_create("tier_standard", Tier.STANDARD)
        self._bulkhead_registry.get_or_create("tier_optional", Tier.OPTIONAL)

        logger.info(
            "tier_bulkheads_initialized",
            tiers=["CRITICAL", "STANDARD", "OPTIONAL"],
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker for a service.

        Args:
            name: Service name (e.g., "llm_api", "openai", "anthropic")

        Returns:
            CircuitBreaker instance

        """
        if name not in self._circuit_breakers:
            # LLM-optimized config: Lower threshold, longer timeout
            config = CircuitBreakerConfig(
                failure_threshold=3,  # LLM APIs can be unstable
                success_threshold=2,
                timeout_seconds=60.0,  # Give API time to recover
            )
            self._circuit_breakers[name] = CircuitBreaker(name=name, config=config)
            logger.info("circuit_breaker_created", name=name, config=config)

        return self._circuit_breakers[name]

    def get_bulkhead(self, tier: Tier) -> Bulkhead | None:
        """Get bulkhead for a tier.

        Args:
            tier: Bulkhead tier (CRITICAL, STANDARD, OPTIONAL)

        Returns:
            Bulkhead instance or None if registry not initialized

        """
        if self._bulkhead_registry is None:
            return None

        tier_name = f"tier_{tier.name.lower()}"
        return self._bulkhead_registry.get(tier_name)

    async def execute_agent(
        self,
        agent_type: str,
        tier: int | Tier,
        fn: Callable[[], Awaitable[T]],
    ) -> T:
        """Execute agent with circuit breaker and bulkhead protection.

        Args:
            agent_type: Agent type name (for logging)
            tier: Agent tier (AgentTier enum value or Bulkhead Tier)
            fn: Async function to execute

        Returns:
            Result from fn

        Raises:
            Exception: Original exception if both circuit breaker and bulkhead pass

        """
        # Convert AgentTier int to Bulkhead Tier
        if isinstance(tier, int):
            bulkhead_tier = AGENT_TIER_TO_BULKHEAD_TIER.get(tier, Tier.STANDARD)
        else:
            bulkhead_tier = tier

        # Get circuit breaker for LLM API
        circuit_breaker = self.get_circuit_breaker("llm_api")

        # Get bulkhead for tier
        bulkhead = self.get_bulkhead(bulkhead_tier)

        logger.debug(
            "executing_agent_with_resilience",
            agent_type=agent_type,
            tier=bulkhead_tier.name,
            has_circuit_breaker=True,
            has_bulkhead=bulkhead is not None,
        )

        # Wrap execution with circuit breaker + bulkhead
        async def protected_execution() -> T:
            # First: Circuit breaker checks LLM API health
            result = await circuit_breaker.call(fn)
            assert result is not None  # noqa: S101 - Type guard
            return result

        # Second: Bulkhead limits concurrency by tier
        if bulkhead is not None:
            result = await bulkhead.execute(protected_execution)
            assert result is not None  # noqa: S101 - Type guard for bulkhead.execute
            return result

        # Fallback: Just use circuit breaker if no bulkhead
        result = await protected_execution()
        assert result is not None  # noqa: S101 - Type guard for circuit breaker
        return result

    def get_status(self) -> dict[str, object]:
        """Get status of all resilience components."""
        circuit_status = {
            name: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "is_open": cb.is_open,
            }
            for name, cb in self._circuit_breakers.items()
        }

        bulkhead_status = (
            self._bulkhead_registry.get_all_status() if self._bulkhead_registry else {}
        )

        return {
            "circuit_breakers": circuit_status,
            "bulkheads": bulkhead_status,
        }


# Global singleton instance
_resilience_manager: ResilienceManager | None = None


def get_resilience_manager() -> ResilienceManager:
    """Get global resilience manager."""
    global _resilience_manager  # noqa: PLW0603 - Acceptable for singleton
    if _resilience_manager is None:
        _resilience_manager = ResilienceManager()
    return _resilience_manager


def reset_resilience_manager() -> None:
    """Reset resilience manager singleton for testing.

    This function clears the singleton instance and circuit breaker state
    to prevent test pollution. The circuit breaker can stay OPEN for 60s
    after failures, causing unrelated tests to fail.

    Note: Only use in test fixtures, never in production code.
    """
    global _resilience_manager  # noqa: PLW0603 - Required for reset
    if _resilience_manager is not None:
        # Clear all circuit breakers by resetting their state
        ResilienceManager._circuit_breakers = {}
        ResilienceManager._instance = None
        _resilience_manager = None
        logger.debug("resilience_manager_reset", reason="test_cleanup")

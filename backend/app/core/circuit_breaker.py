"""Reusable Circuit Breaker Pattern Implementation.

Issue #428: Provides a generic async-compatible circuit breaker that can be
used with any external service (Langfuse, Redis, external APIs).

The circuit breaker pattern prevents cascade failures by:
1. Detecting repeated failures (CLOSED → OPEN)
2. Failing fast when service is known to be down (OPEN)
3. Gradually testing recovery (HALF_OPEN → CLOSED)

States:
    CLOSED:    Normal operation, requests pass through
    OPEN:      Too many failures, requests fail immediately
    HALF_OPEN: Testing if service recovered

Example:
    >>> from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
    >>>
    >>> breaker = CircuitBreaker(
    ...     name="redis", config=CircuitBreakerConfig(failure_threshold=3, timeout_seconds=30)
    ... )
    >>>
    >>> @breaker
    ... async def call_redis():
    ...     return await redis.get("key")

References:
    - Martin Fowler: https://martinfowler.com/bliki/CircuitBreaker.html
    - Microsoft Azure: https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker

"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = get_logger(__name__)

# Type variables for generic decorator
P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states following the standard pattern."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failure threshold exceeded, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit (default: 5)
        success_threshold: Successes needed to close from half-open (default: 2)
        timeout_seconds: Time before attempting recovery (default: 30.0)
        excluded_exceptions: Exceptions that don't trigger circuit breaker

    Example:
        >>> config = CircuitBreakerConfig(
        ...     failure_threshold=3,
        ...     timeout_seconds=60.0,
        ...     excluded_exceptions=(ValueError,),  # Don't trip on validation errors
        ... )

    """

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 30.0
    excluded_exceptions: tuple[type[Exception], ...] = field(default_factory=tuple)


@dataclass
class CircuitBreakerState:
    """Mutable internal state for circuit breaker.

    Thread-safe through asyncio locks in the breaker implementation.
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    last_state_change: float = field(default_factory=time.monotonic)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request cannot proceed.

    This exception should be caught at the API layer and converted to
    an appropriate HTTP response (503 Service Unavailable).
    """


class CircuitBreaker:
    """Async-compatible circuit breaker for external service resilience.

    Implements the standard circuit breaker pattern with three states.
    Can be used as a decorator or called directly.

    Example as decorator:
        >>> breaker = CircuitBreaker(name="api")
        >>> @breaker
        ... async def call_external_api():
        ...     return await httpx.get("https://api.example.com")

    Example with explicit call:
        >>> result = await breaker.call(my_async_function, arg1, arg2)

    """

    def __init__(
        self,
        name: str = "default",
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Identifier for logging and metrics
            config: Circuit breaker configuration

        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state.state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is allowing requests."""
        return self._state.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is blocking requests."""
        return self._state.state == CircuitState.OPEN

    @property
    def failure_count(self) -> int:
        """Current failure count."""
        return self._state.failure_count

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = time.monotonic()

        if old_state != new_state:
            logger.warning(
                "circuit_breaker_state_change",
                breaker=self.name,
                from_state=old_state.value,
                to_state=new_state.value,
                failure_count=self._state.failure_count,
            )

    async def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to try recovery."""
        if self._state.state != CircuitState.OPEN:
            return False

        if self._state.last_failure_time is None:
            return True

        elapsed = time.monotonic() - self._state.last_failure_time
        return elapsed >= self.config.timeout_seconds

    async def _handle_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1
                if self._state.success_count >= self.config.success_threshold:
                    self._state.failure_count = 0
                    self._state.success_count = 0
                    await self._transition_to(CircuitState.CLOSED)
                    logger.info(
                        "circuit_breaker_recovered",
                        breaker=self.name,
                        message="Circuit closed after successful recovery",
                    )
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def _handle_failure(self, exc: Exception) -> None:
        """Handle failed call."""
        # Don't count excluded exceptions
        if isinstance(exc, self.config.excluded_exceptions):
            logger.debug(
                "circuit_breaker_excluded_exception",
                breaker=self.name,
                exception_type=type(exc).__name__,
            )
            return

        async with self._lock:
            self._state.failure_count += 1
            self._state.last_failure_time = time.monotonic()

            if self._state.state == CircuitState.HALF_OPEN:
                # Immediate open on half-open failure
                self._state.success_count = 0
                await self._transition_to(CircuitState.OPEN)
            elif self._state.state == CircuitState.CLOSED:
                if self._state.failure_count >= self.config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

    async def call(
        self,
        func: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception if call fails

        """
        async with self._lock:
            if self._state.state == CircuitState.OPEN:
                if await self._should_attempt_reset():
                    await self._transition_to(CircuitState.HALF_OPEN)
                else:
                    msg = (
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {self.config.timeout_seconds}s"
                    )
                    raise CircuitBreakerOpenError(msg)

        try:
            result = await func(*args, **kwargs)
            await self._handle_success()
            return result
        except Exception as e:
            await self._handle_failure(e)
            raise

    def __call__(self, func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """Wrap function with circuit breaker protection.

        Example:
            >>> @circuit_breaker
            ... async def call_api():
            ...     return await api.fetch()

        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.call(func, *args, **kwargs)  # type: ignore[return-value]

        return wrapper

    def reset(self) -> None:
        """Reset circuit breaker to initial CLOSED state.

        Use this for testing or manual recovery.
        """
        self._state = CircuitBreakerState()
        logger.info(
            "circuit_breaker_reset",
            breaker=self.name,
            message="Circuit breaker manually reset to CLOSED",
        )

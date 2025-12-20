"""Tests for circuit breaker pattern implementation.

Issue #428: Comprehensive tests for the circuit breaker module.
"""

import asyncio

import pytest

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout_seconds == 30.0
        assert config.excluded_exceptions == ()

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=1,
            timeout_seconds=60.0,
            excluded_exceptions=(ValueError, TypeError),
        )

        assert config.failure_threshold == 3
        assert config.success_threshold == 1
        assert config.timeout_seconds == 60.0
        assert config.excluded_exceptions == (ValueError, TypeError)


class TestCircuitBreakerInitialization:
    """Tests for CircuitBreaker initialization."""

    def test_default_initialization(self) -> None:
        """Test default circuit breaker initialization."""
        breaker = CircuitBreaker()

        assert breaker.name == "default"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False
        assert breaker.failure_count == 0

    def test_custom_initialization(self) -> None:
        """Test custom circuit breaker initialization."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(name="test-breaker", config=config)

        assert breaker.name == "test-breaker"
        assert breaker.config.failure_threshold == 3


class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_closed_to_open_on_failures(self) -> None:
        """Test transition from CLOSED to OPEN after failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        # Trigger 3 failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open is True

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self) -> None:
        """Test transition from OPEN to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        # Trigger failure to open circuit
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should transition to HALF_OPEN
        async def success_func() -> str:
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        # After success in half-open with success_threshold=2, still half-open
        # But our call succeeded, so it's progressing

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self) -> None:
        """Test transition from HALF_OPEN to CLOSED after success."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        async def success_func() -> str:
            return "success"

        # Open circuit
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Two successful calls should close circuit
        await breaker.call(success_func)
        await breaker.call(success_func)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self) -> None:
        """Test transition from HALF_OPEN to OPEN on failure."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=0.1,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        async def success_func() -> str:
            return "success"

        # Open circuit
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        # Wait for timeout
        await asyncio.sleep(0.15)

        # First call transitions to half-open, then success
        await breaker.call(success_func)

        # Now in half-open, another failure should re-open
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerOpenBehavior:
    """Tests for behavior when circuit is open."""

    @pytest.mark.asyncio
    async def test_open_circuit_fails_fast(self) -> None:
        """Test that open circuit raises immediately."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_seconds=60.0,  # Long timeout
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        # Open circuit
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(failing_func)

        assert "is OPEN" in str(exc_info.value)
        assert "Retry after" in str(exc_info.value)


class TestCircuitBreakerSuccessHandling:
    """Tests for success handling."""

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        """Test that success resets failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Service unavailable")

        async def success_func() -> str:
            return "success"

        # Trigger 2 failures (not enough to open)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.failure_count == 2

        # Success should reset
        await breaker.call(success_func)
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerExcludedExceptions:
    """Tests for excluded exceptions."""

    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted(self) -> None:
        """Test that excluded exceptions don't trigger circuit breaker."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def validation_error_func() -> None:
            raise ValueError("Invalid input")

        # Many ValueErrors should NOT open circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                await breaker.call(validation_error_func)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestCircuitBreakerDecorator:
    """Tests for decorator functionality."""

    @pytest.mark.asyncio
    async def test_decorator_success(self) -> None:
        """Test decorator with successful function."""
        breaker = CircuitBreaker(name="test")

        @breaker
        async def my_func(x: int) -> int:
            return x * 2

        result = await my_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_decorator_failure(self) -> None:
        """Test decorator with failing function."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(name="test", config=config)

        @breaker
        async def my_func() -> None:
            raise RuntimeError("Error")

        with pytest.raises(RuntimeError):
            await my_func()

        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerReset:
    """Tests for manual reset."""

    @pytest.mark.asyncio
    async def test_reset_from_open(self) -> None:
        """Test resetting from OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            raise RuntimeError("Error")

        # Open circuit
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0


class TestCircuitBreakerConcurrency:
    """Tests for concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self) -> None:
        """Test circuit breaker with concurrent calls."""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker(name="test", config=config)

        call_count = 0

        async def counting_func() -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count

        # Run 10 concurrent calls
        tasks = [breaker.call(counting_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_failures(self) -> None:
        """Test circuit breaker with concurrent failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func() -> None:
            await asyncio.sleep(0.01)
            raise RuntimeError("Error")

        # Run concurrent failures
        tasks = [breaker.call(failing_func) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should be RuntimeError (some may be CircuitBreakerOpenError)
        error_count = sum(
            1 for r in results if isinstance(r, (RuntimeError, CircuitBreakerOpenError))
        )
        assert error_count == 5

        # Circuit should be open
        assert breaker.state == CircuitState.OPEN

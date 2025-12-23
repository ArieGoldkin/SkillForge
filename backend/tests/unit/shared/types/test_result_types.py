"""Unit tests for Result<T, E> type implementation (2025 best practice).

Tests cover the Rust-inspired Result type for type-safe error handling,
including all methods and pattern matching functionality.
"""

import pytest

from app.shared.types.result_types import (
    Result,
    UnwrapError,
    err,
    is_err,
    is_ok,
    match,
    ok,
)


class TestOk:
    """Tests for Ok variant of Result."""

    def test_is_ok_returns_true(self):
        """Ok.is_ok() returns True."""
        result = ok(42)
        assert result.is_ok() is True

    def test_is_err_returns_false(self):
        """Ok.is_err() returns False."""
        result = ok("hello")
        assert result.is_err() is False

    def test_unwrap_returns_value(self):
        """Ok.unwrap() returns the contained value."""
        result = ok(123)
        assert result.unwrap() == 123

    def test_unwrap_err_raises_error(self):
        """Ok.unwrap_err() raises UnwrapError."""
        result = ok("value")
        with pytest.raises(UnwrapError, match="Called unwrap_err on Ok value"):
            result.unwrap_err()

    def test_unwrap_or_returns_value(self):
        """Ok.unwrap_or() returns the contained value."""
        result = ok("actual")
        assert result.unwrap_or("default") == "actual"

    def test_unwrap_or_else_returns_value(self):
        """Ok.unwrap_or_else() returns the contained value."""
        result = ok(100)
        assert result.unwrap_or_else(lambda x: x * 2) == 100

    def test_map_applies_function(self):
        """Ok.map() applies function to contained value."""
        result = ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok()
        assert mapped.unwrap() == 10

    def test_map_err_returns_ok_unchanged(self):
        """Ok.map_err() returns the Ok unchanged."""
        result = ok("hello")
        mapped = result.map_err(lambda e: f"Error: {e}")
        assert mapped.is_ok()
        assert mapped.unwrap() == "hello"

    def test_and_then_chains_operations(self):
        """Ok.and_then() chains operations that return Results."""
        result = ok(10)

        def double_if_even(x: int) -> Result[int, str]:
            if x % 2 == 0:
                return ok(x * 2)
            return err("Odd number")

        chained = result.and_then(double_if_even)
        assert chained.is_ok()
        assert chained.unwrap() == 20

    def test_or_else_returns_ok_unchanged(self):
        """Ok.or_else() returns the Ok unchanged."""
        result = ok("success")
        recovered = result.or_else(lambda e: ok(f"Recovered: {e}"))
        assert recovered.is_ok()
        assert recovered.unwrap() == "success"

    def test_repr_shows_ok_and_value(self):
        """Ok.__repr__ shows Ok and the contained value."""
        result = ok(42)
        assert repr(result) == "Ok(42)"


class TestErr:
    """Tests for Err variant of Result."""

    def test_is_ok_returns_false(self):
        """Err.is_ok() returns False."""
        result = err("error message")
        assert result.is_ok() is False

    def test_is_err_returns_true(self):
        """Err.is_err() returns True."""
        result = err(404)
        assert result.is_err() is True

    def test_unwrap_raises_error_with_message(self):
        """Err.unwrap() raises UnwrapError with error message."""
        result = err("Something went wrong")
        with pytest.raises(UnwrapError, match="Called unwrap on Err value: Something went wrong"):
            result.unwrap()

    def test_unwrap_err_returns_error(self):
        """Err.unwrap_err() returns the contained error."""
        result = err("database error")
        assert result.unwrap_err() == "database error"

    def test_unwrap_or_returns_default(self):
        """Err.unwrap_or() returns the default value."""
        result = err("not found")
        assert result.unwrap_or("default") == "default"

    def test_unwrap_or_else_applies_function(self):
        """Err.unwrap_or_else() applies function to error."""
        result = err("timeout")
        value = result.unwrap_or_else(lambda e: f"Handled {e}")
        assert value == "Handled timeout"

    def test_map_returns_err_unchanged(self):
        """Err.map() returns the Err unchanged."""
        result = err("error")
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err()
        assert mapped.unwrap_err() == "error"

    def test_map_err_applies_function(self):
        """Err.map_err() applies function to contained error."""
        result = err("original error")
        mapped = result.map_err(lambda e: f"Enhanced: {e}")
        assert mapped.is_err()
        assert mapped.unwrap_err() == "Enhanced: original error"

    def test_and_then_returns_err_unchanged(self):
        """Err.and_then() returns the Err unchanged."""
        result = err("failed")

        def process(x: int) -> Result[int, str]:
            return ok(x + 1)

        chained = result.and_then(process)
        assert chained.is_err()
        assert chained.unwrap_err() == "failed"

    def test_or_else_recovers_with_new_result(self):
        """Err.or_else() allows error recovery."""
        result = err("network error")

        def recover(error: str) -> Result[str, str]:
            if "network" in error:
                return ok("recovered")
            return err("unrecoverable")

        recovered = result.or_else(recover)
        assert recovered.is_ok()
        assert recovered.unwrap() == "recovered"

    def test_repr_shows_err_and_value(self):
        """Err.__repr__ shows Err and the contained error."""
        result = err("error message")
        assert repr(result) == "Err('error message')"


class TestResultUtilities:
    """Tests for Result utility functions."""

    def test_is_ok_utility_function(self):
        """is_ok() utility function works correctly."""
        assert is_ok(ok(42)) is True
        assert is_ok(err("error")) is False

    def test_is_err_utility_function(self):
        """is_err() utility function works correctly."""
        assert is_err(ok(42)) is False
        assert is_err(err("error")) is True

    def test_match_ok_variant(self):
        """match() returns (True, value) for Ok."""
        result = ok("success")
        is_success, value = match(result)
        assert is_success is True
        assert value == "success"

    def test_match_err_variant(self):
        """match() returns (False, error) for Err."""
        result = err("failure")
        is_success, error = match(result)
        assert is_success is False
        assert error == "failure"


class TestResultUsagePatterns:
    """Tests for common Result usage patterns."""

    def test_division_example(self):
        """Test the division example from docstring."""

        def divide(a: int, b: int) -> Result[int, str]:
            if b == 0:
                return err("Division by zero")
            return ok(a // b)

        # Test successful division
        result = divide(10, 2)
        assert result.is_ok()
        assert result.unwrap() == 5

        # Test division by zero
        result = divide(10, 0)
        assert result.is_err()
        assert result.unwrap_err() == "Division by zero"

    def test_chaining_operations(self):
        """Test chaining multiple Result operations."""

        def parse_int(s: str) -> Result[int, str]:
            try:
                return ok(int(s))
            except ValueError:
                return err(f"Invalid integer: {s}")

        def divide_by_two(n: int) -> Result[float, str]:
            if n == 0:
                return err("Division by zero")
            return ok(n / 2)

        # Chain operations: parse -> divide
        result = parse_int("10").and_then(divide_by_two)
        assert result.is_ok()
        assert result.unwrap() == 5.0

        # Test error in first operation
        result = parse_int("not_a_number").and_then(divide_by_two)
        assert result.is_err()
        assert "Invalid integer" in result.unwrap_err()

        # Test error in second operation
        result = parse_int("0").and_then(divide_by_two)
        assert result.is_err()
        assert result.unwrap_err() == "Division by zero"

    def test_error_recovery(self):
        """Test error recovery with or_else."""

        def risky_operation() -> Result[int, str]:
            return err("Database connection failed")

        def fallback_operation(error: str) -> Result[int, str]:
            if "Database" in error:
                return ok(42)  # Fallback value
            return err("Unrecoverable error")

        result = risky_operation().or_else(fallback_operation)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_result_mapping(self):
        """Test mapping over Results."""

        def add_one(n: int) -> Result[int, str]:
            return ok(n + 1)

        def to_string(n: int) -> str:
            return f"Number: {n}"

        # Map success
        result = ok(5).map(add_one).map(lambda r: r.map(to_string))
        # This creates nested Results, flatten with and_then
        final = result.and_then(lambda x: x)
        assert final.is_ok()
        assert final.unwrap() == "Number: 6"

        # Map error (should remain unchanged)
        result = err("error").map(add_one)
        assert result.is_err()
        assert result.unwrap_err() == "error"

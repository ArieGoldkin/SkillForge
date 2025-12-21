"""Result<T, E> type for type-safe error handling (2025 best practice).

This module provides a Rust-inspired Result type that encapsulates either
a successful value (Ok) or an error (Err). This pattern provides compile-time
guarantees about error handling and eliminates null checks.

Usage:
    from app.shared.types.result_types import Result, ok, err

    def divide(a: int, b: int) -> Result[int, str]:
        if b == 0:
            return err("Division by zero")
        return ok(a // b)

    result = divide(10, 2)
    if result.is_ok():
        print(f"Result: {result.unwrap()}")  # 5
    else:
        print(f"Error: {result.unwrap_err()}")  # Won't execute

    # Or use pattern matching
    match result:
        case Ok(value):
            print(f"Success: {value}")
        case Err(error):
            print(f"Error: {error}")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

# Type variables for Result<T, E>
T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class Result[T, E](ABC):
    """Base Result type for type-safe error handling.

    Result<T, E> represents either a successful value of type T (Ok)
    or an error value of type E (Err). This pattern eliminates null
    checks and provides compile-time guarantees about error handling.
    """

    def __init__(self, value: T | E) -> None:
        """Initialize Result - use Ok() or Err() constructors instead."""
        self._value = value

    @abstractmethod
    def is_ok(self) -> bool:
        """Return True if this is an Ok value."""
        ...

    @abstractmethod
    def is_err(self) -> bool:
        """Return True if this is an Err value."""
        ...

    @abstractmethod
    def unwrap(self) -> T:
        """Return the contained Ok value or raise UnwrapError."""
        ...

    @abstractmethod
    def unwrap_err(self) -> E:
        """Return the contained Err value or raise UnwrapError."""
        ...

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Return contained Ok value or default if Err."""
        ...

    @abstractmethod
    def unwrap_or_else(self, op: Callable[[E], T]) -> T:
        """Return Ok value or compute default from Err."""
        ...

    @abstractmethod
    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        """Apply function to contained Ok value."""
        ...

    @abstractmethod
    def map_err(self, op: Callable[[E], U]) -> Result[T, U]:
        """Apply function to contained Err value."""
        ...

    @abstractmethod
    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain operations that return Results."""
        ...

    @abstractmethod
    def or_else(self, op: Callable[[E], Result[T, U]]) -> Result[T, U]:
        """Chain error recovery operations."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"


class Ok(Result[T, E]):
    """Successful Result containing a value of type T."""

    def __init__(self, value: T) -> None:
        """Create an Ok Result with the given value."""
        super().__init__(value)

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self._value  # type: ignore[return-value]

    def unwrap_err(self) -> E:
        msg = "Called unwrap_err on Ok value"
        raise UnwrapError(msg)

    def unwrap_or(self, default: T) -> T:
        return self._value  # type: ignore[return-value]

    def unwrap_or_else(self, op: Callable[[E], T]) -> T:
        return self._value  # type: ignore[return-value]

    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        return Ok(op(self._value))  # type: ignore[arg-type]

    def map_err(self, op: Callable[[E], U]) -> Result[T, U]:
        return Ok(self._value)  # type: ignore

    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return op(self._value)  # type: ignore[arg-type]

    def or_else(self, op: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return Ok(self._value)  # type: ignore


class Err(Result[T, E]):
    """Error Result containing an error value of type E."""

    def __init__(self, error: E) -> None:
        """Create an Err Result with the given error."""
        super().__init__(error)

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> T:
        msg = f"Called unwrap on Err value: {self._value}"
        raise UnwrapError(msg)

    def unwrap_err(self) -> E:
        return self._value  # type: ignore[return-value]

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_or_else(self, op: Callable[[E], T]) -> T:
        return op(self._value)  # type: ignore[arg-type]

    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        return Err(self._value)  # type: ignore

    def map_err(self, op: Callable[[E], U]) -> Result[T, U]:
        return Err(op(self._value))  # type: ignore

    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self._value)  # type: ignore

    def or_else(self, op: Callable[[E], Result[T, U]]) -> Result[T, U]:
        return op(self._value)  # type: ignore[arg-type]


class UnwrapError(Exception):
    """Exception raised when unwrapping a Result fails."""


# Convenience functions for creating Results
def ok(value: T) -> Result[T, E]:  # type: ignore
    """Create an Ok Result with the given value."""
    return Ok(value)


def err(error: E) -> Result[T, E]:  # type: ignore
    """Create an Err Result with the given error."""
    return Err(error)


# Utility functions for working with Results
def is_ok(result: Result[T, E]) -> bool:
    """Check if a Result is Ok."""
    return result.is_ok()


def is_err(result: Result[T, E]) -> bool:
    """Check if a Result is Err."""
    return result.is_err()


# Pattern matching helpers (Python 3.10+)
def match(result: Result[T, E]) -> tuple[bool, T | E]:
    """Return (is_ok, value_or_error) for pattern matching."""
    if result.is_ok():
        return True, result.unwrap()
    return False, result.unwrap_err()

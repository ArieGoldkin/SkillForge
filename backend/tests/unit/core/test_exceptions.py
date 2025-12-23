"""Unit tests for exception utilities."""

import pytest

from app.core.exceptions import is_cleanup_generator_exit


@pytest.mark.unit
def test_is_cleanup_generator_exit_cleanup_case():
    """Test that cleanup GeneratorExit is detected correctly."""
    # Cleanup GeneratorExit (workflow completed)
    assert is_cleanup_generator_exit(GeneratorExit(), workflow_completed=True) is True


@pytest.mark.unit
def test_is_cleanup_generator_exit_execution_case():
    """Test that execution GeneratorExit is detected correctly."""
    # Execution GeneratorExit (workflow didn't complete)
    assert is_cleanup_generator_exit(GeneratorExit(), workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_converted_runtime_error():
    """Test that converted RuntimeError from GeneratorExit is detected."""
    # Converted RuntimeError (Python async runtime converts GeneratorExit)
    converted_error = RuntimeError("coroutine ignored GeneratorExit")
    assert is_cleanup_generator_exit(converted_error, workflow_completed=True) is True
    assert is_cleanup_generator_exit(converted_error, workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_other_runtime_error():
    """Test that other RuntimeErrors are not detected as GeneratorExit."""
    # Other RuntimeError (not from GeneratorExit)
    other_error = RuntimeError("some other error")
    assert is_cleanup_generator_exit(other_error, workflow_completed=True) is False
    assert is_cleanup_generator_exit(other_error, workflow_completed=False) is False


@pytest.mark.unit
def test_is_cleanup_generator_exit_other_exception():
    """Test that other exceptions are not detected as GeneratorExit."""
    # Other exception types
    assert is_cleanup_generator_exit(ValueError("test"), workflow_completed=True) is False
    assert is_cleanup_generator_exit(KeyError("test"), workflow_completed=False) is False
    assert is_cleanup_generator_exit(Exception("test"), workflow_completed=True) is False

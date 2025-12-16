"""Unit tests for timeout handling utilities."""

from unittest.mock import MagicMock

import pytest

from app.shared.workflows.utils.timeout_handling import (

@pytest.mark.unit
    convert_generatorexit_to_timeouterror,
    handle_timeout_error,
)


@pytest.fixture
def mock_logger():
    """Mock structured logger."""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.exception = MagicMock()
    return logger


def test_convert_generatorexit_to_timeouterror(mock_logger):
    """Test GeneratorExit is converted to TimeoutError."""
    exc = GeneratorExit("Generator closed")
    context = "Test operation"
    timeout = 120.0

    result = convert_generatorexit_to_timeouterror(
        exc=exc,
        context=context,
        timeout=timeout,
        logger=mock_logger,
        test_key="test_value",
    )

    assert isinstance(result, TimeoutError)
    assert "exceeded timeout" in str(result)
    assert "generator closed" in str(result)
    mock_logger.warning.assert_called_once()
    call_kwargs = mock_logger.warning.call_args[1]
    assert call_kwargs["context"] == context
    assert call_kwargs["timeout"] == timeout
    assert call_kwargs["test_key"] == "test_value"


def test_handle_timeout_error_with_generatorexit(mock_logger):
    """Test handle_timeout_error converts GeneratorExit."""
    exc = GeneratorExit("Generator closed")
    context = "Test operation"
    timeout = 120.0

    result = handle_timeout_error(
        exc=exc,
        context=context,
        timeout=timeout,
        logger=mock_logger,
    )

    assert isinstance(result, TimeoutError)
    mock_logger.warning.assert_called_once()


def test_handle_timeout_error_with_timeouterror(mock_logger):
    """Test handle_timeout_error re-raises TimeoutError."""
    exc = TimeoutError("Operation timed out")
    context = "Test operation"
    timeout = 120.0

    result = handle_timeout_error(
        exc=exc,
        context=context,
        timeout=timeout,
        logger=mock_logger,
    )

    assert isinstance(result, TimeoutError)
    assert "exceeded timeout" in str(result)
    mock_logger.exception.assert_called_once()

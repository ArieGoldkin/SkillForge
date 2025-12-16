"""Unit tests for constants module."""

from app.core.constants import (
import pytest

    CONTENT_TYPE_ARTICLE,
    CONTENT_TYPE_REPO,
    CONTENT_TYPE_VIDEO,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DEFAULT_TIMEOUT,
    DEFAULT_TITLE,
    EMBEDDING_TIMEOUT,
    HTTP_ERROR_THRESHOLD,
    HTTP_NOT_FOUND,
    HTTP_OK,
    MAX_ERROR_MESSAGE_LENGTH,
    MAX_ERROR_MESSAGE_LENGTH_LONG,
    MAX_MODELS_PREVIEW_COUNT,
    MAX_RETRY_ATTEMPTS,
    MAX_TITLE_PREVIEW_LENGTH,
    RETRY_MAX_WAIT_EMBEDDING,
    RETRY_MAX_WAIT_JINA,
    RETRY_MIN_WAIT_EMBEDDING,
    RETRY_MIN_WAIT_JINA,
    RETRY_MULTIPLIER_EMBEDDING,
    RETRY_MULTIPLIER_JINA,
)


def test_http_status_codes() -> None:
    """Test HTTP status code constants."""
    assert HTTP_OK == 200
    assert HTTP_NOT_FOUND == 404
    assert HTTP_ERROR_THRESHOLD == 400


def test_timeout_constants() -> None:
    """Test timeout constants."""
    assert DEFAULT_TIMEOUT == 30.0
    assert EMBEDDING_TIMEOUT == 120.0
    assert all(isinstance(t, float) for t in [DEFAULT_TIMEOUT, EMBEDDING_TIMEOUT])


def test_text_limits() -> None:
    """Test text and message limit constants."""
    assert MAX_ERROR_MESSAGE_LENGTH == 100
    assert MAX_ERROR_MESSAGE_LENGTH_LONG == 200
    assert MAX_TITLE_PREVIEW_LENGTH == 100
    assert MAX_MODELS_PREVIEW_COUNT == 5
    assert isinstance(MAX_ERROR_MESSAGE_LENGTH, int)


def test_retry_configuration() -> None:
    """Test retry configuration constants."""
    assert MAX_RETRY_ATTEMPTS == 3
    assert RETRY_MULTIPLIER_EMBEDDING == 2
    assert RETRY_MIN_WAIT_EMBEDDING == 2
    assert RETRY_MAX_WAIT_EMBEDDING == 16
    assert RETRY_MULTIPLIER_JINA == 1
    assert RETRY_MIN_WAIT_JINA == 1
    assert RETRY_MAX_WAIT_JINA == 10


def test_database_pool_configuration() -> None:
    """Test database pool configuration constants."""
    assert DB_POOL_SIZE == 5
    assert DB_MAX_OVERFLOW == 10
    assert DB_POOL_RECYCLE == 3600
    assert all(isinstance(v, int) for v in [DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_RECYCLE])


def test_content_types() -> None:
    """Test content type constants."""
    assert CONTENT_TYPE_ARTICLE == "article"
    assert CONTENT_TYPE_VIDEO == "video"
    assert CONTENT_TYPE_REPO == "repo"
    assert all(
        isinstance(ct, str) for ct in [CONTENT_TYPE_ARTICLE, CONTENT_TYPE_VIDEO, CONTENT_TYPE_REPO]
    )


def test_default_values() -> None:
    """Test default value constants."""
    assert DEFAULT_TITLE == "Untitled"
    assert isinstance(DEFAULT_TITLE, str)

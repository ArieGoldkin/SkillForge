"""Unit tests for Redis caching service."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr


# =============================================================================
# Tests for _get_embedding_model
# =============================================================================


@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.OpenAIEmbeddings")
def test_get_embedding_model_success(mock_openai_embeddings, mock_settings):
    """Test _get_embedding_model creates OpenAI embeddings."""
    from app.shared.services.cache.redis_service import _get_embedding_model

    # Clear cache for this test
    _get_embedding_model.cache_clear()

    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_embeddings = MagicMock()
    mock_openai_embeddings.return_value = mock_embeddings

    result = _get_embedding_model()

    # Verify OpenAIEmbeddings was called with correct params
    mock_openai_embeddings.assert_called_once()
    call_kwargs = mock_openai_embeddings.call_args.kwargs
    assert call_kwargs["model"] == "text-embedding-3-small"
    assert isinstance(call_kwargs["openai_api_key"], SecretStr)
    assert call_kwargs["openai_api_key"].get_secret_value() == "sk-test-key"
    assert result == mock_embeddings


@patch("app.shared.services.cache.redis_service.settings")
def test_get_embedding_model_missing_api_key(mock_settings):
    """Test _get_embedding_model raises error without API key."""
    from app.shared.services.cache.redis_service import _get_embedding_model

    # Clear cache for this test
    _get_embedding_model.cache_clear()

    mock_settings.OPENAI_API_KEY = None

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        _get_embedding_model()


# =============================================================================
# Tests for get_semantic_cache
# =============================================================================


@patch("app.shared.services.cache.redis_service._get_embedding_model")
@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.RedisSemanticCache")
def test_get_semantic_cache_success(
    mock_redis_semantic_cache, mock_settings, mock_get_embedding_model
):
    """Test get_semantic_cache creates RedisSemanticCache correctly."""
    from app.shared.services.cache.redis_service import get_semantic_cache

    # Clear cache for this test
    get_semantic_cache.cache_clear()

    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.REDIS_SEMANTIC_CACHE_TTL = 86400
    mock_settings.REDIS_SIMILARITY_THRESHOLD = 0.08

    mock_embeddings = MagicMock()
    mock_get_embedding_model.return_value = mock_embeddings

    mock_cache = MagicMock()
    mock_redis_semantic_cache.return_value = mock_cache

    result = get_semantic_cache()

    mock_redis_semantic_cache.assert_called_once_with(
        embeddings=mock_embeddings,
        redis_url="redis://localhost:6379",
        distance_threshold=0.08,
        ttl=86400,
    )
    assert result == mock_cache


# =============================================================================
# Tests for get_exact_cache
# =============================================================================


@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.RedisCache")
def test_get_exact_cache_success(mock_redis_cache, mock_settings):
    """Test get_exact_cache creates RedisCache correctly."""
    from app.shared.services.cache.redis_service import get_exact_cache

    # Clear cache for this test
    get_exact_cache.cache_clear()

    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.REDIS_EXACT_CACHE_TTL = 3600

    mock_cache = MagicMock()
    mock_redis_cache.return_value = mock_cache

    result = get_exact_cache()

    mock_redis_cache.assert_called_once_with(
        redis_url="redis://localhost:6379",
        ttl=3600,
    )
    assert result == mock_cache


# =============================================================================
# Tests for get_chat_history
# =============================================================================


@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.RedisChatMessageHistory")
def test_get_chat_history_success(mock_redis_history, mock_settings):
    """Test get_chat_history creates RedisChatMessageHistory correctly."""
    from app.shared.services.cache.redis_service import get_chat_history

    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.REDIS_CHAT_HISTORY_TTL = 7200

    mock_history = MagicMock()
    mock_redis_history.return_value = mock_history

    result = get_chat_history("session_123")

    mock_redis_history.assert_called_once_with(
        session_id="session_123",
        redis_url="redis://localhost:6379",
        ttl=7200,
        key_prefix="skillforge:tutor:",
    )
    assert result == mock_history


@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.RedisChatMessageHistory")
def test_get_chat_history_with_custom_ttl(mock_redis_history, mock_settings):
    """Test get_chat_history respects custom TTL."""
    from app.shared.services.cache.redis_service import get_chat_history

    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.REDIS_CHAT_HISTORY_TTL = 7200

    mock_history = MagicMock()
    mock_redis_history.return_value = mock_history

    result = get_chat_history("session_456", ttl=3600)  # Custom TTL

    mock_redis_history.assert_called_once_with(
        session_id="session_456",
        redis_url="redis://localhost:6379",
        ttl=3600,  # Custom TTL used
        key_prefix="skillforge:tutor:",
    )
    assert result == mock_history


@patch("app.shared.services.cache.redis_service.settings")
@patch("app.shared.services.cache.redis_service.RedisChatMessageHistory")
def test_get_chat_history_not_cached(mock_redis_history, mock_settings):
    """Test get_chat_history creates new instance for each session."""
    from app.shared.services.cache.redis_service import get_chat_history

    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.REDIS_CHAT_HISTORY_TTL = 7200

    mock_history1 = MagicMock()
    mock_history2 = MagicMock()
    mock_redis_history.side_effect = [mock_history1, mock_history2]

    result1 = get_chat_history("session_1")
    result2 = get_chat_history("session_2")

    # Each session should get its own history instance
    assert result1 == mock_history1
    assert result2 == mock_history2
    assert mock_redis_history.call_count == 2


# =============================================================================
# Tests for clear_all_caches
# =============================================================================


def test_clear_all_caches():
    """Test clear_all_caches clears all cached instances."""
    from app.shared.services.cache.redis_service import (
        _get_embedding_model,
        clear_all_caches,
        get_exact_cache,
        get_semantic_cache,
    )

    # Call clear and verify no errors
    clear_all_caches()

    # Caches should be cleared (cache_info would show misses)
    info = _get_embedding_model.cache_info()
    assert info.hits == 0
    assert info.currsize == 0


# =============================================================================
# Tests for _SESSION_ID_TRUNCATE_LENGTH constant
# =============================================================================


def test_session_id_truncate_length_constant():
    """Test _SESSION_ID_TRUNCATE_LENGTH is defined correctly."""
    from app.shared.services.cache.redis_service import _SESSION_ID_TRUNCATE_LENGTH

    assert _SESSION_ID_TRUNCATE_LENGTH == 8

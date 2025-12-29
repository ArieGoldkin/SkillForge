"""Test circuit breaker and timeout configuration for embedding service.

Issue: 2025 best practice OpenAI client timeout and circuit breaker pattern
Tests the httpx.Timeout configuration and CircuitBreaker integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.core.circuit_breaker import CircuitState
from app.core.constants import (
    EMBEDDING_CIRCUIT_FAILURE_THRESHOLD,
    EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD,
    EMBEDDING_CIRCUIT_TIMEOUT_SECONDS,
    EMBEDDING_HTTP_CONNECT_TIMEOUT,
    EMBEDDING_HTTP_POOL_TIMEOUT,
    EMBEDDING_HTTP_READ_TIMEOUT,
    EMBEDDING_HTTP_WRITE_TIMEOUT,
)
from app.core.exceptions import EmbeddingError
from app.shared.services.embeddings.service import EmbeddingService


class TestEmbeddingServiceCircuitBreaker:
    """Test circuit breaker integration in embedding service."""

    @pytest.fixture
    def embedding_service(self) -> EmbeddingService:
        """Create embedding service with mocked dependencies."""
        with patch("app.shared.services.embeddings.service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.METRICS_ENABLED = False
            service = EmbeddingService()
            # Reset circuit breaker state before each test
            service._circuit_breaker.reset()
            return service

    def test_circuit_breaker_initialized_with_correct_config(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that circuit breaker is initialized with correct configuration."""
        assert embedding_service._circuit_breaker is not None
        assert embedding_service._circuit_breaker.name == "embedding_service"
        assert embedding_service._circuit_breaker.state == CircuitState.CLOSED
        assert (
            embedding_service._circuit_breaker.config.failure_threshold
            == EMBEDDING_CIRCUIT_FAILURE_THRESHOLD
        )
        assert (
            embedding_service._circuit_breaker.config.success_threshold
            == EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD
        )
        assert (
            embedding_service._circuit_breaker.config.timeout_seconds
            == EMBEDDING_CIRCUIT_TIMEOUT_SECONDS
        )
        # Verify ValueError is excluded (validation errors shouldn't trip circuit)
        assert ValueError in embedding_service._circuit_breaker.config.excluded_exceptions

    def test_timeout_configuration(self, embedding_service: EmbeddingService) -> None:
        """Test that httpx timeout is configured correctly."""
        assert isinstance(embedding_service.client.timeout, httpx.Timeout)
        assert embedding_service.client.timeout.connect == EMBEDDING_HTTP_CONNECT_TIMEOUT
        assert embedding_service.client.timeout.read == EMBEDDING_HTTP_READ_TIMEOUT
        assert embedding_service.client.timeout.write == EMBEDDING_HTTP_WRITE_TIMEOUT
        assert embedding_service.client.timeout.pool == EMBEDDING_HTTP_POOL_TIMEOUT

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_connection_errors(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that circuit breaker tracks API connection errors."""
        # Create mock request for OpenAI exceptions
        mock_request = MagicMock()
        mock_request.url = "https://api.openai.com/v1/embeddings"
        mock_request.method = "POST"

        # Mock the client to raise connection errors
        embedding_service.client.embeddings.create = AsyncMock(
            side_effect=APIConnectionError(request=mock_request)
        )

        # Attempt should fail with EmbeddingError
        with pytest.raises(EmbeddingError):
            await embedding_service.generate_embedding("test")

        # Circuit breaker should have recorded failures (including retries from tenacity)
        assert embedding_service._circuit_breaker.failure_count >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_timeout_errors(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that circuit breaker tracks timeout errors."""
        # Create mock request for OpenAI exceptions
        mock_request = MagicMock()
        mock_request.url = "https://api.openai.com/v1/embeddings"
        mock_request.method = "POST"

        # Mock the client to raise timeout errors
        embedding_service.client.embeddings.create = AsyncMock(
            side_effect=APITimeoutError(request=mock_request)
        )

        with pytest.raises(EmbeddingError):
            await embedding_service.generate_embedding("test")

        # Verify circuit breaker counted failures (including retries from tenacity)
        assert embedding_service._circuit_breaker.failure_count >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_rate_limit_errors(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that circuit breaker tracks rate limit errors."""
        # Create mock request and response for OpenAI exceptions
        mock_request = MagicMock()
        mock_request.url = "https://api.openai.com/v1/embeddings"
        mock_request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        # Mock the client to raise rate limit errors
        embedding_service.client.embeddings.create = AsyncMock(
            side_effect=RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        )

        with pytest.raises(EmbeddingError):
            await embedding_service.generate_embedding("test")

        # Verify circuit breaker counted failures (including retries from tenacity)
        assert embedding_service._circuit_breaker.failure_count >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_excludes_validation_errors(
        self, embedding_service: EmbeddingService
    ) -> None:
        """Test that validation errors don't trip the circuit breaker."""
        # Test empty text validation (should not trip circuit)
        with pytest.raises(ValueError, match="cannot be empty"):
            await embedding_service.generate_embedding("")

        # Circuit should still be closed
        assert embedding_service._circuit_breaker.state == CircuitState.CLOSED
        assert embedding_service._circuit_breaker.failure_count == 0


class TestEmbeddingServiceTimeoutConfiguration:
    """Test httpx timeout configuration for embedding service."""

    def test_timeout_constants_defined(self) -> None:
        """Test that all timeout constants are defined with correct values."""
        assert EMBEDDING_HTTP_CONNECT_TIMEOUT == 5.0
        assert EMBEDDING_HTTP_READ_TIMEOUT == 120.0
        assert EMBEDDING_HTTP_WRITE_TIMEOUT == 10.0
        assert EMBEDDING_HTTP_POOL_TIMEOUT == 60.0

    def test_circuit_breaker_constants_defined(self) -> None:
        """Test that circuit breaker constants are defined with correct values."""
        assert EMBEDDING_CIRCUIT_FAILURE_THRESHOLD == 5
        assert EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD == 2
        assert EMBEDDING_CIRCUIT_TIMEOUT_SECONDS == 60.0

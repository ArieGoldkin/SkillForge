"""Tests for Langfuse API client with circuit breaker.

Issue #428: Comprehensive tests for the Langfuse client module.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.circuit_breaker import CircuitBreakerConfig, CircuitState
from app.core.langfuse_client import (
    LangfuseClient,
    LangfuseClientError,
    close_langfuse_client,
    get_langfuse_api_client,
)


class TestLangfuseClientInitialization:
    """Tests for LangfuseClient initialization."""

    def test_basic_initialization(self) -> None:
        """Test basic client initialization."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
            host="http://localhost:3000",
        )

        assert client.public_key == "pk-test"
        assert client.secret_key == "sk-test"
        assert client.host == "http://localhost:3000"
        assert client.timeout == 30.0
        assert client.max_retries == 3

    def test_host_trailing_slash_removed(self) -> None:
        """Test that trailing slash is removed from host."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
            host="http://localhost:3000/",
        )

        assert client.host == "http://localhost:3000"

    def test_custom_timeout_and_retries(self) -> None:
        """Test custom timeout and retry configuration."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
            timeout=60.0,
            max_retries=5,
        )

        assert client.timeout == 60.0
        assert client.max_retries == 5

    def test_custom_circuit_breaker_config(self) -> None:
        """Test custom circuit breaker configuration."""
        config = CircuitBreakerConfig(failure_threshold=10)
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
            circuit_breaker_config=config,
        )

        assert client._circuit_breaker.config.failure_threshold == 10


class TestLangfuseClientFromEnv:
    """Tests for LangfuseClient.from_env() factory method."""

    def test_from_env_disabled(self) -> None:
        """Test that None is returned when Langfuse is disabled."""
        with patch.dict(os.environ, {"LANGFUSE_ENABLED": "false"}, clear=True):
            client = LangfuseClient.from_env()
            assert client is None

    def test_from_env_missing_keys(self) -> None:
        """Test that None is returned when keys are missing."""
        with patch.dict(
            os.environ,
            {"LANGFUSE_ENABLED": "true"},
            clear=True,
        ):
            client = LangfuseClient.from_env()
            assert client is None

    def test_from_env_success(self) -> None:
        """Test successful client creation from environment."""
        env = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://custom:3000",
            "LANGFUSE_TIMEOUT": "45",
            "LANGFUSE_MAX_RETRIES": "4",
        }
        with patch.dict(os.environ, env, clear=True):
            client = LangfuseClient.from_env()

            assert client is not None
            assert client.public_key == "pk-test"
            assert client.host == "http://custom:3000"
            assert client.timeout == 45.0
            assert client.max_retries == 4


class TestLangfuseClientHttpClient:
    """Tests for HTTP client management."""

    @pytest.mark.asyncio
    async def test_get_http_client_creates_client(self) -> None:
        """Test that HTTP client is created on first access."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        assert client._http_client is None

        http_client = await client._get_http_client()

        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)

        await client.close()

    @pytest.mark.asyncio
    async def test_close_client(self) -> None:
        """Test that close properly closes the HTTP client."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        await client._get_http_client()
        assert client._http_client is not None

        await client.close()
        assert client._http_client is None


class TestLangfuseClientCircuitBreaker:
    """Tests for circuit breaker integration."""

    def test_circuit_state_property(self) -> None:
        """Test circuit state property."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        assert client.circuit_state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self) -> None:
        """Test that circuit opens after repeated failures."""
        config = CircuitBreakerConfig(failure_threshold=2)
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
            circuit_breaker_config=config,
        )

        # Mock HTTP client to always fail
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_client.request = AsyncMock(return_value=mock_response)
        client._http_client = mock_client

        # First failure
        with pytest.raises(LangfuseClientError):
            await client._request("GET", "/test")

        # Second failure opens circuit
        with pytest.raises(LangfuseClientError):
            await client._request("GET", "/test")

        assert client.circuit_state == CircuitState.OPEN

        await client.close()


class TestLangfuseClientPromptAPI:
    """Tests for Prompt Management API."""

    @pytest.mark.asyncio
    async def test_get_prompt_success(self) -> None:
        """Test successful prompt retrieval."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"name": "test-prompt", "prompt": "Hello"}'
        mock_response.json.return_value = {"name": "test-prompt", "prompt": "Hello"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.get_prompt("test-prompt")

        assert result is not None
        assert result["name"] == "test-prompt"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self) -> None:
        """Test prompt not found returns None."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.get_prompt("nonexistent")

        assert result is None

        await client.close()


class TestLangfuseClientScoreAPI:
    """Tests for Score API."""

    @pytest.mark.asyncio
    async def test_create_score_success(self) -> None:
        """Test successful score creation."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.create_score(
            trace_id="trace-123",
            name="relevance",
            value=0.85,
        )

        assert result is True

        await client.close()


class TestLangfuseClientAnnotationQueueAPI:
    """Tests for Annotation Queue API."""

    @pytest.mark.asyncio
    async def test_add_to_annotation_queue_success(self) -> None:
        """Test successful annotation queue item addition."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.add_to_annotation_queue(
            queue_id="queue-123",
            trace_id="trace-456",
        )

        assert result is True

        await client.close()


class TestLangfuseClientDatasetAPI:
    """Tests for Dataset API."""

    @pytest.mark.asyncio
    async def test_get_dataset_success(self) -> None:
        """Test successful dataset retrieval."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"name": "test-dataset", "items": []}'
        mock_response.json.return_value = {"name": "test-dataset", "items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.get_dataset("test-dataset")

        assert result is not None
        assert result["name"] == "test-dataset"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_dataset_items_empty(self) -> None:
        """Test empty dataset items returns empty list."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.get_dataset_items("nonexistent")

        assert result == []

        await client.close()


class TestLangfuseClientExperimentAPI:
    """Tests for Experiment API."""

    @pytest.mark.asyncio
    async def test_create_experiment_success(self) -> None:
        """Test successful experiment creation."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "exp-123", "name": "test-exp"}'
        mock_response.json.return_value = {"id": "exp-123", "name": "test-exp"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.create_experiment(
            name="test-exp",
            dataset_name="test-dataset",
        )

        assert result is not None
        assert result["name"] == "test-exp"

        await client.close()

    @pytest.mark.asyncio
    async def test_log_experiment_run_success(self) -> None:
        """Test successful experiment run logging."""
        client = LangfuseClient(
            public_key="pk-test",
            secret_key="sk-test",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b"{}"
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        client._http_client = mock_client

        result = await client.log_experiment_run(
            experiment_id="exp-123",
            dataset_item_id="item-456",
            trace_id="trace-789",
            output="Test output",
            scores={"relevance": 0.9},
        )

        assert result is True

        await client.close()


class TestLangfuseClientSingleton:
    """Tests for module-level singleton."""

    def test_get_langfuse_api_client_returns_none_when_disabled(self) -> None:
        """Test singleton returns None when Langfuse is disabled."""
        import app.core.langfuse_client as module

        # Reset singleton
        module._langfuse_client = None

        with patch.dict(os.environ, {"LANGFUSE_ENABLED": "false"}, clear=True):
            client = get_langfuse_api_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_close_langfuse_client(self) -> None:
        """Test closing the singleton client."""
        import app.core.langfuse_client as module

        # Set up a mock client
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        module._langfuse_client = mock_client

        await close_langfuse_client()

        mock_client.close.assert_called_once()
        assert module._langfuse_client is None

"""Unit tests for OllamaEmbeddingService.

Tests the Ollama embedding service for local inference.
Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOllamaEmbeddingServiceInit:
    """Tests for OllamaEmbeddingService initialization."""

    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    def test_init_with_defaults(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialization with default settings."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        assert service.model == "nomic-embed-text"
        assert service.expected_dimensions == 768
        mock_ollama_embeddings.assert_called_once_with(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )

    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    def test_init_with_custom_model(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialization with custom model."""
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService(
            model="mxbai-embed-large",
            dimensions=1024,
        )

        assert service.model == "mxbai-embed-large"
        assert service.expected_dimensions == 1024


class TestOllamaEmbeddingServiceGenerate:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    async def test_generate_embedding(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test single text embedding generation."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_embeddings = AsyncMock()
        mock_embeddings.aembed_query.return_value = [0.1] * 768
        mock_ollama_embeddings.return_value = mock_embeddings

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        result = await service.generate_embedding("Hello world")

        mock_embeddings.aembed_query.assert_called_once_with("Hello world")
        assert len(result) == 768

    @pytest.mark.asyncio
    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    async def test_generate_embedding_empty_text_raises(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that empty text raises ValueError."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.generate_embedding("")

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.generate_embedding("   ")

    @pytest.mark.asyncio
    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    async def test_generate_embeddings_batch(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test batch embedding generation."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_embeddings = AsyncMock()
        mock_embeddings.aembed_documents.return_value = [
            [0.1] * 768,
            [0.2] * 768,
            [0.3] * 768,
        ]
        mock_ollama_embeddings.return_value = mock_embeddings

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        results = await service.generate_embeddings_batch(
            [
                "First text",
                "Second text",
                "Third text",
            ]
        )

        assert len(results) == 3
        assert all(len(emb) == 768 for emb, _ in results)

    @pytest.mark.asyncio
    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    async def test_generate_embeddings_batch_empty_list(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test batch embedding with empty list."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        results = await service.generate_embeddings_batch([])

        assert results == []

    @pytest.mark.asyncio
    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    async def test_generate_embeddings_batch_filters_empty(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test batch embedding filters out empty texts."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_embeddings = AsyncMock()
        mock_embeddings.aembed_documents.return_value = [
            [0.1] * 768,
        ]
        mock_ollama_embeddings.return_value = mock_embeddings

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        results = await service.generate_embeddings_batch(
            [
                "",
                "Valid text",
                "   ",
            ]
        )

        # Only one valid text
        mock_embeddings.aembed_documents.assert_called_once_with(["Valid text"])
        assert len(results) == 1


class TestOllamaEmbeddingServiceAvailability:
    """Tests for availability checking."""

    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    @patch("app.shared.services.embeddings.ollama_service.httpx")
    def test_is_available_true(
        self,
        mock_httpx: MagicMock,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test is_available returns True when server responds."""
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.get.return_value = mock_response

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        assert service.is_available is True

    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    @patch("app.shared.services.embeddings.ollama_service.httpx")
    def test_is_available_false_on_error(
        self,
        mock_httpx: MagicMock,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test is_available returns False on connection error."""
        import httpx

        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_httpx.get.side_effect = httpx.HTTPError("Connection refused")
        mock_httpx.HTTPError = httpx.HTTPError

        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        assert service.is_available is False


class TestGetEmbeddingService:
    """Tests for factory function."""

    @patch("app.shared.services.embeddings.ollama_service.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddings")
    def test_get_embedding_service_when_enabled(
        self,
        mock_ollama_embeddings: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test factory returns service when Ollama enabled."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        from app.shared.services.embeddings.ollama_service import (
            OllamaEmbeddingService,
            get_embedding_service,
        )

        service = get_embedding_service()
        assert isinstance(service, OllamaEmbeddingService)

    @patch("app.shared.services.embeddings.ollama_service.settings")
    def test_get_embedding_service_when_disabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test factory raises when Ollama disabled."""
        mock_settings.OLLAMA_ENABLED = False

        from app.shared.services.embeddings.ollama_service import get_embedding_service

        with pytest.raises(ValueError, match="Ollama is not enabled"):
            get_embedding_service()

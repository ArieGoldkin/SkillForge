"""Integration tests for Ollama LLM and embedding services.

Tests verify:
1. Ollama server connectivity when available
2. Provider factory switching based on OLLAMA_ENABLED
3. Actual LLM inference with local models
4. Actual embedding generation with local models

Issue #606: CI Cost Reduction via Local Models

Note: These tests are skipped when Ollama is not available.
Run with: pytest tests/integration/services/llm/ -v --tb=short
"""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest


def is_ollama_running() -> bool:
    """Check if Ollama server is running locally."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


# Skip marker for tests requiring Ollama
requires_ollama = pytest.mark.skipif(
    not is_ollama_running(),
    reason="Ollama server not running at localhost:11434",
)


class TestOllamaServerConnectivity:
    """Tests for Ollama server connectivity."""

    @requires_ollama
    def test_ollama_server_responds(self) -> None:
        """Test Ollama server responds to health check."""
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        assert response.status_code == 200

    @requires_ollama
    def test_ollama_lists_models(self) -> None:
        """Test Ollama returns list of available models."""
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        data = response.json()

        assert "models" in data
        # Models may or may not be pulled yet
        assert isinstance(data["models"], list)


class TestProviderFactorySwitching:
    """Tests for provider factory switching between cloud and local."""

    @patch.dict(os.environ, {"OLLAMA_ENABLED": "true"})
    @requires_ollama
    def test_factory_returns_ollama_when_enabled(self) -> None:
        """Test factory returns OllamaProvider when OLLAMA_ENABLED=true."""
        # Clear settings cache
        from app.core.config import get_settings

        get_settings.cache_clear()

        from app.shared.services.llm.factory import get_llm_provider
        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = get_llm_provider(task_type="reasoning")

        assert isinstance(provider, OllamaProvider)

    @patch.dict(os.environ, {"OLLAMA_ENABLED": "false"})
    def test_factory_returns_cloud_when_disabled(self) -> None:
        """Test factory returns cloud model when OLLAMA_ENABLED=false."""
        # Clear settings cache
        from app.core.config import get_settings

        get_settings.cache_clear()

        from app.shared.services.llm.factory import get_llm_provider
        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = get_llm_provider(task_type="reasoning")

        # Should NOT be OllamaProvider
        assert not isinstance(provider, OllamaProvider)


class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider with actual Ollama server."""

    @requires_ollama
    @pytest.mark.asyncio
    async def test_ollama_provider_invoke(self) -> None:
        """Test OllamaProvider can invoke the model."""
        from app.shared.services.llm.ollama_provider import OllamaProvider

        # Use a small/fast model for testing
        provider = OllamaProvider(model="llama3.2:1b", temperature=0.0)

        # Simple test prompt
        result = await provider.ainvoke("Say 'hello' in one word.")

        assert result is not None
        assert hasattr(result, "content")
        assert len(result.content) > 0

    @requires_ollama
    def test_ollama_provider_is_available(self) -> None:
        """Test OllamaProvider reports availability correctly."""
        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()

        assert provider.is_available is True

    @requires_ollama
    def test_ollama_for_reasoning_factory(self) -> None:
        """Test for_reasoning factory method creates provider."""
        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider.for_reasoning()

        assert provider is not None
        assert provider.model is not None

    @requires_ollama
    def test_ollama_for_coding_factory(self) -> None:
        """Test for_coding factory method creates provider."""
        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider.for_coding()

        assert provider is not None
        assert provider.model is not None


class TestOllamaEmbeddingIntegration:
    """Integration tests for OllamaEmbeddingService with actual Ollama server."""

    @requires_ollama
    @pytest.mark.asyncio
    async def test_embedding_generation(self) -> None:
        """Test OllamaEmbeddingService generates embeddings."""
        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        # Use nomic-embed-text if available, otherwise default
        service = OllamaEmbeddingService()

        embedding = await service.generate_embedding("Hello, world!")

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    @requires_ollama
    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self) -> None:
        """Test OllamaEmbeddingService generates batch embeddings."""
        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        texts = [
            "First document about Python programming",
            "Second document about machine learning",
            "Third document about web development",
        ]

        results = await service.generate_embeddings_batch(texts)

        assert len(results) == 3
        for embedding, _ in results:
            assert isinstance(embedding, list)
            assert len(embedding) > 0

    @requires_ollama
    def test_embedding_service_is_available(self) -> None:
        """Test OllamaEmbeddingService reports availability correctly."""
        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()

        assert service.is_available is True


class TestFactoryFunctions:
    """Tests for factory utility functions."""

    @requires_ollama
    def test_is_ollama_available_returns_true(self) -> None:
        """Test is_ollama_available returns True when server running."""
        with patch.dict(os.environ, {"OLLAMA_ENABLED": "true"}):
            from app.core.config import get_settings

            get_settings.cache_clear()

            from app.shared.services.llm.factory import is_ollama_available

            assert is_ollama_available() is True

    @requires_ollama
    def test_get_available_ollama_models(self) -> None:
        """Test get_available_ollama_models returns model list."""
        with patch.dict(os.environ, {"OLLAMA_ENABLED": "true"}):
            from app.core.config import get_settings

            get_settings.cache_clear()

            from app.shared.services.llm.factory import get_available_ollama_models

            models = get_available_ollama_models()

            assert isinstance(models, list)
            # List may be empty if no models pulled


@pytest.mark.integration
class TestEndToEndOllamaWorkflow:
    """End-to-end tests for Ollama in a workflow context."""

    @requires_ollama
    @pytest.mark.asyncio
    async def test_full_embedding_workflow(self) -> None:
        """Test full embedding workflow with Ollama.

        This simulates what happens when processing a document:
        1. Get embedding provider
        2. Generate embedding for document
        3. Verify embedding dimensions
        """
        with patch.dict(os.environ, {"OLLAMA_ENABLED": "true"}):
            from app.core.config import get_settings

            get_settings.cache_clear()

            from app.shared.services.llm.factory import get_embedding_provider

            provider = get_embedding_provider()

            # Simulate document embedding
            document_text = """
            This is a sample document about machine learning.
            It covers topics like neural networks, deep learning,
            and natural language processing.
            """

            embedding = await provider.generate_embedding(document_text)

            # Verify embedding properties
            assert embedding is not None
            assert len(embedding) == provider.expected_dimensions
            assert all(isinstance(x, float) for x in embedding)

    @requires_ollama
    @pytest.mark.asyncio
    async def test_llm_reasoning_workflow(self) -> None:
        """Test LLM reasoning workflow with Ollama.

        This simulates what happens when analyzing content:
        1. Get LLM provider for reasoning
        2. Invoke with analysis prompt
        3. Verify response structure
        """
        from app.shared.services.llm.ollama_provider import OllamaProvider

        # Use small model for fast testing
        provider = OllamaProvider(model="llama3.2:1b", temperature=0.0)

        analysis_prompt = """
        Analyze the following text and identify the main topic in one sentence:
        "Python is a programming language known for its simplicity and readability."
        """

        result = await provider.ainvoke(analysis_prompt)

        assert result is not None
        assert hasattr(result, "content")
        assert len(result.content) > 10  # Should have meaningful response

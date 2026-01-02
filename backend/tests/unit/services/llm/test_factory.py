"""Unit tests for LLM provider factory.

Tests the factory functions for cloud/local provider switching.
Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestGetLLMProvider:
    """Tests for get_llm_provider factory function."""

    @patch("app.core.model_factory.get_chat_model")
    def test_returns_ollama_when_enabled(
        self,
        mock_get_chat_model: MagicMock,
    ) -> None:
        """Test delegates to get_chat_model for reasoning task.

        Issue #602: get_llm_provider now delegates to get_chat_model().
        We test the delegation contract, not the internal implementation.
        """
        mock_model = MagicMock()
        mock_model.model = "deepseek-r1:70b"
        mock_get_chat_model.return_value = mock_model

        from app.shared.services.llm.factory import get_llm_provider

        result = get_llm_provider(task_type="reasoning")

        mock_get_chat_model.assert_called_once_with(task_type="reasoning")
        assert result == mock_model

    @patch("app.core.model_factory.get_chat_model")
    def test_returns_coding_model(
        self,
        mock_get_chat_model: MagicMock,
    ) -> None:
        """Test delegates to get_chat_model for coding task.

        Issue #602: get_llm_provider now delegates to get_chat_model().
        We test the delegation contract, not the internal implementation.
        """
        mock_model = MagicMock()
        mock_model.model = "qwen2.5-coder:32b"
        mock_get_chat_model.return_value = mock_model

        from app.shared.services.llm.factory import get_llm_provider

        result = get_llm_provider(task_type="coding")

        mock_get_chat_model.assert_called_once_with(task_type="coding")
        assert result == mock_model

    @patch("app.core.model_factory.get_chat_model")
    def test_returns_cloud_when_disabled(
        self,
        mock_get_chat_model: MagicMock,
    ) -> None:
        """Test delegates to get_chat_model for general task.

        Issue #602: get_llm_provider now delegates to get_chat_model().
        Cloud vs Ollama routing is handled by get_chat_model internally.
        """
        mock_model = MagicMock()
        mock_get_chat_model.return_value = mock_model

        from app.shared.services.llm.factory import get_llm_provider

        result = get_llm_provider(task_type="general")

        mock_get_chat_model.assert_called_once_with(task_type="general")
        assert result == mock_model


class TestGetEmbeddingProvider:
    """Tests for get_embedding_provider factory function."""

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.embeddings.ollama_service.OllamaEmbeddingService")
    def test_returns_ollama_when_enabled(
        self,
        mock_service_class: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns OllamaEmbeddingService when OLLAMA_ENABLED=true."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        mock_instance = MagicMock()
        mock_instance.model = "nomic-embed-text"
        mock_instance.expected_dimensions = 768
        mock_service_class.return_value = mock_instance

        from app.shared.services.llm.factory import get_embedding_provider

        result = get_embedding_provider()

        mock_service_class.assert_called_once()
        assert result.model == "nomic-embed-text"

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.embeddings.service.EmbeddingService")
    def test_returns_openai_when_disabled(
        self,
        mock_service_class: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns EmbeddingService when OLLAMA_ENABLED=false."""
        mock_settings.OLLAMA_ENABLED = False

        mock_instance = MagicMock()
        mock_instance.model = "text-embedding-3-small"
        mock_instance.expected_dimensions = 1536
        mock_service_class.return_value = mock_instance

        from app.shared.services.llm.factory import get_embedding_provider

        result = get_embedding_provider()

        mock_service_class.assert_called_once()
        assert result.model == "text-embedding-3-small"


class TestIsOllamaAvailable:
    """Tests for is_ollama_available function."""

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.llm.factory.httpx")
    def test_returns_true_when_server_responds(
        self,
        mock_httpx: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns True when Ollama server responds."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_HOST = "http://localhost:11434"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.get.return_value = mock_response

        from app.shared.services.llm.factory import is_ollama_available

        assert is_ollama_available() is True

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_false_when_disabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns False when OLLAMA_ENABLED=false."""
        mock_settings.OLLAMA_ENABLED = False

        from app.shared.services.llm.factory import is_ollama_available

        assert is_ollama_available() is False

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.llm.factory.httpx")
    def test_returns_false_on_connection_error(
        self,
        mock_httpx: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns False on connection error."""
        import httpx

        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_HOST = "http://localhost:11434"

        mock_httpx.get.side_effect = httpx.HTTPError("Connection refused")
        mock_httpx.HTTPError = httpx.HTTPError

        from app.shared.services.llm.factory import is_ollama_available

        assert is_ollama_available() is False


class TestGetAvailableOllamaModels:
    """Tests for get_available_ollama_models function."""

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.llm.factory.httpx")
    def test_returns_model_list(
        self,
        mock_httpx: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns list of models from Ollama."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_HOST = "http://localhost:11434"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "deepseek-r1:70b"},
                {"name": "qwen2.5-coder:32b"},
                {"name": "nomic-embed-text"},
            ]
        }
        mock_httpx.get.return_value = mock_response

        from app.shared.services.llm.factory import get_available_ollama_models

        models = get_available_ollama_models()

        assert "deepseek-r1:70b" in models
        assert "qwen2.5-coder:32b" in models
        assert "nomic-embed-text" in models

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_empty_when_disabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns empty list when OLLAMA_ENABLED=false."""
        mock_settings.OLLAMA_ENABLED = False

        from app.shared.services.llm.factory import get_available_ollama_models

        assert get_available_ollama_models() == []

"""Unit tests for LLM provider factory.

Tests the factory functions for cloud/local provider switching.
Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestGetLLMProvider:
    """Tests for get_llm_provider factory function."""

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_ollama_when_enabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns OllamaProvider when OLLAMA_ENABLED=true."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_MODEL_CODING = "qwen2.5-coder:32b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        with patch("app.shared.services.llm.factory.OllamaProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.model = "deepseek-r1:70b"
            mock_provider.for_reasoning.return_value = mock_instance

            from app.shared.services.llm.factory import get_llm_provider

            result = get_llm_provider(task_type="reasoning")

            mock_provider.for_reasoning.assert_called_once()
            assert result.model == "deepseek-r1:70b"

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_coding_model(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns coding model for coding task type."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_MODEL_CODING = "qwen2.5-coder:32b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        with patch("app.shared.services.llm.factory.OllamaProvider") as mock_provider:
            mock_instance = MagicMock()
            mock_instance.model = "qwen2.5-coder:32b"
            mock_provider.for_coding.return_value = mock_instance

            from app.shared.services.llm.factory import get_llm_provider

            result = get_llm_provider(task_type="coding")

            mock_provider.for_coding.assert_called_once()
            assert result.model == "qwen2.5-coder:32b"

    @patch("app.shared.services.llm.factory.settings")
    @patch("app.shared.services.llm.factory.init_chat_model")
    def test_returns_cloud_when_disabled(
        self,
        mock_init_chat_model: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns cloud model when OLLAMA_ENABLED=false."""
        mock_settings.OLLAMA_ENABLED = False
        mock_settings.LLM_MODEL = "gemini-3-flash-preview"
        mock_settings.LLM_MAX_RETRIES = 3

        mock_llm = MagicMock()
        mock_init_chat_model.return_value = mock_llm

        from app.shared.services.llm.factory import get_llm_provider

        result = get_llm_provider(task_type="reasoning")

        mock_init_chat_model.assert_called_once_with(
            "gemini-3-flash-preview",
            temperature=0.0,
            max_retries=3,
        )
        assert result == mock_llm


class TestGetEmbeddingProvider:
    """Tests for get_embedding_provider factory function."""

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_ollama_when_enabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns OllamaEmbeddingService when OLLAMA_ENABLED=true."""
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_MODEL_EMBED = "nomic-embed-text"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_EMBEDDING_DIMENSIONS = 768

        with patch("app.shared.services.llm.factory.OllamaEmbeddingService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.model = "nomic-embed-text"
            mock_instance.expected_dimensions = 768
            mock_service.return_value = mock_instance

            from app.shared.services.llm.factory import get_embedding_provider

            result = get_embedding_provider()

            mock_service.assert_called_once()
            assert result.model == "nomic-embed-text"

    @patch("app.shared.services.llm.factory.settings")
    def test_returns_openai_when_disabled(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns EmbeddingService when OLLAMA_ENABLED=false."""
        mock_settings.OLLAMA_ENABLED = False

        with patch("app.shared.services.llm.factory.EmbeddingService") as mock_service:
            mock_instance = MagicMock()
            mock_instance.model = "text-embedding-3-small"
            mock_instance.expected_dimensions = 1536
            mock_service.return_value = mock_instance

            from app.shared.services.llm.factory import get_embedding_provider

            result = get_embedding_provider()

            mock_service.assert_called_once()
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

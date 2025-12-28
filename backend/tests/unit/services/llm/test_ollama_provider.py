"""Unit tests for OllamaProvider.

Tests the Ollama LLM provider for local inference.
Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_init_with_defaults(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialization with default settings."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()

        assert provider.model == "deepseek-r1:70b"
        mock_chat_ollama.assert_called_once_with(
            model="deepseek-r1:70b",
            base_url="http://localhost:11434",
            temperature=0.0,
            num_ctx=32768,
            timeout=300.0,
            keep_alive="5m",
        )

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_init_with_custom_model(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test initialization with custom model."""
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider(
            model="llama3.3:70b",
            temperature=0.5,
            keep_alive="10m",
        )

        assert provider.model == "llama3.3:70b"
        mock_chat_ollama.assert_called_once()
        call_kwargs = mock_chat_ollama.call_args.kwargs
        assert call_kwargs["model"] == "llama3.3:70b"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["keep_alive"] == "10m"


class TestOllamaProviderClassMethods:
    """Tests for OllamaProvider class methods."""

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_for_reasoning(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test for_reasoning factory method."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider.for_reasoning()

        assert provider.model == "deepseek-r1:70b"
        call_kwargs = mock_chat_ollama.call_args.kwargs
        assert call_kwargs["keep_alive"] == "10m"  # Longer for reasoning

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_for_coding(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test for_coding factory method."""
        mock_settings.OLLAMA_MODEL_CODING = "qwen2.5-coder:32b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider.for_coding()

        assert provider.model == "qwen2.5-coder:32b"
        call_kwargs = mock_chat_ollama.call_args.kwargs
        assert call_kwargs["keep_alive"] == "5m"


class TestOllamaProviderMethods:
    """Tests for OllamaProvider methods."""

    @pytest.mark.asyncio
    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    async def test_ainvoke(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test async invocation."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="Test response")
        mock_chat_ollama.return_value = mock_llm

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        result = await provider.ainvoke("Test prompt")

        mock_llm.ainvoke.assert_called_once_with("Test prompt")
        assert result.content == "Test response"

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_bind_tools(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test tool binding."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = MagicMock()
        mock_chat_ollama.return_value = mock_llm

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        tools = [{"type": "function", "name": "test_tool"}]
        provider.bind_tools(tools)

        mock_llm.bind_tools.assert_called_once_with(tools)

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    def test_with_structured_output(
        self,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test structured output configuration."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()
        mock_chat_ollama.return_value = mock_llm

        from pydantic import BaseModel

        class TestSchema(BaseModel):
            field: str

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        provider.with_structured_output(TestSchema)

        mock_llm.with_structured_output.assert_called_once_with(TestSchema)


class TestOllamaProviderAvailability:
    """Tests for availability checking."""

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    @patch("app.shared.services.llm.ollama_provider.httpx")
    def test_is_available_true(
        self,
        mock_httpx: MagicMock,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test is_available returns True when server responds."""
        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.get.return_value = mock_response

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        assert provider.is_available is True

    @patch("app.shared.services.llm.ollama_provider.settings")
    @patch("app.shared.services.llm.ollama_provider.ChatOllama")
    @patch("app.shared.services.llm.ollama_provider.httpx")
    def test_is_available_false_on_error(
        self,
        mock_httpx: MagicMock,
        mock_chat_ollama: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test is_available returns False on connection error."""
        import httpx

        mock_settings.OLLAMA_MODEL_REASONING = "deepseek-r1:70b"
        mock_settings.OLLAMA_HOST = "http://localhost:11434"
        mock_settings.OLLAMA_NUM_CTX = 32768
        mock_settings.OLLAMA_TIMEOUT = 300.0

        mock_httpx.get.side_effect = httpx.HTTPError("Connection refused")
        mock_httpx.HTTPError = httpx.HTTPError

        from app.shared.services.llm.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        assert provider.is_available is False

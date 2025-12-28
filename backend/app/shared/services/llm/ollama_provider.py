"""Ollama provider for local LLM inference.

This module provides a LangChain-compatible LLM provider that uses Ollama
for local model inference. Designed for CI/CD cost reduction on self-hosted
runners with Apple Silicon (M4 Max 256GB).

Uses langchain-ollama v1.0.1 with:
- ChatOllama for chat completions with tool calling
- OllamaEmbeddings for text embeddings
- Async streaming support
- keep_alive for model caching between calls

Usage:
    ```python
    from app.shared.services.llm import OllamaProvider

    # For reasoning tasks (G-Eval, synthesis)
    provider = OllamaProvider.for_reasoning()
    response = await provider.ainvoke("Explain quantum computing")

    # For coding tasks (agent analysis, reranking)
    provider = OllamaProvider.for_coding()
    response = await provider.ainvoke("Analyze this code pattern")

    # With tool calling
    provider = OllamaProvider.for_coding()
    with_tools = provider.bind_tools([get_weather])
    response = await with_tools.ainvoke("What's the weather?")
    ```

Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import httpx
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

logger = get_logger(__name__)


class OllamaProvider:
    """Provider for local LLM inference via Ollama.

    This provider wraps LangChain's ChatOllama to provide a consistent interface
    for local model inference. Supports tool calling, streaming, and reasoning modes.

    Key features (langchain-ollama v1.0.1):
    - Tool calling via bind_tools()
    - Structured output via with_structured_output()
    - Async streaming with astream()
    - Model caching via keep_alive parameter

    Attributes:
        model: Ollama model identifier (e.g., "deepseek-r1:70b")
        llm: Underlying ChatOllama instance

    Example:
        >>> provider = OllamaProvider(model="qwen2.5-coder:32b")
        >>> result = await provider.ainvoke("Write a Python function")
        >>> print(result.content)

    """

    def __init__(
        self,
        model: str | None = None,
        *,
        temperature: float = 0.0,
        num_ctx: int | None = None,
        timeout: float | None = None,
        keep_alive: str = "5m",
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Ollama model identifier. Defaults to settings.OLLAMA_MODEL_REASONING.
            temperature: Sampling temperature (0.0 = deterministic).
            num_ctx: Context window size. Defaults to settings.OLLAMA_NUM_CTX.
            timeout: Request timeout. Defaults to settings.OLLAMA_TIMEOUT.
            keep_alive: How long to keep model loaded in memory (e.g., "5m", "1h").
                       Critical for CI performance - avoids cold starts between calls.

        """
        self.model = model or settings.OLLAMA_MODEL_REASONING
        self._temperature = temperature
        self._num_ctx = num_ctx or settings.OLLAMA_NUM_CTX
        self._timeout = timeout or settings.OLLAMA_TIMEOUT
        self._keep_alive = keep_alive

        self.llm: ChatOllama = ChatOllama(
            model=self.model,
            base_url=settings.OLLAMA_HOST,
            temperature=temperature,
            num_ctx=self._num_ctx,
            timeout=self._timeout,
            keep_alive=keep_alive,
        )

        logger.info(
            "ollama_provider_initialized",
            model=self.model,
            host=settings.OLLAMA_HOST,
            num_ctx=self._num_ctx,
            timeout=self._timeout,
            keep_alive=keep_alive,
        )

    async def ainvoke(
        self,
        prompt: str | list[BaseMessage],
        **kwargs: Any,
    ) -> Any:
        """Invoke the model asynchronously.

        Args:
            prompt: Text prompt or list of messages
            **kwargs: Additional arguments passed to ChatOllama

        Returns:
            Model response (AIMessage)

        """
        return await self.llm.ainvoke(prompt, **kwargs)

    async def astream(
        self,
        prompt: str | list[BaseMessage],
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """Stream responses from the model.

        Args:
            prompt: Text prompt or list of messages
            **kwargs: Additional arguments passed to ChatOllama

        Yields:
            Streaming chunks from the model (AIMessageChunk)

        """
        async for chunk in self.llm.astream(prompt, **kwargs):
            yield chunk

    def bind_tools(self, tools: list[Any]) -> BaseChatModel:
        """Bind tools for function calling.

        Ollama supports tool calling for models like:
        - qwen2.5-coder (recommended for coding tools)
        - llama3.3 (good general purpose)
        - mistral (strong tool use)

        Args:
            tools: List of tools (Pydantic models, functions, or tool schemas)

        Returns:
            ChatOllama with tools bound

        Example:
            >>> from pydantic import BaseModel
            >>> class GetWeather(BaseModel):
            ...     location: str
            >>> provider = OllamaProvider.for_coding()
            >>> with_tools = provider.bind_tools([GetWeather])
            >>> response = await with_tools.ainvoke("Weather in Tokyo?")
            >>> print(response.tool_calls)

        """
        return self.llm.bind_tools(tools)

    def with_structured_output(self, schema: type) -> BaseChatModel:
        """Configure model to output structured data.

        Uses Ollama's JSON mode with schema validation.

        Args:
            schema: Pydantic model or JSON schema for output structure

        Returns:
            ChatOllama configured for structured output

        Example:
            >>> from pydantic import BaseModel
            >>> class Summary(BaseModel):
            ...     title: str
            ...     points: list[str]
            >>> provider = OllamaProvider.for_reasoning()
            >>> structured = provider.with_structured_output(Summary)
            >>> result = await structured.ainvoke("Summarize: ...")

        """
        return self.llm.with_structured_output(schema)

    @classmethod
    def for_reasoning(cls) -> OllamaProvider:
        """Create provider optimized for reasoning tasks.

        Uses DeepSeek R1 70B for:
        - G-Eval quality evaluation
        - Complex reasoning and synthesis
        - Multi-step analysis

        DeepSeek R1 uses chain-of-thought internally, matching GPT-4/o1 level.

        Returns:
            OllamaProvider configured for reasoning

        """
        return cls(
            model=settings.OLLAMA_MODEL_REASONING,
            temperature=0.0,
            keep_alive="10m",  # Longer keep_alive for reasoning models
        )

    @classmethod
    def for_coding(cls) -> OllamaProvider:
        """Create provider optimized for coding tasks.

        Uses Qwen 2.5 Coder 32B for:
        - Code generation and analysis
        - Agent tasks and tool calling
        - Reranking and classification

        Qwen 2.5 Coder scores 73.7% on Aider benchmark (comparable to GPT-4o).

        Returns:
            OllamaProvider configured for coding

        """
        return cls(
            model=settings.OLLAMA_MODEL_CODING,
            temperature=0.0,
            keep_alive="5m",
        )

    @property
    def is_available(self) -> bool:
        """Check if Ollama server is available.

        Returns:
            True if Ollama is reachable and responding

        """
        try:
            response = httpx.get(
                f"{settings.OLLAMA_HOST}/api/tags",
                timeout=5.0,
            )
            return response.status_code == HTTPStatus.OK
        except httpx.HTTPError:
            return False

    def has_model(self, model: str) -> bool:
        """Check if a specific model is available.

        Args:
            model: Model identifier to check

        Returns:
            True if model is pulled and available

        """
        try:
            response = httpx.get(
                f"{settings.OLLAMA_HOST}/api/tags",
                timeout=5.0,
            )
            if response.status_code != HTTPStatus.OK:
                return False
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return any(model in m for m in models)
        except httpx.HTTPError:
            return False


def get_ollama_llm(
    model: str | None = None,
    task_type: str = "reasoning",
) -> ChatOllama:
    """Get a ChatOllama instance for the specified task type.

    This is a convenience function for getting the right Ollama model
    based on the task type. Used by the provider factory.

    Args:
        model: Override model identifier
        task_type: One of "reasoning", "coding", "general"

    Returns:
        Configured ChatOllama instance

    """
    if model is None:
        if task_type == "coding":
            model = settings.OLLAMA_MODEL_CODING
        else:
            model = settings.OLLAMA_MODEL_REASONING

    return ChatOllama(
        model=model,
        base_url=settings.OLLAMA_HOST,
        temperature=0.0,
        num_ctx=settings.OLLAMA_NUM_CTX,
        timeout=settings.OLLAMA_TIMEOUT,
        keep_alive="5m",
    )

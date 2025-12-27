"""Tests for Langfuse Prompt Observation Linking (Issue #564).

This module tests the prompt manager's get_prompt_with_langfuse_client() method
which returns both compiled prompt content and a TextPromptClient object for
proper Langfuse prompt-to-generation linkage.

Key functionality tested:
- L1 cache hits return (content, None) - no Langfuse client needed
- L2 cache hits return (content, None) - no Langfuse client needed
- L3 Langfuse fetches return (content, TextPromptClient) - linkable to generations
- Hardcoded fallbacks return (content, None) - no Langfuse client needed
- Variable substitution works correctly with client objects
- Client objects contain version and config metadata
"""

from unittest.mock import MagicMock

import pytest
from langfuse.model import TextPromptClient

from app.shared.services.prompts.prompt_manager import PromptManager


class TestPromptManagerWithLangfuseClient:
    """Test get_prompt_with_langfuse_client() method (Issue #564).

    This method is the core implementation for Issue #564 which enables proper
    Langfuse prompt-to-generation linkage by returning the TextPromptClient object
    when fetching from Langfuse (L3 cache).
    """

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = MagicMock()
        mock.get.return_value = None
        mock.setex.return_value = True
        return mock

    @pytest.fixture
    def mock_langfuse(self):
        """Mock Langfuse client."""
        mock = MagicMock()
        mock.get_prompt.return_value = None
        return mock

    @pytest.fixture
    def manager(self, mock_redis, mock_langfuse):
        """Create PromptManager with mocked dependencies."""
        manager = PromptManager(
            l1_cache_size=10,
            l1_ttl_seconds=300,
            l2_ttl_seconds=900,
            enable_langfuse=True,
            enable_redis=True,
        )
        # Override lazy-loaded clients with mocks
        manager._redis_client = mock_redis
        manager._langfuse_client = mock_langfuse
        return manager

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_l1_cache_hit_returns_content_and_none(self, manager):
        """L1 cache hit should return (content, None) - no client object."""
        # Pre-populate L1 cache
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "Hello {name}")

        content, client = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={"name": "World"},
            label="production",
        )

        assert content == "Hello World"
        assert client is None  # Cache hit = no client

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_l2_cache_hit_returns_content_and_none(self, manager, mock_redis):
        """L2 Redis cache hit should return (content, None) - no client object."""
        mock_redis.get.return_value = b"Cached {greeting}"

        content, client = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={"greeting": "Hello"},
            label="production",
        )

        assert content == "Cached Hello"
        assert client is None  # Cache hit = no client

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_langfuse_fetch_returns_content_and_client(self, manager, mock_langfuse):
        """L3 Langfuse fetch should return (content, TextPromptClient) - linkable."""
        # Mock Langfuse prompt object
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Hello {name}"
        mock_prompt.version = 42
        mock_prompt.config = {}
        mock_prompt.name = "test-prompt"
        mock_langfuse.get_prompt.return_value = mock_prompt

        content, client = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={"name": "World"},
            label="production",
        )

        assert content == "Hello World"
        assert client is not None  # Langfuse fetch = client provided
        assert client.name == "test-prompt"
        assert client.version == 42

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hardcoded_fallback_returns_content_and_none(self, manager, mock_langfuse):
        """Hardcoded fallback should return (content, None) - no client."""
        # Langfuse returns None (not found)
        mock_langfuse.get_prompt.return_value = None

        content, client = await manager.get_prompt_with_langfuse_client(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- agent1"},
            label="production",
        )

        assert "Analyze content and select relevant agents" in content
        assert client is None  # Hardcoded = no client

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_langfuse_empty_prompt_falls_back_with_none_client(self, manager, mock_langfuse):
        """Empty Langfuse prompt should fallback to hardcoded, return (content, None)."""
        # Mock Langfuse to return empty prompt
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = ""  # Empty prompt
        mock_prompt.version = 42
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        content, client = await manager.get_prompt_with_langfuse_client(
            name="analysis-supervisor-routing",
            variables={"agent_list": "test"},
            label="production",
        )

        # Should fallback to hardcoded
        assert "Analyze content and select relevant agents" in content
        assert client is None  # Fallback = no client

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_prompt_not_found_raises_error(self, manager, mock_langfuse):
        """Unknown prompt should raise ValueError."""
        mock_langfuse.get_prompt.return_value = None

        with pytest.raises(ValueError, match="Prompt 'unknown-prompt' not found"):
            await manager.get_prompt_with_langfuse_client(
                name="unknown-prompt",
                variables={},
                label="production",
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_variable_substitution_works_with_client(self, manager, mock_langfuse):
        """Variable substitution should work correctly with Langfuse client."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Agent: {agent_name}, Task: {task}"
        mock_prompt.version = 1
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        content, client = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={"agent_name": "TechComparator", "task": "Analyze frameworks"},
            label="production",
        )

        assert content == "Agent: TechComparator, Task: Analyze frameworks"
        assert client is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_client_object_contains_version_info(self, manager, mock_langfuse):
        """Returned client object should contain version and config info."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Test prompt"
        mock_prompt.version = 123
        mock_prompt.config = {"temperature": 0.7, "max_tokens": 1000}
        mock_prompt.name = "test-prompt"
        mock_prompt.label = "production"
        mock_langfuse.get_prompt.return_value = mock_prompt

        content, client = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert client is not None
        assert client.version == 123
        assert client.config == {"temperature": 0.7, "max_tokens": 1000}
        assert client.name == "test-prompt"
        assert client.label == "production"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_return_type_is_tuple(self, manager):
        """Method should return a tuple of (str, TextPromptClient | None)."""
        # Pre-populate cache for quick test
        key = "prompt:test:production"
        manager.l1_cache.set(key, "Test")

        result = await manager.get_prompt_with_langfuse_client(
            name="test",
            variables={},
            label="production",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert result[1] is None or isinstance(result[1], TextPromptClient)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cache_population_after_langfuse_fetch(self, manager, mock_redis, mock_langfuse):
        """Langfuse fetch should populate both L1 and L2 caches with content only."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Cached content"
        mock_prompt.version = 5
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        # First call - fetch from Langfuse
        content1, client1 = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert content1 == "Cached content"
        assert client1 is not None  # Langfuse provided client
        assert client1.version == 5

        # L1 cache should be populated with content string
        l1_cached = manager.l1_cache.get("prompt:test-prompt:production")
        assert l1_cached == "Cached content"

        # L2 Redis should be populated with content bytes
        mock_redis.setex.assert_called_once()

        # Second call - hit L1 cache
        content2, client2 = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert content2 == "Cached content"
        assert client2 is None  # Cache hit = no client

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_missing_variable_raises_key_error(self, manager, mock_langfuse):
        """Missing required variable should raise KeyError."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Hello {name}, you are {age} years old"
        mock_prompt.version = 1
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        with pytest.raises(KeyError):
            await manager.get_prompt_with_langfuse_client(
                name="test-prompt",
                variables={"name": "Alice"},  # Missing 'age'
                label="production",
            )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_from_langfuse_includes_client_object(self, manager, mock_langfuse):
        """_fetch_from_langfuse should return dict with langfuse_client key."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Test"
        mock_prompt.version = 10
        mock_prompt.config = {"model": "gpt-4"}
        mock_langfuse.get_prompt.return_value = mock_prompt

        # Call the internal method directly
        result = await manager._fetch_from_langfuse("test-prompt", "production")

        assert result is not None
        assert "prompt" in result
        assert "version" in result
        assert "config" in result
        assert "langfuse_client" in result  # Key for Issue #564

        # Verify the client object is the mock prompt
        assert result["langfuse_client"] is mock_prompt
        assert result["langfuse_client"].version == 10

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_prompt_client_has_required_attributes(self, manager, mock_langfuse):
        """TextPromptClient should have name, version, prompt attributes."""
        mock_prompt = MagicMock(spec=TextPromptClient)
        mock_prompt.prompt = "Test content"
        mock_prompt.version = 99
        mock_prompt.config = {}
        mock_prompt.name = "my-prompt"
        mock_langfuse.get_prompt.return_value = mock_prompt

        content, client = await manager.get_prompt_with_langfuse_client(
            name="my-prompt",
            variables={},
            label="production",
        )

        assert client is not None
        # Verify required attributes exist
        assert hasattr(client, "name")
        assert hasattr(client, "version")
        assert hasattr(client, "prompt")

        # Verify values
        assert client.name == "my-prompt"
        assert client.version == 99
        assert client.prompt == "Test content"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_different_labels_return_separate_clients(self, manager, mock_langfuse):
        """Fetching same prompt with different labels should return separate clients."""
        mock_prompt_prod = MagicMock(spec=TextPromptClient)
        mock_prompt_prod.prompt = "Production version"
        mock_prompt_prod.version = 10
        mock_prompt_prod.config = {}
        mock_prompt_prod.label = "production"

        mock_prompt_staging = MagicMock(spec=TextPromptClient)
        mock_prompt_staging.prompt = "Staging version"
        mock_prompt_staging.version = 11
        mock_prompt_staging.config = {}
        mock_prompt_staging.label = "staging"

        mock_langfuse.get_prompt.side_effect = [mock_prompt_prod, mock_prompt_staging]

        # Fetch production label
        content_prod, client_prod = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={},
            label="production",
        )

        # Fetch staging label
        content_staging, client_staging = await manager.get_prompt_with_langfuse_client(
            name="test-prompt",
            variables={},
            label="staging",
        )

        assert content_prod == "Production version"
        assert client_prod is not None
        assert client_prod.version == 10

        assert content_staging == "Staging version"
        assert client_staging is not None
        assert client_staging.version == 11

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_langfuse_disabled_returns_none_client(self, manager):
        """When Langfuse is disabled, should return (hardcoded_content, None)."""
        # Create manager with Langfuse disabled
        manager_no_langfuse = PromptManager(
            enable_langfuse=False,
            enable_redis=False,
        )

        content, client = await manager_no_langfuse.get_prompt_with_langfuse_client(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- test"},
            label="production",
        )

        assert "Analyze content and select relevant agents" in content
        assert client is None  # Langfuse disabled = always None

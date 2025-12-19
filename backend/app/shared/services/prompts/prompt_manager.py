"""Langfuse Prompt Management with multi-level caching.

Issue #379: Centralized prompt management with:
- L1 Cache: In-memory LRU (5 min TTL, 100 prompts)
- L2 Cache: Redis (15 min TTL, shared across workers)
- L3 Source: Langfuse API (~100-200ms)
- Fallback: Hardcoded prompts (<1ms, offline operation)

Architecture:
    Application → PromptManager.get_prompt() → L1 Cache (LRU)
                                              ↓ MISS
                                          → L2 Cache (Redis)
                                              ↓ MISS
                                          → L3 Source (Langfuse API)
                                              ↓ FAILURE
                                          → Fallback (Hardcoded)

Benefits:
- Version control without deploys
- A/B testing infrastructure
- Prompt usage analytics
- Cost optimization through caching
"""

from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.langfuse_config import get_langfuse_client
from app.core.logging import get_logger
from app.shared.services.cache.redis_connection import create_redis_client

logger = get_logger(__name__)

# Hardcoded prompts for fallback (embedded from supervisor_config.py)
HARDCODED_PROMPTS: dict[str, str] = {
    "analysis-supervisor-routing": """Analyze content and select relevant agents. Output JSON:
{{"agents": ["agent1", "agent2"], "reasoning": "brief", "confidence": 0.0-1.0}}

Agents:
{agent_list}

AGENT SELECTION GUIDELINES:
1. MINIMUM 3 AGENTS REQUIRED for all content (ensures diverse perspectives)
2. SHORT content (<1000 words): 3-4 agents covering primary topics
3. MEDIUM content (1000-3000 words): 4-6 agents covering main themes
4. COMPREHENSIVE content (>3000 words): 6-8 agents for thorough analysis

IMPORTANT: Never select fewer than 3 agents. Even simple content benefits from:
- implementation_planner (how to use)
- At least one perspective agent (security_auditor, performance_analyst, or tech_comparator)
- At least one context agent (dependency_mapper, trend_validator, or integration_feasibility)

TUTORIAL ANALYSIS (important):
- Tutorials are COMPREHENSIVE by nature - analyze from multiple angles
- Always include: implementation_planner + at least 2 of: security_auditor,
  performance_analyst, dependency_mapper
- Framework tutorials: Add tech_comparator for ecosystem context
- Minimum 3-4 agents for medium/large tutorials to ensure thorough coverage

CONTENT TYPE TRIGGERS:
- "tutorial", "guide", "introduction" → Include implementation_planner, dependency_mapper
- "security", "auth", "vulnerability" → Include security_auditor
- "performance", "fast", "async", "benchmark" → Include performance_analyst
- "vs", "comparison", "alternative" → Include tech_comparator
- Framework names (FastAPI, React, Django) → Include tech_comparator, performance_analyst

CODE PATTERN TRIGGERS (REQUIRED):
- Import statements (import X, from X import Y) → dependency_mapper REQUIRED
- Package files (requirements.txt, pyproject.toml, package.json) → dependency_mapper REQUIRED
- Installation commands (pip install, npm install) → dependency_mapper REQUIRED
- Framework tutorials with code examples → dependency_mapper REQUIRED + ecosystem mapping

Select based on: content type, keywords, complexity, analysis needs.

Examples:
- Quick tip/snippet → {{"agents": ["implementation_planner", "dependency_mapper", "security_auditor"],
  "reasoning": "Even simple content needs implementation guidance, dependency context, and security basics",
  "confidence": 0.85}}
- Framework tutorial → {{
    "agents": [
        "implementation_planner", "security_auditor", "performance_analyst", "dependency_mapper"
    ],
  "reasoning": "Comprehensive tutorial needs multi-perspective analysis",
  "confidence": 0.85}}
- Security deep-dive → {{"agents": ["security_auditor", "trend_validator", "code_quality_critic"],
  "reasoning": "Security focus with code patterns and trend validation",
  "confidence": 0.95}}
- Architecture comparison → {{
    "agents": [
        "tech_comparator", "performance_analyst", "integration_feasibility",
        "trend_validator", "dependency_mapper"
    ],
  "reasoning": "Architecture decisions need comprehensive technical analysis",
  "confidence": 0.8}}
- API quickstart → {{"agents": ["implementation_planner", "security_auditor"],
  "reasoning": "API setup needs implementation and security basics",
  "confidence": 0.9}}""",
}


class LRUCache:
    """Thread-safe LRU cache with TTL support.

    Simpler than functools.lru_cache because we need TTL and custom serialization.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)

        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, tuple[str, datetime]] = OrderedDict()

    def get(self, key: str) -> str | None:
        """Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/missing

        """
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        age = (datetime.now(UTC) - timestamp).total_seconds()
        if age > self.ttl_seconds:
            del self.cache[key]
            return None

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: str) -> None:
        """Set cached value with current timestamp.

        Args:
            key: Cache key
            value: Value to cache

        """
        # Remove if exists (to update timestamp)
        if key in self.cache:
            del self.cache[key]

        # Add to end
        self.cache[key] = (value, datetime.now(UTC))

        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()


class PromptManager:
    """Manages prompts with multi-level caching and Langfuse integration.

    Features:
    - L1 Cache: In-memory LRU (fast, per-worker)
    - L2 Cache: Redis (shared across workers)
    - L3 Source: Langfuse API (source of truth)
    - Fallback: Hardcoded prompts (offline operation)

    Example:
        >>> manager = PromptManager()
        >>> prompt = await manager.get_prompt(
        ...     name="analysis-supervisor-routing",
        ...     variables={"agent_list": agents_str},
        ...     label="production",
        ... )

    """

    def __init__(
        self,
        l1_cache_size: int = 100,
        l1_ttl_seconds: int = 300,
        l2_ttl_seconds: int = 900,
        enable_langfuse: bool = True,
        enable_redis: bool = True,
    ):
        """Initialize PromptManager.

        Args:
            l1_cache_size: Maximum items in L1 LRU cache
            l1_ttl_seconds: L1 cache TTL in seconds (default: 5 minutes)
            l2_ttl_seconds: L2 Redis cache TTL in seconds (default: 15 minutes)
            enable_langfuse: Enable Langfuse API fetching
            enable_redis: Enable Redis L2 cache

        """
        self.settings = get_settings()
        self.enable_langfuse = enable_langfuse
        self.enable_redis = enable_redis
        self.l2_ttl_seconds = l2_ttl_seconds

        # L1 Cache: In-memory LRU
        self.l1_cache = LRUCache(max_size=l1_cache_size, ttl_seconds=l1_ttl_seconds)

        # L2 Cache: Redis (lazy initialization)
        self._redis_client = None

        # L3 Source: Langfuse client (lazy initialization)
        self._langfuse_client = None

        logger.info(
            "prompt_manager_initialized",
            l1_cache_size=l1_cache_size,
            l1_ttl_seconds=l1_ttl_seconds,
            l2_ttl_seconds=l2_ttl_seconds,
            enable_langfuse=enable_langfuse,
            enable_redis=enable_redis,
        )

    @property
    def redis_client(self):
        """Lazy-load Redis client."""
        if not self.enable_redis:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = create_redis_client()
                logger.debug("prompt_manager_redis_connected")
            except Exception as e:  # noqa: BLE001 - Graceful degradation for cache
                logger.warning(
                    "prompt_manager_redis_failed",
                    error=str(e),
                    exc_info=True,
                )
                self._redis_client = None

        return self._redis_client

    @property
    def langfuse_client(self):
        """Lazy-load Langfuse client."""
        if not self.enable_langfuse:
            return None

        if self._langfuse_client is None:
            self._langfuse_client = get_langfuse_client()

        return self._langfuse_client

    def _build_cache_key(self, name: str, label: str) -> str:
        """Build cache key from prompt name and label.

        Args:
            name: Prompt name (e.g., "analysis-supervisor-routing")
            label: Prompt label (e.g., "production")

        Returns:
            Cache key string

        """
        return f"prompt:{name}:{label}"

    async def _get_from_l1_cache(self, name: str, label: str) -> str | None:
        """Get prompt from L1 in-memory cache.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Cached prompt or None if miss

        """
        key = self._build_cache_key(name, label)
        prompt = self.l1_cache.get(key)

        if prompt:
            logger.debug("prompt_cache_l1_hit", name=name, label=label)
            return prompt

        logger.debug("prompt_cache_l1_miss", name=name, label=label)
        return None

    async def _get_from_l2_cache(self, name: str, label: str) -> str | None:
        """Get prompt from L2 Redis cache.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Cached prompt or None if miss

        """
        if not self.redis_client:
            return None

        key = self._build_cache_key(name, label)

        try:
            cached = self.redis_client.get(key)
            if cached:
                logger.debug("prompt_cache_l2_hit", name=name, label=label)
                return cached.decode("utf-8")

            logger.debug("prompt_cache_l2_miss", name=name, label=label)
            return None

        except Exception as e:  # noqa: BLE001 - Graceful degradation for cache
            logger.warning(
                "prompt_cache_l2_error",
                name=name,
                label=label,
                error=str(e),
                exc_info=True,
            )
            return None

    async def _fetch_from_langfuse(self, name: str, label: str) -> dict[str, Any] | None:
        """Fetch prompt from Langfuse API.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Prompt object with 'prompt' and 'version' keys, or None if not found

        """
        if not self.langfuse_client:
            logger.debug(
                "prompt_langfuse_disabled",
                name=name,
                label=label,
            )
            return None

        try:
            # Fetch prompt from Langfuse
            prompt_obj = self.langfuse_client.get_prompt(
                name=name,
                label=label,
            )

            if not prompt_obj:
                logger.warning(
                    "prompt_langfuse_not_found",
                    name=name,
                    label=label,
                )
                return None

            logger.info(
                "prompt_langfuse_fetched",
                name=name,
                label=label,
                version=prompt_obj.version,
            )

            return {
                "prompt": prompt_obj.prompt,
                "version": prompt_obj.version,
                "config": prompt_obj.config,
            }

        except Exception as e:
            logger.error(
                "prompt_langfuse_fetch_failed",
                name=name,
                label=label,
                error=str(e),
                exc_info=True,
            )
            return None

    def _get_hardcoded_prompt(self, name: str) -> str | None:
        """Get hardcoded fallback prompt.

        Args:
            name: Prompt name

        Returns:
            Hardcoded prompt or None if not found

        """
        prompt = HARDCODED_PROMPTS.get(name)

        if prompt:
            logger.info(
                "prompt_fallback_to_hardcoded",
                name=name,
                message="Using hardcoded prompt as fallback",
            )
        else:
            logger.error(
                "prompt_not_found",
                name=name,
                message="Prompt not found in Langfuse or hardcoded fallbacks",
            )

        return prompt

    async def _cache_prompt(self, name: str, label: str, prompt: str) -> None:
        """Cache prompt in both L1 and L2 caches.

        Args:
            name: Prompt name
            label: Prompt label
            prompt: Prompt content to cache

        """
        key = self._build_cache_key(name, label)

        # Cache in L1 (in-memory)
        self.l1_cache.set(key, prompt)

        # Cache in L2 (Redis)
        if self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    self.l2_ttl_seconds,
                    prompt.encode("utf-8"),
                )
                logger.debug("prompt_cached_l2", name=name, label=label)
            except Exception as e:  # noqa: BLE001 - Graceful degradation for cache
                logger.warning(
                    "prompt_cache_l2_set_failed",
                    name=name,
                    label=label,
                    error=str(e),
                    exc_info=True,
                )

    def _compile_prompt(self, prompt: str, variables: dict[str, Any]) -> str:
        """Compile prompt with variable substitution.

        Args:
            prompt: Prompt template
            variables: Variables to substitute

        Returns:
            Compiled prompt string

        """
        try:
            return prompt.format(**variables)
        except KeyError as e:
            logger.error(
                "prompt_compilation_failed",
                error=f"Missing variable: {e}",
                variables_provided=list(variables.keys()),
                exc_info=True,
            )
            raise

    async def get_prompt(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        label: str = "production",
    ) -> str:
        r"""Get and compile prompt with multi-level caching.

        Fetching strategy:
        1. Try L1 cache (in-memory LRU)
        2. Try L2 cache (Redis)
        3. Try L3 source (Langfuse API)
        4. Fallback to hardcoded prompts

        Args:
            name: Prompt name (e.g., "analysis-supervisor-routing")
            variables: Variables for prompt compilation
            label: Prompt label/version (default: "production")

        Returns:
            Compiled prompt string

        Raises:
            ValueError: If prompt not found in any source
            KeyError: If required variables are missing

        Example:
            >>> prompt = await manager.get_prompt(
            ...     name="analysis-supervisor-routing",
            ...     variables={"agent_list": "- agent1\n- agent2"},
            ...     label="production",
            ... )

        """
        variables = variables or {}

        # L1 Cache: In-memory LRU
        cached_prompt = await self._get_from_l1_cache(name, label)
        if cached_prompt:
            return self._compile_prompt(cached_prompt, variables)

        # L2 Cache: Redis
        cached_prompt = await self._get_from_l2_cache(name, label)
        if cached_prompt:
            # Populate L1 cache
            self.l1_cache.set(self._build_cache_key(name, label), cached_prompt)
            return self._compile_prompt(cached_prompt, variables)

        # L3 Source: Langfuse API
        prompt_obj = await self._fetch_from_langfuse(name, label)
        if prompt_obj:
            prompt_content = prompt_obj["prompt"]
            # Cache in both L1 and L2
            await self._cache_prompt(name, label, prompt_content)
            return self._compile_prompt(prompt_content, variables)

        # Fallback: Hardcoded prompts
        hardcoded_prompt = self._get_hardcoded_prompt(name)
        if hardcoded_prompt:
            # Don't cache hardcoded prompts (they're already in memory)
            return self._compile_prompt(hardcoded_prompt, variables)

        # Not found anywhere
        msg = f"Prompt '{name}' not found in Langfuse or hardcoded fallbacks"
        logger.error("prompt_not_found", name=name, label=label)
        raise ValueError(msg)

    async def get_prompt_metadata(
        self,
        name: str,
        label: str = "production",
    ) -> dict[str, Any]:
        """Get prompt metadata for trace attribution.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Dictionary with prompt metadata (version, label, source)

        """
        # Try to fetch from Langfuse for version info
        prompt_obj = await self._fetch_from_langfuse(name, label)

        if prompt_obj:
            return {
                "prompt_name": name,
                "prompt_version": prompt_obj["version"],
                "prompt_label": label,
                "prompt_source": "langfuse",
            }

        # Fallback to hardcoded
        return {
            "prompt_name": name,
            "prompt_version": "hardcoded",
            "prompt_label": label,
            "prompt_source": "hardcoded",
        }

    def clear_caches(self) -> None:
        """Clear all caches (useful for testing)."""
        self.l1_cache.clear()

        if self.redis_client:
            try:
                # Clear all prompt keys
                for key in self.redis_client.scan_iter("prompt:*"):
                    self.redis_client.delete(key)
                logger.info("prompt_cache_cleared")
            except Exception as e:  # noqa: BLE001 - Graceful degradation for cache
                logger.warning(
                    "prompt_cache_clear_failed",
                    error=str(e),
                    exc_info=True,
                )


# Global singleton instance
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """Get global PromptManager singleton.

    Returns:
        PromptManager instance

    """
    global _prompt_manager  # noqa: PLW0603

    if _prompt_manager is None:
        settings = get_settings()

        # Read configuration from environment
        enable_langfuse = getattr(settings, "LANGFUSE_PROMPTS_ENABLED", False)
        enable_redis = getattr(settings, "LANGFUSE_PROMPTS_REDIS_ENABLED", True)
        l1_ttl = getattr(settings, "LANGFUSE_PROMPTS_L1_TTL", 300)
        l2_ttl = getattr(settings, "LANGFUSE_PROMPTS_L2_TTL", 900)

        _prompt_manager = PromptManager(
            l1_cache_size=100,
            l1_ttl_seconds=l1_ttl,
            l2_ttl_seconds=l2_ttl,
            enable_langfuse=enable_langfuse,
            enable_redis=enable_redis,
        )

    return _prompt_manager

"""Langfuse Prompt Management with multi-level caching.

Issue #379: Centralized prompt management with:
- L1 Cache: In-memory LRU (5 min TTL, 100 prompts)
- L2 Cache: Redis (15 min TTL, shared across workers)
- L3 Source: Langfuse API (~100-200ms)
- L4 Fallback: Jinja2 templates (<1ms, offline operation)

Issue #414: Migrated hardcoded prompts to Jinja2 templates for:
- Template inheritance and shared macros
- Separation of concerns (prompts vs Python code)
- Easier editing and review by non-developers
- Version control friendly (clean diffs)

Architecture:
    Application → PromptManager.get_prompt() → L1 Cache (LRU)
                                              ↓ MISS
                                          → L2 Cache (Redis)
                                              ↓ MISS
                                          → L3 Source (Langfuse API)
                                              ↓ FAILURE
                                          → L4 Fallback (Jinja2 Templates)

Benefits:
- Version control without deploys
- A/B testing infrastructure
- Prompt usage analytics
- Cost optimization through caching
- Clean separation of prompts from code
"""

import re
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from jinja2 import TemplateNotFound
from langfuse.model import TextPromptClient

from app.core.config import get_settings
from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.shared.services.cache.redis_connection import create_redis_client
from app.shared.services.prompts.template_loader import TemplatePaths, render_template

logger = get_logger(__name__)

# Issue #414: Mapping from prompt names to Jinja2 template paths
# Replaces the 1600-line HARDCODED_PROMPTS dictionary with clean template references
TEMPLATE_MAPPING: dict[str, str] = {
    # Supervisor
    "analysis-supervisor-routing": TemplatePaths.SUPERVISOR_ROUTING,
    # Tier 1 Agents (Universal - run on ALL content types)
    "analysis-agent-key-insights": TemplatePaths.AGENT_KEY_INSIGHTS,
    "analysis-agent-pros-cons": TemplatePaths.AGENT_PROS_CONS,
    "analysis-agent-audience-fit": TemplatePaths.AGENT_AUDIENCE_FIT,
    "analysis-agent-actionable": TemplatePaths.AGENT_ACTIONABLE,
    # Tier 2 Agents (Validation - Standard+ depth)
    "analysis-agent-implementation-planner": TemplatePaths.AGENT_IMPLEMENTATION_PLANNER,
    "analysis-agent-security-auditor": TemplatePaths.AGENT_SECURITY_AUDITOR,
    "analysis-agent-performance-analyst": TemplatePaths.AGENT_PERFORMANCE_ANALYST,
    "analysis-agent-tech-comparator": TemplatePaths.AGENT_TECH_COMPARATOR,
    "analysis-agent-dependency-mapper": TemplatePaths.AGENT_DEPENDENCY_MAPPER,
    "analysis-agent-trend-validator": TemplatePaths.AGENT_TREND_VALIDATOR,
    "analysis-agent-integration-feasibility": TemplatePaths.AGENT_INTEGRATION_FEASIBILITY,
    "analysis-agent-code-quality-critic": TemplatePaths.AGENT_CODE_QUALITY_CRITIC,
    "analysis-agent-fact-validator": TemplatePaths.AGENT_FACT_VALIDATOR,
    # Tier 3 Agents (Research - Deep Dive with memory/tools)
    "analysis-agent-deep-researcher": TemplatePaths.AGENT_DEEP_RESEARCHER,
    "analysis-agent-community-pulse": TemplatePaths.AGENT_COMMUNITY_PULSE,
    "analysis-agent-knowledge-curator": TemplatePaths.AGENT_KNOWLEDGE_CURATOR,
    "analysis-agent-learning-path-advisor": TemplatePaths.AGENT_LEARNING_PATH_ADVISOR,
    # Archive (Dead agents - kept for reference, may be revived)
    "analysis-agent-research-analyst": TemplatePaths.AGENT_RESEARCH_ANALYST,
    "analysis-agent-freshness-checker": TemplatePaths.AGENT_FRESHNESS_CHECKER,
    "analysis-agent-alternatives-finder": TemplatePaths.AGENT_ALTERNATIVES_FINDER,
    "analysis-agent-source-credibility": TemplatePaths.AGENT_SOURCE_CREDIBILITY,
    # Evaluators (G-Eval LLM-as-Judge)
    "evaluator-quality-relevance": TemplatePaths.EVALUATOR_RELEVANCE,
    "evaluator-quality-depth": TemplatePaths.EVALUATOR_DEPTH,
    "evaluator-quality-accuracy": TemplatePaths.EVALUATOR_ACCURACY,
    "evaluator-quality-coherence": TemplatePaths.EVALUATOR_COHERENCE,
    "evaluator-quality-overall": TemplatePaths.EVALUATOR_OVERALL,
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
    - L4 Fallback: Jinja2 templates (offline operation)

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
        """Lazy-load Langfuse SDK client via service."""
        if not self.enable_langfuse:
            return None

        if self._langfuse_client is None:
            service = get_langfuse_service()
            self._langfuse_client = service.sdk_client if service else None

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
        """Get prompt from L2 Redis cache with retry logic.

        Implements exponential backoff retry (3 attempts) for Redis connection errors.
        Retry delays: 100ms, 200ms, 400ms.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Cached prompt or None if miss/error

        """
        if not self.redis_client:
            return None

        import asyncio

        import redis

        key = self._build_cache_key(name, label)
        max_retries = 3
        base_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                cached = self.redis_client.get(key)
                if cached:
                    logger.debug("prompt_cache_l2_hit", name=name, label=label)
                    return cached.decode("utf-8")

                logger.debug("prompt_cache_l2_miss", name=name, label=label)
                return None

            except redis.ConnectionError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "prompt_cache_l2_connection_error_retry",
                        name=name,
                        label=label,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "prompt_cache_l2_connection_error_exhausted",
                        name=name,
                        label=label,
                        error=str(e),
                        exc_info=True,
                    )
                    return None  # Graceful degradation to L3

            except Exception as e:  # noqa: BLE001 - Graceful degradation for cache
                logger.warning(
                    "prompt_cache_l2_error",
                    name=name,
                    label=label,
                    error=str(e),
                    exc_info=True,
                )
                return None

        # All retries exhausted without success
        return None

    async def _fetch_from_langfuse(self, name: str, label: str) -> dict[str, Any] | None:
        """Fetch prompt from Langfuse API.

        Issue #564: Modified to include TextPromptClient in return dict for prompt linkage.

        Args:
            name: Prompt name
            label: Prompt label

        Returns:
            Prompt object with 'prompt', 'version', 'config', and 'langfuse_client' keys,
            or None if not found

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
                "langfuse_client": prompt_obj,  # Issue #564: Store TextPromptClient for linkage
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

    def _get_template_prompt(self, name: str, variables: dict[str, Any]) -> str | None:
        """Get prompt from Jinja2 template fallback.

        Issue #414: Replaces _get_hardcoded_prompt with Jinja2 template loading.
        Issue #414 (refactor): Uses TRUE Jinja2 best practices:
        - Templates use {{ variable }} syntax (not Python {variable})
        - Variables passed at render time via render_template(**variables)
        - No separate Python .format() step needed

        Templates are stored in templates/ directory and mapped via TEMPLATE_MAPPING.

        Args:
            name: Prompt name (e.g., "analysis-agent-key-insights")
            variables: Variables to pass to Jinja2 template

        Returns:
            Rendered template content with variables substituted or None if not found

        """
        template_path = TEMPLATE_MAPPING.get(name)

        if not template_path:
            logger.error(
                "prompt_template_not_mapped",
                name=name,
                message=f"No template mapping found for prompt '{name}'",
            )
            return None

        try:
            # TRUE Jinja2: Pass variables directly to render_template()
            # Templates use {{ var }} syntax, not Python {var} syntax
            prompt = render_template(template_path, **variables)

            logger.info(
                "prompt_fallback_to_template",
                name=name,
                template_path=template_path,
                variables_count=len(variables),
                message="Using Jinja2 template as fallback",
            )

            return prompt

        except TemplateNotFound:
            logger.warning(
                "prompt_template_not_found",
                name=name,
                template_path=template_path,
                message=f"Template file not found: {template_path}",
            )
            return None

        except Exception as e:
            logger.exception(
                "prompt_template_render_failed",
                name=name,
                template_path=template_path,
                error=str(e),
            )
            return None

    async def _cache_prompt(self, name: str, label: str, prompt: str) -> None:
        """Cache prompt in both L1 and L2 caches.

        Args:
            name: Prompt name
            label: Prompt label
            prompt: Prompt content to cache

        """
        key = self._build_cache_key(name, label)

        self.l1_cache.set(key, prompt)

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

        Issue #586: Uses selective regex substitution instead of str.format()
        to avoid conflicts with JSON examples in Langfuse prompts.

        str.format() interprets ALL {word} as variables, which breaks when
        prompts contain JSON like {"immediate_actions": [...]}. This method
        only substitutes variables that are explicitly provided.

        Args:
            prompt: Prompt template
            variables: Variables to substitute

        Returns:
            Compiled prompt string

        """
        if not variables:
            return prompt

        def replace_var(match: re.Match[str]) -> str:
            """Replace only if variable is in provided dict."""
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            # Leave unmatched braces as-is (could be JSON)
            return match.group(0)

        # Match {word} patterns where word is alphanumeric + underscore
        # This matches template variables but not JSON keys with colons/quotes
        pattern = r"\{(\w+)\}"
        result = re.sub(pattern, replace_var, prompt)

        # Log if some provided variables weren't used (potential typo)
        used_vars = set(re.findall(r"\{(\w+)\}", prompt))
        unused_vars = set(variables.keys()) - used_vars
        if unused_vars:
            logger.debug(
                "prompt_compilation_unused_variables",
                unused=list(unused_vars),
                prompt_vars=list(used_vars),
            )

        return result

    async def get_prompt_with_langfuse_client(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        label: str = "production",
    ) -> tuple[str, TextPromptClient | None]:
        r"""Get prompt content AND Langfuse client object for observation linking.

        Issue #564: New method that returns both compiled prompt and TextPromptClient
        for proper Langfuse prompt-to-generation linkage.

        Fetching strategy:
        1. Try L1 cache (in-memory LRU) → returns (content, None)
        2. Try L2 cache (Redis) → returns (content, None)
        3. Try L3 source (Langfuse API) → returns (content, TextPromptClient)
        4. Fallback to Jinja2 templates → returns (content, None)

        Args:
            name: Prompt name (e.g., "analysis-supervisor-routing")
            variables: Variables for prompt compilation
            label: Prompt label/version (default: "production")

        Returns:
            Tuple of (compiled_prompt_string, langfuse_client_or_none)
            - L1/L2 cache hits return (content, None) - no client object
            - L3 Langfuse fetch returns (content, TextPromptClient) - linkable
            - L4 template fallback returns (content, None) - no client object

        Raises:
            ValueError: If prompt not found in any source
            KeyError: If required variables are missing

        Example:
            >>> prompt, langfuse_client = await manager.get_prompt_with_langfuse_client(
            ...     name="analysis-supervisor-routing",
            ...     variables={"agent_list": "- agent1\n- agent2"},
            ...     label="production",
            ... )
            >>> # If langfuse_client is not None, can link to generation span

        """
        variables = variables or {}

        # L1 Cache: In-memory LRU
        cached_prompt = await self._get_from_l1_cache(name, label)
        if cached_prompt:
            return self._compile_prompt(cached_prompt, variables), None

        # L2 Cache: Redis
        cached_prompt = await self._get_from_l2_cache(name, label)
        if cached_prompt:
            # Populate L1 cache
            self.l1_cache.set(self._build_cache_key(name, label), cached_prompt)
            return self._compile_prompt(cached_prompt, variables), None

        # L3 Source: Langfuse API - CRITICAL PATH FOR LINKAGE
        prompt_obj = await self._fetch_from_langfuse(name, label)
        if prompt_obj:
            prompt_content = prompt_obj["prompt"]
            langfuse_client = prompt_obj["langfuse_client"]  # TextPromptClient object

            # Only use Langfuse prompt if it has content
            if prompt_content and prompt_content.strip():
                # Cache content only (not client object)
                await self._cache_prompt(name, label, prompt_content)

                # Return BOTH compiled content and client object
                return self._compile_prompt(prompt_content, variables), langfuse_client

            logger.warning(
                "prompt_langfuse_empty",
                name=name,
                label=label,
                message="Langfuse prompt is empty, falling back to template",
            )

        # L4 Fallback: Jinja2 templates
        # TRUE Jinja2: Variables already substituted by render_template()
        # No need for _compile_prompt() - that's only for Langfuse prompts with {var} syntax
        template_prompt = self._get_template_prompt(name, variables)
        if template_prompt:
            # Don't cache template prompts (they're already fast to load)
            return template_prompt, None

        # Not found anywhere
        msg = f"Prompt '{name}' not found in Langfuse or templates"
        logger.error("prompt_not_found", name=name, label=label)
        raise ValueError(msg)

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
        4. Fallback to Jinja2 templates

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
            # Only use Langfuse prompt if it has content
            if prompt_content and prompt_content.strip():
                # Cache in both L1 and L2
                await self._cache_prompt(name, label, prompt_content)
                return self._compile_prompt(prompt_content, variables)

            logger.warning(
                "prompt_langfuse_empty",
                name=name,
                label=label,
                message="Langfuse prompt is empty, falling back to template",
            )

        # L4 Fallback: Jinja2 templates
        # TRUE Jinja2: Variables already substituted by render_template()
        # No need for _compile_prompt() - that's only for Langfuse prompts with {var} syntax
        template_prompt = self._get_template_prompt(name, variables)
        if template_prompt:
            # Don't cache template prompts (they're already fast to load)
            return template_prompt

        # Not found anywhere
        msg = f"Prompt '{name}' not found in Langfuse or templates"
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

        # Check if template exists
        template_path = TEMPLATE_MAPPING.get(name)
        if template_path:
            return {
                "prompt_name": name,
                "prompt_version": "template",
                "prompt_label": label,
                "prompt_source": "jinja2_template",
                "template_path": template_path,
            }

        # Unknown prompt
        return {
            "prompt_name": name,
            "prompt_version": "unknown",
            "prompt_label": label,
            "prompt_source": "not_found",
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

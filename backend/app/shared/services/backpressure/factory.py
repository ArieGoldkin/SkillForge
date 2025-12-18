"""Factory functions for creating backpressure components from settings.

Provides singleton instances of rate limiter, error tracker, and batch sizer
configured from application settings.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.shared.services.backpressure.batch_sizer import AdaptiveBatchSizer
from app.shared.services.backpressure.error_tracker import ErrorTracker
from app.shared.services.backpressure.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from app.core.config import Settings


def create_rate_limiter(settings: Settings, name: str = "embedding") -> RateLimiter:
    """Create a rate limiter from settings.

    Args:
        settings: Application settings.
        name: Identifier for logging.

    Returns:
        Configured RateLimiter instance.

    """
    return RateLimiter(
        tokens_per_minute=settings.RATE_LIMIT_TOKENS_PER_MINUTE,
        burst_capacity=settings.RATE_LIMIT_BURST_CAPACITY,
        name=name,
    )


def create_error_tracker(settings: Settings, name: str = "embedding") -> ErrorTracker:
    """Create an error tracker from settings.

    Args:
        settings: Application settings.
        name: Identifier for logging.

    Returns:
        Configured ErrorTracker instance.

    """
    return ErrorTracker(
        window_seconds=settings.ERROR_RATE_WINDOW_SECONDS,
        threshold_percent=settings.ERROR_RATE_THRESHOLD_PERCENT,
        name=name,
    )


def create_batch_sizer(settings: Settings, name: str = "embedding") -> AdaptiveBatchSizer:
    """Create an adaptive batch sizer from settings.

    Args:
        settings: Application settings.
        name: Identifier for logging.

    Returns:
        Configured AdaptiveBatchSizer instance.

    """
    return AdaptiveBatchSizer(
        initial_size=settings.BATCH_SIZE_INITIAL,
        min_size=settings.BATCH_SIZE_MIN,
        max_size=settings.BATCH_SIZE_MAX,
        decrease_factor_429=settings.BATCH_DECREASE_FACTOR_429,
        decrease_factor_5xx=settings.BATCH_DECREASE_FACTOR_5XX,
        increase_factor=settings.BATCH_INCREASE_FACTOR,
        cooldown_seconds=settings.BATCH_COOLDOWN_SECONDS,
        healthy_window_seconds=settings.BATCH_HEALTHY_WINDOW_SECONDS,
        name=name,
    )


@lru_cache(maxsize=1)
def get_embedding_rate_limiter() -> RateLimiter:
    """Get the singleton rate limiter for embedding API."""
    from app.core.config import get_settings

    return create_rate_limiter(get_settings(), name="embedding")


@lru_cache(maxsize=1)
def get_embedding_error_tracker() -> ErrorTracker:
    """Get the singleton error tracker for embedding API."""
    from app.core.config import get_settings

    return create_error_tracker(get_settings(), name="embedding")


@lru_cache(maxsize=1)
def get_embedding_batch_sizer() -> AdaptiveBatchSizer:
    """Get the singleton batch sizer for embedding API."""
    from app.core.config import get_settings

    return create_batch_sizer(get_settings(), name="embedding")

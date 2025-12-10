"""Backpressure and adaptive control services.

This module provides resilience mechanisms for handling API rate limits,
errors, and dynamic batch size optimization.
"""

from app.services.backpressure.batch_sizer import AdaptiveBatchSizer
from app.services.backpressure.error_tracker import ErrorTracker, ErrorType
from app.services.backpressure.factory import (
    create_batch_sizer,
    create_error_tracker,
    create_rate_limiter,
    get_embedding_batch_sizer,
    get_embedding_error_tracker,
    get_embedding_rate_limiter,
)
from app.services.backpressure.rate_limiter import RateLimiter

__all__ = [
    "AdaptiveBatchSizer",
    "ErrorTracker",
    "ErrorType",
    "RateLimiter",
    "create_batch_sizer",
    "create_error_tracker",
    "create_rate_limiter",
    "get_embedding_batch_sizer",
    "get_embedding_error_tracker",
    "get_embedding_rate_limiter",
]

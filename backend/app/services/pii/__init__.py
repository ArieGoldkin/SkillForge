"""PII detection service for SkillForge.

Provides regex-based PII detection with configurable sensitivity levels.
NEVER stores or logs actual PII values - only type flags and counts.
"""

from app.services.pii.detector import PIIDetector, get_pii_detector
from app.services.pii.types import (
    PIIAction,
    PIIMatch,
    PIIResult,
    PIIType,
    SensitivityLevel,
)

__all__ = [
    "PIIAction",
    "PIIDetector",
    "PIIMatch",
    "PIIResult",
    "PIIType",
    "SensitivityLevel",
    "get_pii_detector",
]

"""PII detection types and enums.

Type definitions for PII screening system.
IMPORTANT: These types never store actual PII values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE_US = "phone_us"
    PHONE_INTL = "phone_intl"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"  # noqa: S105 - PII pattern name, not actual token
    STRIPE_KEY = "stripe_key"
    NAME = "name"  # Presidio only (future)
    ORGANIZATION = "organization"  # Presidio only (future)


class SensitivityLevel(str, Enum):
    """Sensitivity levels for PII detection.

    Controls which patterns are enabled at different security levels.
    """

    LOW = "low"  # email only
    MEDIUM = "medium"  # email, phone, SSN, credit card
    HIGH = "high"  # all regex + API keys
    MAXIMUM = "maximum"  # all + Presidio NER (future)


class PIIAction(str, Enum):
    """Action to take when PII is detected."""

    FLAG = "flag"  # Continue with flag in metadata
    REJECT = "reject"  # Fail the workflow


@dataclass
class PIIMatch:
    """A single PII match.

    CRITICAL: Does NOT store the actual PII value.
    Only metadata for debugging and counting.
    """

    pii_type: PIIType
    start: int  # Character offset (for debugging, not value)
    end: int
    # Note: NO value field - we never store the actual PII


@dataclass
class PIIResult:
    """Result of PII detection scan.

    Contains flags and counts only - no actual PII values.
    """

    has_pii: bool
    types: list[PIIType] = field(default_factory=list)
    match_count: int = 0
    matches_by_type: dict[PIIType, int] = field(default_factory=dict)

    @property
    def should_reject(self) -> bool:
        """Check if content should be rejected based on config.

        Returns:
            True if PII was detected and action is REJECT.

        """
        if not self.has_pii:
            return False

        # Avoid circular import by importing at runtime
        from app.core.config import settings

        # Get PII action from settings (defaults to FLAG)
        pii_action = getattr(settings, "PII_ACTION", "flag")
        return pii_action == PIIAction.REJECT.value

    def to_metadata(self) -> dict:
        """Convert to metadata dict for storage.

        Returns:
            Dictionary with pii_flag, pii_types, pii_count.
            NEVER includes actual PII values.

        """
        return {
            "pii_flag": self.has_pii,
            "pii_types": [t.value for t in self.types],
            "pii_count": self.match_count,
        }

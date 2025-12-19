"""PII Anonymizer for evaluation dataset ingestion.

This module provides PII anonymization capabilities for text content
extracted from Langfuse traces and GitHub issues. It builds on the
existing PII detection patterns while adding replacement functionality.

SECURITY:
- Replacements are deterministic within a single text (same PII = same placeholder)
- Original values are NEVER logged or stored
- Allowlist prevents over-anonymization of safe patterns

Example:
    >>> anonymizer = PIIAnonymizer()
    >>> result = anonymizer.anonymize("Contact john@example.com for help")
    >>> print(result.text)
    "Contact [EMAIL_1] for help"

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.shared.services.pii.patterns import PII_PATTERNS, SENSITIVITY_PATTERNS
from app.shared.services.pii.types import PIIType, SensitivityLevel

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = get_logger(__name__)


# Allowlist patterns - these should NOT be anonymized
# These are safe example/test values commonly used in documentation
ALLOWLISTED_DOMAINS: frozenset[str] = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "test.com",
        "localhost",
        "localhost.localdomain",
    }
)

ALLOWLISTED_EMAILS: frozenset[str] = frozenset(
    {
        "user@example.com",
        "admin@example.com",
        "test@example.com",
        "noreply@example.com",
        "support@example.com",
        "info@example.com",
        "hello@example.com",
        "contact@example.com",
    }
)

# Private IP ranges that are safe to keep
PRIVATE_IP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^127\."),  # Loopback
    re.compile(r"^10\."),  # Class A private
    re.compile(r"^192\.168\."),  # Class C private
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\."),  # Class B private
    re.compile(r"^0\.0\.0\.0$"),  # All interfaces
)

# Placeholder format for each PII type
PLACEHOLDER_FORMATS: dict[str, str] = {
    "email": "[EMAIL_{n}]",
    "phone_us": "[PHONE_{n}]",
    "phone_intl": "[PHONE_{n}]",
    "ssn": "[SSN_{n}]",
    "credit_card": "[CARD_{n}]",
    "ipv4": "[IP_{n}]",
    "ipv6": "[IP_{n}]",
    "aws_key": "[AWS_KEY_{n}]",
    "github_token": "[GH_TOKEN_{n}]",
    "stripe_key": "[STRIPE_KEY_{n}]",
}


@dataclass
class PIIReplacement:
    """Record of a single PII replacement.

    Attributes:
        pii_type: Type of PII that was replaced
        start: Original start position in text
        end: Original end position in text
        placeholder: The replacement string used (e.g., "[EMAIL_1]")

    Note:
        Does NOT store the original value for security.

    """

    pii_type: PIIType
    start: int
    end: int
    placeholder: str


@dataclass
class AnonymizedResult:
    """Result of PII anonymization.

    Attributes:
        text: The anonymized text with PII replaced by placeholders
        replacements: List of replacements made (without original values)
        pii_count: Total number of PII instances replaced
        skipped_allowlisted: Number of matches skipped due to allowlist

    """

    text: str
    replacements: list[PIIReplacement] = field(default_factory=list)
    pii_count: int = 0
    skipped_allowlisted: int = 0

    @property
    def has_pii(self) -> bool:
        """Check if any PII was found and replaced."""
        return self.pii_count > 0

    @property
    def types_found(self) -> list[PIIType]:
        """Get unique PII types that were replaced."""
        return list({r.pii_type for r in self.replacements})

    def to_metadata(self) -> dict:
        """Convert to metadata dict for provenance tracking.

        Returns:
            Dictionary with anonymization metadata.
            NEVER includes original PII values.

        """
        return {
            "pii_anonymized": self.has_pii,
            "pii_count": self.pii_count,
            "pii_types": [t.value for t in self.types_found],
            "skipped_allowlisted": self.skipped_allowlisted,
        }


class PIIAnonymizer:
    """Anonymizes PII in text by replacing with placeholders.

    Uses regex patterns from the existing PII detection system,
    with an allowlist to preserve safe example values.

    Example:
        >>> anonymizer = PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)
        >>> result = anonymizer.anonymize("Email: john.doe@company.com")
        >>> print(result.text)
        "Email: [EMAIL_1]"
        >>> print(result.pii_count)
        1

    """

    def __init__(
        self,
        sensitivity: SensitivityLevel = SensitivityLevel.HIGH,
        custom_allowlist: set[str] | None = None,
    ) -> None:
        """Initialize the anonymizer.

        Args:
            sensitivity: Detection sensitivity level (default: HIGH)
            custom_allowlist: Additional patterns to skip anonymization

        """
        self.sensitivity = sensitivity

        # Build combined allowlist
        self.allowlisted_emails = ALLOWLISTED_EMAILS.copy()
        self.allowlisted_domains = ALLOWLISTED_DOMAINS.copy()
        if custom_allowlist:
            self.allowlisted_emails = self.allowlisted_emails | custom_allowlist

        # Get active patterns based on sensitivity
        pattern_names = SENSITIVITY_PATTERNS.get(sensitivity.value, [])
        self.active_patterns: dict[str, re.Pattern[str]] = {
            name: PII_PATTERNS[name] for name in pattern_names if name in PII_PATTERNS
        }

        logger.debug(
            "pii_anonymizer_initialized",
            sensitivity=sensitivity.value,
            active_patterns=list(self.active_patterns.keys()),
        )

    def _is_allowlisted(self, match_value: str, pattern_name: str) -> bool:
        """Check if a match should be skipped due to allowlist.

        Args:
            match_value: The matched PII value
            pattern_name: Name of the pattern that matched

        Returns:
            True if the match should be preserved (not anonymized)

        """
        value_lower = match_value.lower()

        # Check email allowlist
        if pattern_name == "email":
            # Check exact email match
            if value_lower in self.allowlisted_emails:
                return True
            # Check if domain is allowlisted
            if "@" in value_lower:
                domain = value_lower.split("@")[1]
                if domain in self.allowlisted_domains:
                    return True

        # Check IP allowlist (private ranges)
        if pattern_name == "ipv4":
            for private_pattern in PRIVATE_IP_PATTERNS:
                if private_pattern.match(match_value):
                    return True

        return False

    def _find_all_matches(self, text: str) -> Iterator[tuple[str, re.Match[str]]]:
        """Find all PII matches in text, sorted by position.

        Args:
            text: Text to scan for PII

        Yields:
            Tuples of (pattern_name, match_object) sorted by start position

        """
        all_matches: list[tuple[str, re.Match[str]]] = []

        for pattern_name, pattern in self.active_patterns.items():
            for match in pattern.finditer(text):
                all_matches.append((pattern_name, match))

        # Sort by start position (for proper replacement)
        all_matches.sort(key=lambda x: x[1].start())
        yield from all_matches

    def anonymize(self, text: str) -> AnonymizedResult:
        """Anonymize PII in text by replacing with placeholders.

        Args:
            text: Text to anonymize

        Returns:
            AnonymizedResult with anonymized text and replacement metadata

        """
        if not text or not text.strip():
            return AnonymizedResult(text=text)

        replacements: list[PIIReplacement] = []
        skipped_count = 0

        # Track unique values to use consistent placeholders
        value_to_placeholder: dict[str, str] = {}
        type_counters: dict[str, int] = {}

        # Collect all matches first
        matches_to_replace: list[tuple[str, re.Match[str]]] = []
        for pattern_name, match in self._find_all_matches(text):
            match_value = match.group()

            if self._is_allowlisted(match_value, pattern_name):
                skipped_count += 1
                continue

            matches_to_replace.append((pattern_name, match))

        # Process matches in reverse order (to preserve positions)
        result_text = text
        for pattern_name, match in reversed(matches_to_replace):
            match_value = match.group()

            # Get or create placeholder for this value
            if match_value in value_to_placeholder:
                placeholder = value_to_placeholder[match_value]
            else:
                # Create new placeholder
                type_counters[pattern_name] = type_counters.get(pattern_name, 0) + 1
                placeholder_format = PLACEHOLDER_FORMATS.get(pattern_name, "[PII_{n}]")
                placeholder = placeholder_format.format(n=type_counters[pattern_name])
                value_to_placeholder[match_value] = placeholder

            # Record replacement (without original value)
            pii_type = PIIType(pattern_name)
            replacements.append(
                PIIReplacement(
                    pii_type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    placeholder=placeholder,
                )
            )

            # Replace in text
            result_text = result_text[: match.start()] + placeholder + result_text[match.end() :]

        # Reverse replacements list to match original order
        replacements.reverse()

        result = AnonymizedResult(
            text=result_text,
            replacements=replacements,
            pii_count=len(replacements),
            skipped_allowlisted=skipped_count,
        )

        if result.has_pii:
            logger.info(
                "pii_anonymized",
                pii_count=result.pii_count,
                pii_types=[t.value for t in result.types_found],
                skipped=skipped_count,
                # SECURITY: Never log original values
            )

        return result

    def anonymize_batch(self, texts: list[str]) -> list[AnonymizedResult]:
        """Anonymize PII in multiple texts.

        Args:
            texts: List of texts to anonymize

        Returns:
            List of AnonymizedResult objects

        """
        return [self.anonymize(text) for text in texts]

    def anonymize_dict(
        self,
        data: dict,
        fields: list[str] | None = None,
    ) -> tuple[dict, list[PIIReplacement]]:
        """Anonymize PII in specific fields of a dictionary.

        Useful for anonymizing structured data like issue bodies or trace outputs.

        Args:
            data: Dictionary containing text fields to anonymize
            fields: List of field names to anonymize (default: all string fields)

        Returns:
            Tuple of (anonymized_dict, all_replacements)

        """
        result = data.copy()
        all_replacements: list[PIIReplacement] = []

        # Determine which fields to process
        if fields is None:
            fields = [k for k, v in data.items() if isinstance(v, str)]

        for field_name in fields:
            if field_name in result and isinstance(result[field_name], str):
                anonymized = self.anonymize(result[field_name])
                result[field_name] = anonymized.text
                all_replacements.extend(anonymized.replacements)

        return result, all_replacements


# Singleton cache for convenience
_anonymizer_cache: dict[SensitivityLevel, PIIAnonymizer] = {}


def get_anonymizer(
    sensitivity: SensitivityLevel = SensitivityLevel.HIGH,
) -> PIIAnonymizer:
    """Get a PII anonymizer instance (cached by sensitivity level).

    Args:
        sensitivity: Detection sensitivity level

    Returns:
        PIIAnonymizer instance

    """
    if sensitivity not in _anonymizer_cache:
        _anonymizer_cache[sensitivity] = PIIAnonymizer(sensitivity=sensitivity)
    return _anonymizer_cache[sensitivity]

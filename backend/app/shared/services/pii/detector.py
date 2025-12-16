"""PII Detection service for pre-embedding content screening.

This service scans text for PII patterns and returns metadata flags
WITHOUT storing or logging the actual PII values.

SECURITY CRITICAL:
- Never logs actual PII values
- Only returns type flags and counts
- No raw PII stored in any data structure
"""

from __future__ import annotations

import structlog

from app.core.config import settings
from app.shared.services.pii.patterns import (
    PATTERN_TO_TYPE,
    PII_PATTERNS,
    SENSITIVITY_PATTERNS,
)
from app.shared.services.pii.types import PIIMatch, PIIResult, PIIType, SensitivityLevel

logger = structlog.get_logger(__name__)


class PIIDetector:
    """Detects PII in text using regex patterns.

    IMPORTANT: This detector never stores or logs actual PII values.
    It only returns type flags and counts for metadata.

    Attributes:
        sensitivity: Detection sensitivity level.
        enabled: Whether detection is enabled.
        active_patterns: Compiled regex patterns for this sensitivity level.

    """

    def __init__(
        self,
        sensitivity: SensitivityLevel | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Initialize the PII detector.

        Args:
            sensitivity: Detection sensitivity level. Defaults to config setting.
            enabled: Whether detection is enabled. Defaults to config setting.

        """
        # Load from config if not provided
        self.sensitivity = sensitivity or SensitivityLevel(
            getattr(settings, "PII_SENSITIVITY_LEVEL", "medium")
        )
        self.enabled = (
            enabled if enabled is not None else getattr(settings, "PII_SCREENING_ENABLED", False)
        )

        # Get active patterns based on sensitivity level
        pattern_names = SENSITIVITY_PATTERNS.get(self.sensitivity.value, [])
        self.active_patterns = {
            name: PII_PATTERNS[name] for name in pattern_names if name in PII_PATTERNS
        }

        logger.info(
            "pii_detector_initialized",
            enabled=self.enabled,
            sensitivity=self.sensitivity.value,
            pattern_count=len(self.active_patterns),
        )

    def scan(self, text: str) -> PIIResult:
        """Scan text for PII patterns.

        Performs regex-based pattern matching to detect common PII types.
        SECURITY: Does NOT store or log actual PII values.

        Args:
            text: The text content to scan.

        Returns:
            PIIResult with detection flags (no actual PII values).

        """
        # If disabled, return empty result
        if not self.enabled:
            return PIIResult(has_pii=False)

        if not text or not text.strip():
            return PIIResult(has_pii=False)

        matches: list[PIIMatch] = []
        types_found: set[PIIType] = set()
        matches_by_type: dict[PIIType, int] = {}

        # Scan with all active patterns
        for pattern_name, pattern in self.active_patterns.items():
            pii_type = PIIType(PATTERN_TO_TYPE[pattern_name])

            for match in pattern.finditer(text):
                # Store match metadata, NOT the value
                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        start=match.start(),
                        end=match.end(),
                    )
                )
                types_found.add(pii_type)
                matches_by_type[pii_type] = matches_by_type.get(pii_type, 0) + 1

        has_pii = len(matches) > 0

        # Log detection event WITHOUT values (only types and count)
        if has_pii:
            logger.warning(
                "pii_detected",
                pii_types=[t.value for t in types_found],
                match_count=len(matches),
                sensitivity=self.sensitivity.value,
                # SECURITY: NEVER log actual values or offsets that could reveal content
            )

        # Return PIIResult
        return PIIResult(
            has_pii=has_pii,
            types=list(types_found),
            match_count=len(matches),
            matches_by_type=matches_by_type,
        )

    def scan_chunks(
        self,
        chunks: list[str],
    ) -> tuple[list[PIIResult], int, int]:
        """Batch scan multiple chunks for PII.

        Args:
            chunks: List of text chunks to scan.

        Returns:
            Tuple of (results, clean_count, flagged_count).

        """
        results = [self.scan(chunk) for chunk in chunks]
        flagged_count = sum(1 for r in results if r.has_pii)
        clean_count = len(results) - flagged_count

        if flagged_count > 0:
            logger.info(
                "pii_batch_scan_complete",
                total_chunks=len(chunks),
                flagged_count=flagged_count,
                clean_count=clean_count,
                sensitivity=self.sensitivity.value,
            )

        return results, clean_count, flagged_count


# Singleton pattern
_detector: PIIDetector | None = None


def get_pii_detector() -> PIIDetector:
    """Get the singleton PII detector instance.

    Returns:
        Global PIIDetector instance (created on first call).

    """
    global _detector  # noqa: PLW0603
    if _detector is None:
        _detector = PIIDetector()
    return _detector

"""Unit tests for PII detector service.

Tests basic initialization, scanning functionality, and batch operations
to improve coverage of app/shared/services/pii/detector.py.
"""

from unittest.mock import Mock, patch

import pytest

from app.shared.services.pii.detector import PIIDetector, get_pii_detector
from app.shared.services.pii.types import PIIResult, PIIType, SensitivityLevel


class TestPIIDetectorInitialization:
    """Test PIIDetector initialization and configuration."""

    def test_detector_initializes_with_defaults(self):
        """Test that detector initializes with default config settings."""
        with patch("app.shared.services.pii.detector.settings") as mock_settings:
            mock_settings.PII_SENSITIVITY_LEVEL = "medium"
            mock_settings.PII_SCREENING_ENABLED = True

            detector = PIIDetector()

            assert detector.sensitivity == SensitivityLevel.MEDIUM
            assert detector.enabled is True
            assert len(detector.active_patterns) > 0

    def test_detector_initializes_with_custom_sensitivity(self):
        """Test detector initialization with custom sensitivity level."""
        detector = PIIDetector(sensitivity=SensitivityLevel.HIGH, enabled=True)

        assert detector.sensitivity == SensitivityLevel.HIGH
        assert detector.enabled is True
        # High sensitivity should have more patterns than medium
        assert len(detector.active_patterns) >= 5

    def test_detector_can_be_disabled(self):
        """Test detector initialization with screening disabled."""
        detector = PIIDetector(enabled=False)

        assert detector.enabled is False


class TestPIIDetectorScan:
    """Test PII detection scanning functionality."""

    def test_scan_returns_empty_result_when_disabled(self):
        """Test that disabled detector returns clean result without scanning."""
        detector = PIIDetector(enabled=False)

        result = detector.scan("test@example.com")

        assert result.has_pii is False
        assert result.match_count == 0
        assert len(result.types) == 0

    def test_scan_returns_empty_result_for_empty_text(self):
        """Test that scanning empty text returns clean result."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        result = detector.scan("")

        assert result.has_pii is False
        assert result.match_count == 0

    def test_scan_returns_empty_result_for_whitespace_only(self):
        """Test that scanning whitespace-only text returns clean result."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        result = detector.scan("   \n\t  ")

        assert result.has_pii is False
        assert result.match_count == 0

    def test_scan_detects_email_address(self):
        """Test that scan detects email addresses in text."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        result = detector.scan("Contact me at john.doe@example.com for more info")

        assert result.has_pii is True
        assert result.match_count >= 1
        assert PIIType.EMAIL in result.types

    def test_scan_returns_pii_result_with_type_counts(self):
        """Test that scan result includes match counts by type."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        result = detector.scan("Email: test@example.com, Phone: 555-123-4567")

        assert result.has_pii is True
        assert result.match_count >= 1
        assert len(result.matches_by_type) > 0


class TestPIIDetectorBatchScan:
    """Test batch scanning functionality."""

    def test_scan_chunks_processes_multiple_texts(self):
        """Test that scan_chunks processes list of text chunks."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        chunks = [
            "This is clean text",
            "Contact: admin@example.com",
            "Another clean chunk",
        ]

        results, clean_count, flagged_count = detector.scan_chunks(chunks)

        assert len(results) == 3
        assert isinstance(results[0], PIIResult)
        assert clean_count + flagged_count == 3

    def test_scan_chunks_counts_clean_and_flagged_correctly(self):
        """Test that scan_chunks returns correct counts."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        chunks = [
            "Clean text without PII",
            "Another clean chunk",
        ]

        results, clean_count, flagged_count = detector.scan_chunks(chunks)

        assert clean_count == 2
        assert flagged_count == 0

    def test_scan_chunks_handles_empty_list(self):
        """Test that scan_chunks handles empty chunk list."""
        detector = PIIDetector(enabled=True, sensitivity=SensitivityLevel.MEDIUM)

        results, clean_count, flagged_count = detector.scan_chunks([])

        assert len(results) == 0
        assert clean_count == 0
        assert flagged_count == 0


class TestGetPIIDetector:
    """Test singleton getter function."""

    def test_get_pii_detector_returns_detector_instance(self):
        """Test that get_pii_detector returns PIIDetector instance."""
        # Reset singleton
        import app.shared.services.pii.detector as detector_module

        detector_module._detector = None

        detector = get_pii_detector()

        assert isinstance(detector, PIIDetector)

    def test_get_pii_detector_returns_same_instance(self):
        """Test that get_pii_detector returns singleton instance."""
        # Reset singleton
        import app.shared.services.pii.detector as detector_module

        detector_module._detector = None

        detector1 = get_pii_detector()
        detector2 = get_pii_detector()

        assert detector1 is detector2

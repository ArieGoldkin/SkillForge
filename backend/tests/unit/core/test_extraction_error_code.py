"""Tests for ExtractionErrorCode enum."""

import pytest

from app.core.exceptions import ExtractionErrorCode, JinaReaderError


@pytest.mark.unit
class TestExtractionErrorCode:
    """Test cases for ExtractionErrorCode enum."""

    def test_all_error_codes_exist(self):
        """Verify all expected error codes are defined."""
        expected_codes = [
            "HTTP_404",
            "HTTP_5XX",
            "TIMEOUT",
            "ERROR_PAGE",
            "REDIRECT_LOOP",
            "NETWORK_ERROR",
            "UNKNOWN",
        ]
        for code in expected_codes:
            assert hasattr(ExtractionErrorCode, code), f"Missing error code: {code}"

    def test_error_code_values(self):
        """Verify error codes have expected string values."""
        assert ExtractionErrorCode.HTTP_404.value == "HTTP_404"
        assert ExtractionErrorCode.HTTP_5XX.value == "HTTP_5XX"
        assert ExtractionErrorCode.TIMEOUT.value == "TIMEOUT"
        assert ExtractionErrorCode.ERROR_PAGE.value == "ERROR_PAGE"
        assert ExtractionErrorCode.REDIRECT_LOOP.value == "REDIRECT_LOOP"
        assert ExtractionErrorCode.NETWORK_ERROR.value == "NETWORK_ERROR"
        assert ExtractionErrorCode.UNKNOWN.value == "UNKNOWN"

    def test_error_codes_are_strings(self):
        """Verify error codes are string enum members."""
        for code in ExtractionErrorCode:
            assert isinstance(code.value, str)

    def test_jina_reader_error_with_code(self):
        """Test JinaReaderError includes error_code."""
        error = JinaReaderError("Test error", error_code=ExtractionErrorCode.HTTP_404)
        assert error.error_code == ExtractionErrorCode.HTTP_404
        assert str(error) == "Test error"

    def test_jina_reader_error_default_code(self):
        """Test JinaReaderError defaults to UNKNOWN."""
        error = JinaReaderError("Test error")
        assert error.error_code == ExtractionErrorCode.UNKNOWN

    def test_jina_reader_error_with_timeout_code(self):
        """Test JinaReaderError with TIMEOUT code."""
        error = JinaReaderError("Request timed out", error_code=ExtractionErrorCode.TIMEOUT)
        assert error.error_code == ExtractionErrorCode.TIMEOUT
        assert "timed out" in str(error)

    def test_jina_reader_error_with_http_5xx_code(self):
        """Test JinaReaderError with HTTP_5XX code."""
        error = JinaReaderError("Server error", error_code=ExtractionErrorCode.HTTP_5XX)
        assert error.error_code == ExtractionErrorCode.HTTP_5XX

    def test_jina_reader_error_none_code_defaults_to_unknown(self):
        """Test JinaReaderError with None error_code defaults to UNKNOWN."""
        error = JinaReaderError("Test error", error_code=None)
        assert error.error_code == ExtractionErrorCode.UNKNOWN

    def test_error_code_enum_uniqueness(self):
        """Verify all error codes are unique."""
        codes = [code.value for code in ExtractionErrorCode]
        assert len(codes) == len(set(codes)), "Error codes must be unique"

    def test_error_code_enum_count(self):
        """Verify expected number of error codes."""
        # 10 error codes: HTTP_404, HTTP_5XX, TIMEOUT, ERROR_PAGE, REDIRECT_LOOP,
        # NETWORK_ERROR, INVALID_URL, TRANSCRIPT_DISABLED, NO_TRANSCRIPT, UNKNOWN
        assert len(ExtractionErrorCode) == 10, "Expected 10 error codes"

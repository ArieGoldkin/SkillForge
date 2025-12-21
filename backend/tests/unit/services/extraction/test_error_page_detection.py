"""Tests for error page detection in JinaReader."""

import pytest

from app.shared.services.extraction.jina_reader import _is_error_page


@pytest.mark.unit
class TestErrorPageDetection:
    """Test cases for _is_error_page() function."""

    @pytest.mark.parametrize(
        "title,expected",
        [
            ("404 - Page Not Found", True),
            ("Not Found - Claude Docs", True),
            ("Error 500 - Internal Server Error", True),
            ("Access Denied", True),
            ("Redirecting...", True),
            ("Bad Gateway", True),
            ("Service Unavailable", True),
            ("Forbidden - Access Denied", True),
            ("Unauthorized Access", True),
            ("Internal Server Error", True),
            ("Moved Permanently", True),
            ("Getting Started with Python", False),
            ("How to Build REST APIs", False),
            ("LangGraph Documentation", False),
            ("Introduction to Machine Learning", False),
            ("", False),
            (None, False),
        ],
    )
    def test_error_page_detection(self, title: str | None, expected: bool):
        """Test that error pages are correctly detected by title."""
        result = _is_error_page(title)
        assert result == expected, f"Expected {expected} for title: {title!r}"

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        assert _is_error_page("PAGE NOT FOUND") is True
        assert _is_error_page("page not found") is True
        assert _is_error_page("Page Not Found") is True
        assert _is_error_page("ERROR 404") is True
        assert _is_error_page("error 404") is True

    def test_partial_matches_in_title(self):
        """Test that error indicators are detected even when embedded in longer titles."""
        assert _is_error_page("Documentation - Error 404") is True
        assert _is_error_page("Access Denied - Please Log In") is True
        assert _is_error_page("Redirecting to Login Page...") is True
        assert _is_error_page("Normal Title") is False

    def test_empty_string_handling(self):
        """Test that empty string returns False."""
        assert _is_error_page("") is False

    def test_none_handling(self):
        """Test that None returns False."""
        assert _is_error_page(None) is False

    def test_whitespace_only_title(self):
        """Test that whitespace-only title returns False."""
        assert _is_error_page("   ") is False
        assert _is_error_page("\n\t") is False

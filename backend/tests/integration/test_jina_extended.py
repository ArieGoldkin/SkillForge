"""Extended tests for Jina Reader service - Testing various URL types."""

import os

import pytest

from app.core.config import get_settings
from app.shared.services.extraction.jina_reader import JinaReader, JinaReaderError


@pytest.mark.asyncio
@pytest.mark.external
async def test_multiple_urls(requires_jina_api_key):
    """Test extraction from multiple different URLs."""
    from app.shared.services.extraction.content_type import detect_content_type

    test_urls = [
        ("https://react.dev", "article"),
        ("https://python.org", "article"),
        ("https://fastapi.tiangolo.com", "article"),
    ]

    reader = JinaReader()
    results = []

    try:
        for url, _expected_type in test_urls:
            detected_type = detect_content_type(url)

            try:
                result = await reader.extract_article(url)

                assert result["title"], f"Title is empty for {url}"
                assert result["content"], f"Content is empty for {url}"
                assert result["word_count"] > 0, f"Word count is 0 for {url}"

                results.append(True)
            except JinaReaderError as e:
                error_str = str(e).lower()
                # Skip on 401 (invalid API key) - user needs to update .env.test
                if "401" in str(e) or "AuthenticationFailedError" in str(e):
                    pytest.skip(f"JINA_API_KEY is invalid or expired: {e}")
                # Skip on 429 (rate limit) - API key hit rate limit
                if "429" in str(e) or "rate limit" in error_str or "quota" in error_str:
                    pytest.skip(f"Jina API rate limit hit: {e}")
                results.append(False)
            except (RuntimeError, ValueError, KeyError, TimeoutError) as e:
                results.append(False)
                raise

        assert all(results), f"Only {sum(results)}/{len(results)} URLs extracted successfully"
    finally:
        await reader.close()


@pytest.mark.asyncio
@pytest.mark.external
async def test_retry_behavior(requires_jina_api_key):
    """Test retry behavior (manual verification).

    Note: Retry behavior is tested with invalid URLs that fail.
    Retries should occur automatically (3 attempts with exponential backoff).
    The error handling test already verified retries work.
    """
    # Retry behavior is verified in error handling tests
    # This test is kept for documentation purposes
    pass


@pytest.fixture
def requires_jina_api_key():
    """Skip test if JINA_API_KEY is not set or in CI environment.

    CI environment is detected via CI or GITHUB_ACTIONS environment variables.
    Tests are skipped in CI due to rate limits and API key restrictions.
    """
    # Skip automatically in CI to avoid rate limits
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        pytest.skip("Skipping Jina API tests in CI due to rate limits")

    settings = get_settings()
    if not settings.JINA_API_KEY:
        pytest.skip("JINA_API_KEY not set in .env.test - skipping test")


@pytest.mark.asyncio
@pytest.mark.external
async def test_title_extraction_variations(requires_jina_api_key):
    """Test title extraction with different markdown formats."""
    reader = JinaReader()

    # Test with a URL that should have markdown title
    test_url = "https://react.dev"

    try:
        result = await reader.extract_article(test_url)
        title = result["title"]

        # Verify title is not empty
        assert title and title != "Untitled", "Title should not be empty or 'Untitled'"

        # Check if title has markdown removed
        assert not title.startswith("# "), "Title should not contain markdown header prefix"
    except JinaReaderError as e:
        error_str = str(e).lower()
        # Skip on 401 (invalid API key) - user needs to update .env.test
        if "401" in str(e) or "AuthenticationFailedError" in str(e):
            pytest.skip(f"JINA_API_KEY is invalid or expired: {e}")
        # Skip on 429 (rate limit) - API key hit rate limit
        if "429" in str(e) or "rate limit" in error_str or "quota" in error_str:
            pytest.skip(f"Jina API rate limit hit: {e}")
        raise
    finally:
        await reader.close()


@pytest.mark.asyncio
@pytest.mark.external
async def test_metadata_structure(requires_jina_api_key):
    """Test metadata structure in response."""
    reader = JinaReader()
    test_url = "https://react.dev"

    try:
        result = await reader.extract_article(test_url)

        # Verify all required fields
        required_fields = ["title", "content", "word_count", "metadata"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Verify metadata structure
        metadata = result["metadata"]
        assert "extractor" in metadata, "Missing 'extractor' in metadata"
        assert "source_url" in metadata, "Missing 'source_url' in metadata"
        assert metadata["extractor"] == "jina_reader", "Wrong extractor name"
        assert metadata["source_url"] == test_url, "Wrong source URL"

        # Verify types
        assert isinstance(result["title"], str), "Title should be string"
        assert isinstance(result["content"], str), "Content should be string"
        assert isinstance(result["word_count"], int), "Word count should be int"
        assert isinstance(result["metadata"], dict), "Metadata should be dict"
    except JinaReaderError as e:
        error_str = str(e).lower()
        # Skip on 401 (invalid API key) - user needs to update .env.test
        if "401" in str(e) or "AuthenticationFailedError" in str(e):
            pytest.skip(f"JINA_API_KEY is invalid or expired: {e}")
        # Skip on 429 (rate limit) - API key hit rate limit
        if "429" in str(e) or "rate limit" in error_str or "quota" in error_str:
            pytest.skip(f"Jina API rate limit hit: {e}")
        raise
    finally:
        await reader.close()

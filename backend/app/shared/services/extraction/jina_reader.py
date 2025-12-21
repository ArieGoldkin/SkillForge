"""Jina AI Reader service for content extraction."""

import os

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.constants import (
    DEFAULT_TIMEOUT,
    DEFAULT_TITLE,
    HTTP_ERROR_THRESHOLD,
    HTTP_NOT_FOUND,
    MAX_ERROR_MESSAGE_LENGTH_LONG,
    MAX_RETRY_ATTEMPTS,
    MAX_TITLE_PREVIEW_LENGTH,
    RETRY_MAX_WAIT_JINA,
    RETRY_MAX_WAIT_JINA_TEST,
    RETRY_MIN_WAIT_JINA,
    RETRY_MIN_WAIT_JINA_TEST,
    RETRY_MULTIPLIER_JINA,
)
from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.core.logging import get_logger
from app.core.types import ExtractionResult
from app.shared.services.extraction.content_cleaner import clean_extracted_content

logger = get_logger(__name__)


def _is_error_page(title: str | None, content: str | None = None) -> bool:  # noqa: ARG001
    """Detect if extracted content is an error page.

    Args:
        title: Page title from extraction
        content: Optional page content for additional checks

    Returns:
        True if the page appears to be an error page

    """
    if not title:
        return False

    title_lower = title.lower()

    # Common error page indicators in titles
    error_indicators = [
        "404",
        "not found",
        "page not found",
        "error",
        "access denied",
        "forbidden",
        "unauthorized",
        "redirecting",
        "moved permanently",
        "bad gateway",
        "service unavailable",
        "internal server error",
    ]

    return any(indicator in title_lower for indicator in error_indicators)


class JinaReader:
    """Jina AI Reader service for extracting content from URLs."""

    BASE_URL = "https://r.jina.ai"

    def __init__(self) -> None:
        """Initialize Jina Reader with API key and HTTP client."""
        self.api_key = settings.JINA_API_KEY
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_JINA,
            min=(
                RETRY_MIN_WAIT_JINA_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MIN_WAIT_JINA
            ),
            max=(
                RETRY_MAX_WAIT_JINA_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MAX_WAIT_JINA
            ),
        ),
        reraise=True,
    )
    async def extract_article(self, url: str) -> ExtractionResult:
        """Extract content from article URL using Jina AI Reader.

        Args:
            url: The URL to extract content from

        Returns:
            Dictionary with title, content, word_count, and metadata

        Raises:
            JinaReaderError: If extraction fails or URL is not found

        """
        try:
            # Build headers with optional API key
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Make request to Jina Reader API
            response = await self.client.get(
                f"{self.BASE_URL}/{url}",
                headers=headers,
                follow_redirects=True,
            )

            # Handle 404 specifically
            if response.status_code == HTTP_NOT_FOUND:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = f"URL not found (404): {url}. Response preview: {response_preview}"
                logger.error(
                    "jina_extraction_not_found",
                    url=url,
                    status_code=HTTP_NOT_FOUND,
                    response_preview=response_preview,
                )
                raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.HTTP_404)

            # Handle other HTTP errors
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = (
                    f"HTTP {response.status_code} error for {url}. Response: {response_preview}"
                )
                logger.error(
                    "jina_extraction_http_error",
                    url=url,
                    status_code=response.status_code,
                    response_preview=response_preview,
                    response_headers=dict(response.headers),
                )
                raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Jina returns markdown content
            raw_content = response.text

            # Extract title from first line (remove markdown header)
            lines = raw_content.split("\n")
            title = DEFAULT_TITLE
            if lines:
                first_line = lines[0].strip()
                if first_line.startswith("# "):
                    title = first_line[2:].strip()
                elif first_line:
                    title = first_line

            # Clean content to remove boilerplate (cookies, nav, footer)
            content = clean_extracted_content(raw_content)

            logger.info(
                "jina_extraction_success",
                url=url,
                raw_content_length=len(raw_content),
                cleaned_content_length=len(content),
                word_count=len(content.split()),
                title=title[:MAX_TITLE_PREVIEW_LENGTH] if title else DEFAULT_TITLE,
            )

            return {
                "title": title,
                "content": content,
                "word_count": len(content.split()),
                "metadata": {
                    "extractor": "jina_reader",
                    "source_url": url,
                    "raw_content_length": len(raw_content),
                    "cleaned_content_length": len(content),
                },
            }

        except httpx.TimeoutException as e:
            error_msg = (
                f"Request timed out after {DEFAULT_TIMEOUT}s: {url}. Error type: {type(e).__name__}"
            )
            logger.exception(
                "jina_extraction_timeout",
                url=url,
                timeout=DEFAULT_TIMEOUT,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.TIMEOUT) from e

        except JinaReaderError:
            # Re-raise JinaReaderError without modification
            raise

        except Exception as e:
            error_msg = f"Extraction failed for {url}: {type(e).__name__}: {e!s}"
            logger.exception(
                "jina_extraction_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                # exc_info is implicit when exception context is available
            )
            raise JinaReaderError(error_msg) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

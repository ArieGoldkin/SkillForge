"""Jina AI Reader service for content extraction."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class JinaReaderError(Exception):
    """Custom exception for Jina Reader errors."""

    pass


class JinaReader:
    """Jina AI Reader service for extracting content from URLs."""

    BASE_URL = "https://r.jina.ai"

    def __init__(self) -> None:
        """Initialize Jina Reader with API key and HTTP client."""
        self.api_key = settings.JINA_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def extract_article(self, url: str) -> dict[str, str | int | dict[str, str]]:
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
            if response.status_code == 404:
                logger.error("jina_extraction_not_found", url=url, status_code=404)
                raise JinaReaderError("URL not found (404)")

            # Handle other HTTP errors
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(
                    "jina_extraction_http_error",
                    url=url,
                    status_code=response.status_code,
                    error=error_msg,
                )
                raise JinaReaderError(error_msg)

            # Jina returns markdown content
            content = response.text

            # Extract title from first line (remove markdown header)
            lines = content.split("\n")
            title = "Untitled"
            if lines:
                first_line = lines[0].strip()
                if first_line.startswith("# "):
                    title = first_line[2:].strip()
                elif first_line:
                    title = first_line

            logger.info(
                "jina_extraction_success",
                url=url,
                content_length=len(content),
                word_count=len(content.split()),
                title=title[:100] if title else "Untitled",
            )

            return {
                "title": title,
                "content": content,
                "word_count": len(content.split()),
                "metadata": {
                    "extractor": "jina_reader",
                    "source_url": url,
                },
            }

        except httpx.TimeoutException as e:
            logger.error("jina_extraction_timeout", url=url, error=str(e))
            raise JinaReaderError("Request timed out") from e

        except JinaReaderError:
            # Re-raise JinaReaderError without modification
            raise

        except Exception as e:
            logger.error(
                "jina_extraction_failed", url=url, error=str(e), error_type=type(e).__name__
            )
            raise JinaReaderError(f"Extraction failed: {e!s}") from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

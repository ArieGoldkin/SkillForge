"""Trafilatura web content extractor.

Modern, self-hosted alternative to JinaReader for general web articles.
Uses trafilatura library which is fast, free, and doesn't require API keys.

Best for: News sites, blogs, articles, documentation
"""

import asyncio

from app.core.exceptions import JinaReaderError  # Reuse for consistency
from app.core.logging import get_logger
from app.core.types import ExtractionResult

logger = get_logger(__name__)


class TrafilaturaExtractor:
    """Extracts content from web articles using trafilatura.

    Trafilatura is a Python library for extracting clean article content
    from web pages. It's self-hosted, free, and fast.

    Configuration:
        - favor_recall=True: Prioritizes extracting more content when uncertain
          about whether content is boilerplate. This reduces false negatives at
          the cost of potentially including some non-essential content.
        - include_tables=True: Preserves table data which often contains
          valuable structured information.

    Example:
        >>> extractor = TrafilaturaExtractor()
        >>> result = await extractor.extract_article("https://example.com/article")
        >>> result["content"]  # Clean article content
        "Article text here..."

    """

    def __init__(self) -> None:
        """Initialize Trafilatura extractor."""
        try:
            import trafilatura

            self.trafilatura = trafilatura
        except ImportError:
            msg = "trafilatura not installed. Install with: poetry add trafilatura"
            logger.exception("trafilatura_not_installed", error=msg)
            raise ImportError(msg) from None

    async def extract_article(self, url: str) -> ExtractionResult:
        """Extract content from article URL.

        Args:
            url: The URL to extract content from

        Returns:
            ExtractionResult with title, content, word_count, and metadata

        Raises:
            JinaReaderError: If extraction fails (reused for API consistency)

        """
        logger.info(
            "trafilatura_extraction_started",
            url=url,
        )

        try:
            # Trafilatura is synchronous, so we run it in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._extract_sync,
                url,
            )

            # Type-safe access to title for logging
            title = result.get("title")
            title_length = len(title) if isinstance(title, str) else 0

            logger.info(
                "trafilatura_extraction_success",
                url=url,
                word_count=result["word_count"],
                title_length=title_length,
            )

            return result

        except Exception as e:
            error_msg = f"Trafilatura extraction failed for {url}: {type(e).__name__}: {e!s}"
            logger.exception(
                "trafilatura_extraction_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg) from e

    async def extract_batch(self, urls: list[str], threads: int = 10) -> list[ExtractionResult]:
        """Batch extract multiple URLs in parallel using trafilatura's native threading.

        This method uses trafilatura's built-in buffered_downloads which implements
        efficient multi-threaded downloading. Significantly faster than sequential
        extraction for multiple URLs.

        Args:
            urls: List of URLs to extract content from
            threads: Number of concurrent threads for downloading (default: 10)

        Returns:
            List of ExtractionResult dictionaries (only successful extractions)

        Example:
            >>> extractor = TrafilaturaExtractor()
            >>> urls = ["https://example.com/1", "https://example.com/2"]
            >>> results = await extractor.extract_batch(urls, threads=5)
            >>> len(results)  # May be less than len(urls) if some failed
            2

        """
        from trafilatura.downloads import buffered_downloads

        logger.info(
            "trafilatura_batch_extraction_started",
            url_count=len(urls),
            threads=threads,
        )

        try:
            # Run buffered_downloads in executor since it's synchronous
            # It returns a generator of (url, html) tuples
            loop = asyncio.get_event_loop()
            downloaded = await loop.run_in_executor(
                None, lambda: list(buffered_downloads(urls, download_threads=threads))
            )

            results: list[ExtractionResult] = []
            successful = 0
            failed = 0

            for url, html in downloaded:
                if html:
                    try:
                        result = self._extract_content(html, url)
                        results.append(result)
                        successful += 1
                    except JinaReaderError as e:
                        # Catch extraction errors for individual URLs
                        # Don't fail the entire batch if one URL fails
                        failed += 1
                        logger.warning(
                            "trafilatura_batch_extraction_item_failed",
                            url=url,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                else:
                    failed += 1
                    logger.warning(
                        "trafilatura_batch_extraction_download_failed",
                        url=url,
                    )

            logger.info(
                "trafilatura_batch_extraction_completed",
                total_urls=len(urls),
                successful=successful,
                failed=failed,
                success_rate=f"{successful / len(urls) * 100:.1f}%" if urls else "0.0%",
            )

            return results

        except Exception as e:
            error_msg = f"Trafilatura batch extraction failed: {type(e).__name__}: {e!s}"
            logger.exception(
                "trafilatura_batch_extraction_failed",
                url_count=len(urls),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg) from e

    def deduplicate_content(self, contents: list[str]) -> list[tuple[int, str]]:
        """Deduplicate content using Simhash fuzzy hashing.

        Uses trafilatura's Simhash implementation for near-duplicate detection.
        This is more sophisticated than exact string matching - it detects
        semantically similar content even with minor textual differences.

        Args:
            contents: List of content strings to deduplicate

        Returns:
            List of (index, content) tuples for unique contents only.
            Index refers to the original position in the input list.

        Example:
            >>> extractor = TrafilaturaExtractor()
            >>> contents = ["Article A", "Article B", "Article A with typo"]
            >>> unique = extractor.deduplicate_content(contents)
            >>> len(unique)  # Simhash may detect A and "A with typo" as duplicates
            2

        """
        from trafilatura.deduplication import Simhash

        logger.info(
            "trafilatura_deduplication_started",
            content_count=len(contents),
        )

        seen_hashes: set[int] = set()
        unique: list[tuple[int, str]] = []

        for i, content in enumerate(contents):
            h = Simhash(content)
            if h.value not in seen_hashes:
                seen_hashes.add(h.value)
                unique.append((i, content))

        duplicates_removed = len(contents) - len(unique)
        logger.info(
            "trafilatura_deduplication_completed",
            original_count=len(contents),
            unique_count=len(unique),
            duplicates_removed=duplicates_removed,
            deduplication_rate=f"{duplicates_removed / len(contents) * 100:.1f}%"
            if contents
            else "0.0%",
        )

        return unique

    def _extract_sync(self, url: str) -> ExtractionResult:
        """Extract content synchronously using trafilatura.

        Args:
            url: URL to extract

        Returns:
            ExtractionResult dictionary

        """
        # Download and extract content
        downloaded = self.trafilatura.fetch_url(url)

        if not downloaded:
            msg = f"Failed to download content from: {url}"
            raise JinaReaderError(msg)

        return self._extract_content(downloaded, url)

    def _extract_content(self, html: str, url: str) -> ExtractionResult:
        """Extract content from pre-downloaded HTML.

        This internal method is used by both extract_article (single URL)
        and extract_batch (multiple URLs) to avoid code duplication.

        Args:
            html: Downloaded HTML content
            url: Source URL (for metadata)

        Returns:
            ExtractionResult dictionary

        Raises:
            JinaReaderError: If content extraction fails

        """
        # Extract main content (article text)
        # This removes boilerplate, ads, navigation, etc.
        extracted = self.trafilatura.extract(
            html,
            favor_recall=True,  # Include more content when unsure
            include_comments=False,  # Don't include comments
            include_tables=True,  # Tables often contain valuable data
            include_images=False,  # Don't include image metadata
            include_links=False,  # Don't include link metadata
            output_format="markdown",  # Return as markdown
        )

        if not extracted:
            # Try extracting as plain text if markdown fails
            extracted = self.trafilatura.extract(
                html,
                favor_recall=True,  # Include more content when unsure
                include_comments=False,
                include_tables=True,  # Tables often contain valuable data
                include_images=False,
                include_links=False,
                output_format="txt",
            )

        if not extracted:
            msg = f"No content extracted from: {url}"
            raise JinaReaderError(msg)

        # Extract metadata
        metadata = self.trafilatura.extract_metadata(html)

        # Get title from metadata or extract from content
        # Note: trafilatura.extract_metadata() returns a Document object, not a dict
        title = None
        if metadata:
            title = getattr(metadata, "title", None)
            if title:
                title = title.strip()

        # If no title in metadata, try to extract from content
        if not title:
            # Trafilatura doesn't always extract title, so we look for first heading
            lines = extracted.split("\n")
            for line in lines[:10]:  # Check first 10 lines
                stripped = line.strip()
                if stripped.startswith("# "):
                    title = stripped[2:].strip()
                    break
                if stripped.startswith("#"):
                    # Remove all # prefixes
                    title = stripped.lstrip("#").strip()
                    break

        # Fallback to "Untitled" if still no title
        if not title:
            title = "Untitled"

        # Clean up content (remove excessive whitespace)
        content = extracted.strip()
        word_count = len(content.split())

        return {
            "title": title,
            "content": content,
            "word_count": word_count,
            "metadata": {
                "extractor": "trafilatura",
                "source_url": url,
                "raw_content_length": len(content),
                "cleaned_content_length": len(content),
                "has_metadata": metadata is not None,
            },
        }

    async def close(self) -> None:
        """Close any resources (no-op for Trafilatura extractor)."""

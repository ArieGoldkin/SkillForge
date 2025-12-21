"""ArXiv PDF extraction service for research papers.

Issue #299-304: Implements direct PDF extraction for arXiv papers.

The standard Jina Reader API only scrapes the abstract page HTML (~4K chars).
This extractor downloads the actual PDF and extracts full text (~50K+ chars).

URL Pattern Detection:
- https://arxiv.org/abs/2512.08296 → Convert to PDF URL
- https://arxiv.org/pdf/2512.08296.pdf → Direct PDF URL

Architecture:
    User URL → is_arxiv_url() → convert_to_pdf_url() → download PDF → extract text
"""

import io
import re

import httpx
from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.constants import MAX_RETRY_ATTEMPTS
from app.core.exceptions import JinaReaderError  # Reuse for consistency
from app.core.logging import get_logger
from app.core.types import ExtractionResult

logger = get_logger(__name__)

# ArXiv URL patterns
ARXIV_ABS_PATTERN = re.compile(r"arxiv\.org/abs/(\d+\.\d+)")
ARXIV_PDF_PATTERN = re.compile(r"arxiv\.org/pdf/(\d+\.\d+)")

# PDF download timeout (PDFs can be large)
PDF_DOWNLOAD_TIMEOUT = 60.0

# Title extraction constants
MIN_METADATA_TITLE_LENGTH = 5  # Minimum valid title length from PDF metadata
MIN_LINE_TITLE_LENGTH = 20  # Minimum line length to consider as title


def is_arxiv_url(url: str) -> bool:
    """Check if URL is an arXiv paper URL.

    Args:
        url: URL to check

    Returns:
        True if URL matches arXiv patterns

    Examples:
        >>> is_arxiv_url("https://arxiv.org/abs/2512.08296")
        True
        >>> is_arxiv_url("https://arxiv.org/pdf/2512.08296.pdf")
        True
        >>> is_arxiv_url("https://example.com/article")
        False

    """
    return bool(ARXIV_ABS_PATTERN.search(url) or ARXIV_PDF_PATTERN.search(url))


def convert_to_pdf_url(url: str) -> str:
    """Convert arXiv URL to PDF download URL.

    Args:
        url: arXiv URL (either /abs/ or /pdf/ format)

    Returns:
        PDF download URL

    Examples:
        >>> convert_to_pdf_url("https://arxiv.org/abs/2512.08296")
        "https://arxiv.org/pdf/2512.08296.pdf"
        >>> convert_to_pdf_url("https://arxiv.org/pdf/2512.08296.pdf")
        "https://arxiv.org/pdf/2512.08296.pdf"

    """
    # Try /abs/ pattern first
    match = ARXIV_ABS_PATTERN.search(url)
    if match:
        paper_id = match.group(1)
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # Try /pdf/ pattern
    match = ARXIV_PDF_PATTERN.search(url)
    if match:
        paper_id = match.group(1)
        return f"https://arxiv.org/pdf/{paper_id}.pdf"

    # Fallback: return as-is
    return url


def extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv paper ID from URL.

    Args:
        url: arXiv URL

    Returns:
        Paper ID (e.g., "2512.08296") or None if not found

    """
    match = ARXIV_ABS_PATTERN.search(url) or ARXIV_PDF_PATTERN.search(url)
    return match.group(1) if match else None


class ArxivPDFExtractor:
    """Extracts full text from arXiv PDF papers.

    Unlike Jina Reader which only gets the abstract page (~4K chars),
    this extractor downloads and parses the full PDF (~50K+ chars).

    Example:
        >>> extractor = ArxivPDFExtractor()
        >>> result = await extractor.extract_article("https://arxiv.org/abs/2512.08296")
        >>> len(result["content"])  # Full paper content
        50000

    """

    def __init__(self) -> None:
        """Initialize with HTTP client for PDF downloads."""
        self.client = httpx.AsyncClient(
            timeout=PDF_DOWNLOAD_TIMEOUT,
            follow_redirects=True,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def extract_article(self, url: str) -> ExtractionResult:
        """Extract content from arXiv paper URL.

        Downloads the PDF and extracts all text content.

        Args:
            url: arXiv URL (either /abs/ or /pdf/ format)

        Returns:
            ExtractionResult with full paper content

        Raises:
            JinaReaderError: If extraction fails (reused for API consistency)

        """
        paper_id = extract_arxiv_id(url)
        if not paper_id:
            error_msg = f"Invalid arXiv URL format: {url}"
            logger.error("arxiv_invalid_url", url=url)
            raise JinaReaderError(error_msg)

        pdf_url = convert_to_pdf_url(url)

        logger.info(
            "arxiv_pdf_download_started",
            url=url,
            pdf_url=pdf_url,
            paper_id=paper_id,
        )

        try:
            # Download PDF
            response = await self.client.get(pdf_url)
            response.raise_for_status()

            pdf_bytes = response.content
            pdf_size = len(pdf_bytes)

            logger.info(
                "arxiv_pdf_downloaded",
                paper_id=paper_id,
                size_bytes=pdf_size,
            )

            # Extract text from PDF
            content, title, page_count = self._extract_pdf_text(pdf_bytes, paper_id)

            word_count = len(content.split())

            logger.info(
                "arxiv_extraction_success",
                url=url,
                paper_id=paper_id,
                content_length=len(content),
                word_count=word_count,
                page_count=page_count,
            )

            return {
                "title": title,
                "content": content,
                "word_count": word_count,
                "metadata": {
                    "extractor": "arxiv_pdf",
                    "source_url": url,
                    "pdf_url": pdf_url,
                    "paper_id": paper_id,
                    "raw_content_length": len(content),
                    "cleaned_content_length": len(content),
                    "pdf_size_bytes": pdf_size,
                    "page_count": page_count,
                },
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} downloading PDF: {pdf_url}"
            logger.exception(
                "arxiv_pdf_http_error",
                url=url,
                pdf_url=pdf_url,
                status_code=e.response.status_code,
            )
            raise JinaReaderError(error_msg) from e

        except httpx.TimeoutException as e:
            error_msg = f"Timeout downloading PDF after {PDF_DOWNLOAD_TIMEOUT}s: {pdf_url}"
            logger.exception(
                "arxiv_pdf_timeout",
                url=url,
                pdf_url=pdf_url,
                timeout=PDF_DOWNLOAD_TIMEOUT,
            )
            raise JinaReaderError(error_msg) from e

        except Exception as e:
            error_msg = f"PDF extraction failed for {url}: {type(e).__name__}: {e!s}"
            logger.exception(
                "arxiv_extraction_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg) from e

    def _extract_pdf_text(
        self,
        pdf_bytes: bytes,
        paper_id: str,
    ) -> tuple[str, str, int]:
        """Extract text content from PDF bytes.

        Args:
            pdf_bytes: Raw PDF file content
            paper_id: arXiv paper ID for fallback title

        Returns:
            Tuple of (content, title, page_count)

        """
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        # Extract title from PDF metadata or first page
        title = self._extract_title(reader, paper_id)

        # Extract text from all pages
        pages_text = []
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    # Add page marker for reference
                    pages_text.append(f"[Page {page_num + 1}]\n{text}")
            except Exception as e:  # noqa: BLE001 - PDF pages can fail individually
                logger.warning(
                    "arxiv_page_extraction_failed",
                    paper_id=paper_id,
                    page_num=page_num + 1,
                    error=str(e),
                )
                continue

        content = "\n\n".join(pages_text)
        page_count = len(reader.pages)

        # Clean up common PDF artifacts
        content = self._clean_pdf_content(content)

        return content, title, page_count

    def _extract_title(self, reader: PdfReader, paper_id: str) -> str:
        """Extract title from PDF metadata or content.

        Args:
            reader: PdfReader instance
            paper_id: Fallback paper ID for title

        Returns:
            Extracted title or fallback

        """
        # Try PDF metadata
        if reader.metadata:
            metadata_title = reader.metadata.get("/Title")
            if (
                metadata_title
                and isinstance(metadata_title, str)
                and len(metadata_title) > MIN_METADATA_TITLE_LENGTH
            ):
                return str(metadata_title).strip()

        # Try first page header (research papers often have title at top)
        if reader.pages:
            try:
                first_page = reader.pages[0].extract_text()
                if first_page:
                    lines = first_page.split("\n")
                    for raw_line in lines[:5]:  # Check first 5 lines
                        stripped_line = raw_line.strip()
                        # Title is usually longer and doesn't start with numbers/dates
                        if (
                            len(stripped_line) > MIN_LINE_TITLE_LENGTH
                            and not stripped_line[0].isdigit()
                            and not stripped_line.startswith("arXiv")
                        ):
                            return stripped_line[:200]  # Truncate very long titles
            except Exception:  # noqa: S110, BLE001 - Best effort title extraction
                pass

        # Fallback to paper ID
        return f"arXiv:{paper_id}"

    def _clean_pdf_content(self, content: str) -> str:
        """Clean common PDF extraction artifacts.

        Args:
            content: Raw extracted text

        Returns:
            Cleaned text content

        """
        # Remove null bytes (PDF-specific issue)
        if "\x00" in content:
            null_count = content.count("\x00")
            logger.warning(
                "pdf_null_bytes_detected",
                count=null_count,
                source="arxiv_pdf",
            )
            content = content.replace("\x00", "")

        # Remove excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove page headers/footers with page numbers
        content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)

        # Remove common PDF artifacts
        content = re.sub(r"arXiv:\d+\.\d+v\d+\s+\[[\w.-]+\]\s+\d+\s+\w+\s+\d+", "", content)

        # Remove ligature artifacts (common in academic PDFs)
        content = content.replace("\ufb01", "fi")
        content = content.replace("\ufb02", "fl")
        content = content.replace("\ufb00", "ff")

        # Clean up hyphenation at line breaks
        content = re.sub(r"(\w+)-\n(\w+)", r"\1\2", content)

        return content.strip()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

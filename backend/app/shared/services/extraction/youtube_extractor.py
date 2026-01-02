"""YouTube transcript extraction service for video content.

Issue: ROADMAP claims YouTube extractor is implemented, but it's not.
This extractor uses youtube-transcript-api to extract video transcripts.
"""

import re

try:
    from youtube_transcript_api import (
        NoTranscriptFound,
        TranscriptsDisabled,
        YouTubeTranscriptApi,
    )
except ImportError:
    # Fallback if youtube-transcript-api is not installed
    YouTubeTranscriptApi = None
    NoTranscriptFound = Exception
    TranscriptsDisabled = Exception

from app.core.constants import DEFAULT_TITLE
from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.core.logging import get_logger
from app.core.types import ExtractionResult

logger = get_logger(__name__)

# YouTube URL patterns
YOUTUBE_URL_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video URL.

    Args:
        url: URL to check

    Returns:
        True if URL matches YouTube patterns

    """
    return extract_youtube_video_id(url) is not None


def extract_youtube_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found

    Examples:
        >>> extract_youtube_video_id("https://youtube.com/watch?v=abc123")
        "abc123"
        >>> extract_youtube_video_id("https://youtu.be/abc123")
        "abc123"

    """
    match = YOUTUBE_URL_PATTERN.search(url)
    return match.group(1) if match else None


class YouTubeExtractor:
    """Extracts transcripts from YouTube videos.

    Uses youtube-transcript-api to fetch available transcripts.
    Supports automatic language detection and manual language selection.
    """

    def __init__(self) -> None:
        """Initialize YouTube extractor."""
        if YouTubeTranscriptApi is None:
            raise ImportError(
                "youtube-transcript-api is not installed. "
                "Install it with: poetry add youtube-transcript-api"
            )
        self.client = YouTubeTranscriptApi()

    async def extract_article(self, url: str) -> ExtractionResult:
        """Extract transcript from YouTube video URL.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with title (video title), content (transcript),
            word_count, and metadata

        Raises:
            JinaReaderError: If extraction fails

        """
        video_id = extract_youtube_video_id(url)
        if not video_id:
            error_msg = f"Invalid YouTube URL format: {url}"
            logger.error("youtube_invalid_url", url=url)
            raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.INVALID_URL)

        logger.info(
            "youtube_extraction_started",
            url=url,
            video_id=video_id,
        )

        try:
            # Fetch transcript list to get available languages
            transcript_list = self.client.list_transcripts(video_id)

            # Try to get English transcript first, fallback to any available
            transcript = None
            try:
                # Try to find English transcript (manual or auto-generated)
                transcript = transcript_list.find_transcript(["en"])
            except NoTranscriptFound:
                # If English not found, get the first available transcript
                # Get manually created transcripts first (better quality)
                manual_transcripts = [t for t in transcript_list if not t.is_generated]
                if manual_transcripts:
                    transcript = manual_transcripts[0]
                else:
                    # Fallback to auto-generated transcript
                    generated_transcripts = [t for t in transcript_list if t.is_generated]
                    if generated_transcripts:
                        transcript = generated_transcripts[0]
                    else:
                        raise NoTranscriptFound(video_id, ["en"])

            # Fetch the actual transcript
            transcript_data = transcript.fetch()

            # Combine all transcript entries into a single text
            # Format: [{"text": "...", "start": 0.0, "duration": 2.5}, ...]
            transcript_text = " ".join(item["text"] for item in transcript_data)

            # Try to get video title from transcript metadata (if available)
            title = DEFAULT_TITLE
            try:
                # youtube-transcript-api doesn't provide title directly
                # We could use YouTube Data API for this, but that requires API key
                # For now, use video ID as fallback title
                title = f"YouTube Video: {video_id}"
            except Exception:  # noqa: BLE001 - Best effort title extraction
                logger.debug("youtube_title_extraction_failed", video_id=video_id)

            word_count = len(transcript_text.split())

            logger.info(
                "youtube_extraction_success",
                url=url,
                video_id=video_id,
                transcript_length=len(transcript_text),
                word_count=word_count,
                language=transcript.language if transcript else "unknown",
            )

            return {
                "title": title,
                "content": transcript_text,
                "word_count": word_count,
                "metadata": {
                    "extractor": "youtube_transcript",
                    "source_url": url,
                    "video_id": video_id,
                    "transcript_length": len(transcript_text),
                    "language": transcript.language if transcript else "unknown",
                    "raw_content_length": len(transcript_text),
                    "cleaned_content_length": len(transcript_text),
                },
            }

        except TranscriptsDisabled as e:
            error_msg = f"Transcripts are disabled for video: {url}"
            logger.exception(
                "youtube_transcript_disabled",
                url=url,
                video_id=video_id,
                error=str(e),
            )
            raise JinaReaderError(
                error_msg, error_code=ExtractionErrorCode.TRANSCRIPT_DISABLED
            ) from e

        except NoTranscriptFound as e:
            error_msg = f"No transcript found for video: {url}"
            logger.exception(
                "youtube_no_transcript",
                url=url,
                video_id=video_id,
                error=str(e),
            )
            raise JinaReaderError(error_msg, error_code=ExtractionErrorCode.NO_TRANSCRIPT) from e

        except Exception as e:
            error_msg = f"YouTube transcript extraction failed for {url}: {type(e).__name__}: {e!s}"
            logger.exception(
                "youtube_extraction_failed",
                url=url,
                video_id=video_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise JinaReaderError(error_msg) from e

    async def close(self) -> None:
        """Close any resources (YouTube extractor doesn't need cleanup)."""

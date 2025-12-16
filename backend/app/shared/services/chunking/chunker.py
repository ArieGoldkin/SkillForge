"""Heading-aware, dynamic chunking with overlap for coarse/fine splits."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tiktoken

if TYPE_CHECKING:
    from app.shared.services.chunking.parsers import ContentParser

DEFAULT_SHORT_WINDOW = 900
DEFAULT_LONG_WINDOW = 600
DEFAULT_OVERLAP_PCT = 0.12
DEFAULT_MAX_COARSE = 500
DEFAULT_MAX_FINE = 2000
DEFAULT_MAX_TOKENS = 7500  # Hard limit per chunk (below 8K OpenAI API limit)


@dataclass
class ChunkText:
    """A single text chunk with hierarchical path and granularity metadata.

    Attributes:
        text: The chunk text content
        path: Hierarchical path (e.g., ["section", "subsection"])
        section_title: Title of the containing section
        granularity: Chunk granularity level ("coarse", "fine", or "summary")
        chunk_idx: Zero-based index within the section
        chunk_total: Total chunks in this section
        token_count: Actual token count (populated during chunking)
        was_truncated: Whether content was truncated to fit token budget
        content_hash: SHA256 hash for deduplication (computed during chunking)

    """

    text: str
    path: list[str]
    section_title: str | None
    granularity: str  # "coarse" | "fine" | "summary"
    chunk_idx: int
    chunk_total: int
    # Telemetry fields (Issue #215)
    token_count: int = 0
    was_truncated: bool = False
    content_hash: str = ""


def _encode(text: str) -> list[int]:
    encoding = tiktoken.get_encoding("cl100k_base")
    return encoding.encode(text)


def _token_count(text: str) -> int:
    return len(_encode(text))


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of normalized text for deduplication.

    Note: This hash is content-only. For model-aware hashing that triggers
    re-embedding on model change, use compute_chunk_hash() from dedup.py
    which includes model and version in the hash.
    """
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def _truncate_to_token_limit(text: str, max_tokens: int) -> tuple[str, int, bool]:
    """Truncate text to fit within token budget if needed.

    Returns:
        Tuple of (text, token_count, was_truncated)

    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    token_count = len(tokens)

    if token_count <= max_tokens:
        return text, token_count, False

    # Truncate to max_tokens
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)
    return truncated_text, max_tokens, True


def _window_size(total_tokens: int, short_window: int, long_window: int, threshold: int) -> int:
    return short_window if total_tokens <= threshold else long_window


def _split_to_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def _split_paragraphs_into_windows(
    paragraphs: Sequence[str],
    window_tokens: int,
    overlap_pct: float,
) -> list[str]:
    if not paragraphs:
        return []

    encoding = tiktoken.get_encoding("cl100k_base")
    windows: list[str] = []
    overlap_tokens = max(1, int(window_tokens * overlap_pct))

    buffer_tokens: list[int] = []
    buffer_text: list[str] = []

    for para in paragraphs:
        tokens = encoding.encode(para)
        if len(tokens) >= window_tokens:
            # Flush current buffer first
            if buffer_tokens:
                windows.append(encoding.decode(buffer_tokens))
                buffer_tokens = []
                buffer_text = []

            # Split long paragraph into windows with overlap
            start = 0
            while start < len(tokens):
                end = min(start + window_tokens, len(tokens))
                win_tokens = tokens[start:end]
                windows.append(encoding.decode(win_tokens))
                start = (
                    max(end - overlap_tokens, end) if end == len(tokens) else end - overlap_tokens
                )
            continue

        # If buffer + para fits, append; else flush buffer
        if len(buffer_tokens) + len(tokens) <= window_tokens:
            buffer_tokens.extend(tokens)
            buffer_text.append(para)
        else:
            if buffer_tokens:
                windows.append(encoding.decode(buffer_tokens))
            buffer_tokens = tokens.copy()
            buffer_text = [para]

    if buffer_tokens:
        windows.append(encoding.decode(buffer_tokens))

    return windows


def build_chunks(  # noqa: PLR0913
    text: str,
    *,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
    overlap_pct: float = DEFAULT_OVERLAP_PCT,
    long_threshold_tokens: int = 4000,
    section_title: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    parser: ContentParser | None = None,
    content_type: str | None = None,
) -> tuple[list[ChunkText], list[ChunkText]]:
    """Produce coarse and fine chunks with path metadata and token validation.

    Args:
        text: Document text to chunk
        short_window: Token window for short documents
        long_window: Token window for long documents
        overlap_pct: Overlap percentage between windows (0.0-1.0)
        long_threshold_tokens: Token count threshold to switch windows
        section_title: Optional section title for path metadata
        max_tokens: Hard limit for tokens per chunk (default 7500)
        parser: Optional ContentParser for format-aware pre-splitting (e.g., MarkdownParser)
        content_type: Optional content type hint for parser (e.g., "text/markdown")

    Returns:
        Tuple of (coarse_chunks, fine_chunks) with token metadata populated

    """
    if not text or not text.strip():
        return [], []

    # Use parser if provided, otherwise fall back to paragraph splitting
    if parser is not None:
        sections = parser.parse(text, content_type)
        # Convert parsed sections to paragraph-like units for downstream processing
        paragraphs = [s.content for s in sections if s.content.strip()]
        # If parser produced nothing, fall back to default splitting
        if not paragraphs:
            paragraphs = _split_to_paragraphs(text)
    else:
        paragraphs = _split_to_paragraphs(text)
    total_tokens = _token_count(text)
    window_tokens = _window_size(total_tokens, short_window, long_window, long_threshold_tokens)

    coarse_chunks: list[ChunkText] = []
    # Coarse: one per top-level paragraph block
    for idx, para in enumerate(paragraphs):
        # Enforce token budget and track truncation
        chunk_text, token_count, was_truncated = _truncate_to_token_limit(para, max_tokens)
        coarse_chunks.append(
            ChunkText(
                text=chunk_text,
                path=[section_title or "root"],
                section_title=section_title,
                granularity="coarse",
                chunk_idx=idx,
                chunk_total=len(paragraphs),
                token_count=token_count,
                was_truncated=was_truncated,
                content_hash=compute_content_hash(chunk_text),
            )
        )

    fine_texts = _split_paragraphs_into_windows(paragraphs, window_tokens, overlap_pct)
    fine_chunks: list[ChunkText] = []
    for idx, raw_chunk_text in enumerate(fine_texts):
        # Enforce token budget and track truncation
        chunk_text, token_count, was_truncated = _truncate_to_token_limit(
            raw_chunk_text, max_tokens
        )
        fine_chunks.append(
            ChunkText(
                text=chunk_text,
                path=[section_title or "root"],
                section_title=section_title,
                granularity="fine",
                chunk_idx=idx,
                chunk_total=len(fine_texts),
                token_count=token_count,
                was_truncated=was_truncated,
                content_hash=compute_content_hash(chunk_text),
            )
        )

    return coarse_chunks, fine_chunks


def chunk_document(  # noqa: PLR0913
    text: str,
    *,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
    overlap_pct: float = DEFAULT_OVERLAP_PCT,
    long_threshold_tokens: int = 4000,
    max_coarse: int = DEFAULT_MAX_COARSE,
    max_fine: int = DEFAULT_MAX_FINE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    parser: ContentParser | None = None,
    content_type: str | None = None,
) -> tuple[list[ChunkText], list[ChunkText]]:
    """Chunk a full document into coarse and fine lists with optional caps.

    Args:
        text: Document text to chunk
        short_window: Token window for short documents
        long_window: Token window for long documents
        overlap_pct: Overlap percentage between windows (0.0-1.0)
        long_threshold_tokens: Token count threshold to switch windows
        max_coarse: Maximum number of coarse chunks (truncates if exceeded)
        max_fine: Maximum number of fine chunks (truncates if exceeded)
        max_tokens: Hard limit for tokens per chunk (default 7500)
        parser: Optional ContentParser for format-aware pre-splitting (e.g., MarkdownParser)
        content_type: Optional content type hint for parser (e.g., "text/markdown")

    Returns:
        Tuple of (coarse_chunks, fine_chunks), each capped at their max

    """
    coarse_chunks, fine_chunks = build_chunks(
        text,
        short_window=short_window,
        long_window=long_window,
        overlap_pct=overlap_pct,
        long_threshold_tokens=long_threshold_tokens,
        section_title=None,
        max_tokens=max_tokens,
        parser=parser,
        content_type=content_type,
    )

    # Enforce caps to prevent runaway chunk counts on very large documents
    if len(coarse_chunks) > max_coarse:
        coarse_chunks = coarse_chunks[:max_coarse]
        # Update chunk_total to reflect truncation
        for chunk in coarse_chunks:
            chunk.chunk_total = max_coarse

    if len(fine_chunks) > max_fine:
        fine_chunks = fine_chunks[:max_fine]
        # Update chunk_total to reflect truncation
        for chunk in fine_chunks:
            chunk.chunk_total = max_fine

    return coarse_chunks, fine_chunks

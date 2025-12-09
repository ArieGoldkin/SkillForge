"""Heading-aware, dynamic chunking with overlap for coarse/fine splits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import tiktoken

DEFAULT_SHORT_WINDOW = 900
DEFAULT_LONG_WINDOW = 600
DEFAULT_OVERLAP_PCT = 0.12
DEFAULT_MAX_COARSE = 500
DEFAULT_MAX_FINE = 2000


@dataclass
class ChunkText:
    text: str
    path: List[str]
    section_title: str | None
    granularity: str  # "coarse" | "fine"
    chunk_idx: int
    chunk_total: int


def _encode(text: str) -> list[int]:
    encoding = tiktoken.get_encoding("cl100k_base")
    return encoding.encode(text)


def _token_count(text: str) -> int:
    return len(_encode(text))


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
                start = max(end - overlap_tokens, end) if end == len(tokens) else end - overlap_tokens
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


def build_chunks(
    text: str,
    *,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
    overlap_pct: float = DEFAULT_OVERLAP_PCT,
    long_threshold_tokens: int = 4000,
    section_title: str | None = None,
) -> tuple[list[ChunkText], list[ChunkText]]:
    """Produce coarse and fine chunks with path metadata."""
    if not text or not text.strip():
        return [], []

    paragraphs = _split_to_paragraphs(text)
    total_tokens = _token_count(text)
    window_tokens = _window_size(total_tokens, short_window, long_window, long_threshold_tokens)

    coarse_chunks: list[ChunkText] = []
    # Coarse: one per top-level paragraph block
    for idx, para in enumerate(paragraphs):
        coarse_chunks.append(
            ChunkText(
                text=para,
                path=[section_title or "root"],
                section_title=section_title,
                granularity="coarse",
                chunk_idx=idx,
                chunk_total=len(paragraphs),
            )
        )

    fine_texts = _split_paragraphs_into_windows(paragraphs, window_tokens, overlap_pct)
    fine_chunks: list[ChunkText] = []
    for idx, chunk_text in enumerate(fine_texts):
        fine_chunks.append(
            ChunkText(
                text=chunk_text,
                path=[section_title or "root"],
                section_title=section_title,
                granularity="fine",
                chunk_idx=idx,
                chunk_total=len(fine_texts),
            )
        )

    return coarse_chunks, fine_chunks


def chunk_document(
    text: str,
    *,
    short_window: int = DEFAULT_SHORT_WINDOW,
    long_window: int = DEFAULT_LONG_WINDOW,
    overlap_pct: float = DEFAULT_OVERLAP_PCT,
    long_threshold_tokens: int = 4000,
    max_coarse: int = DEFAULT_MAX_COARSE,
    max_fine: int = DEFAULT_MAX_FINE,
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


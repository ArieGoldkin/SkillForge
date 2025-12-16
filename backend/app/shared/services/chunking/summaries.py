"""Optional section summaries for routing on very large documents."""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.services.chunking.chunker import ChunkText


@dataclass
class SummaryChunk:
    """A summary-level chunk for section routing."""

    text: str
    path: list[str]
    section_title: str | None
    granularity: str  # "summary"
    chunk_idx: int
    chunk_total: int


def summarize_sections(sections: list[ChunkText], max_len: int = 240) -> list[SummaryChunk]:
    """Create brief summaries from coarse chunks (simple heuristic: truncate)."""
    summaries: list[SummaryChunk] = []
    if not sections:
        return summaries

    for idx, section in enumerate(sections):
        snippet = section.text.strip()
        if len(snippet) > max_len:
            snippet = snippet[:max_len].rstrip() + "..."
        summaries.append(
            SummaryChunk(
                text=snippet,
                path=section.path,
                section_title=section.section_title,
                granularity="summary",
                chunk_idx=idx,
                chunk_total=len(sections),
            )
        )
    return summaries

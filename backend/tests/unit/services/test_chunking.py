import pytest

from app.services.chunking.chunker import chunk_document
from app.services.chunking.dedup import deduplicate


def test_chunk_document_produces_coarse_and_fine():
    text = "Intro paragraph.\n\nSecond paragraph with more words to ensure some length."
    coarse, fine = chunk_document(text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10)
    assert coarse, "expected coarse chunks"
    assert fine, "expected fine chunks"
    assert all(c.granularity == "coarse" for c in coarse)
    assert all(f.granularity == "fine" for f in fine)
    assert coarse[0].path
    assert fine[0].path


def test_dedup_removes_duplicates():
    text = "Same para.\n\nSame para."
    coarse, fine = chunk_document(text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10)
    deduped, stats = deduplicate(coarse)
    assert stats.dropped >= 1
    assert len(deduped) == 1


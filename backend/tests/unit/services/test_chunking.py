from app.services.chunking.chunker import chunk_document
from app.services.chunking.dedup import deduplicate


def test_chunk_document_produces_coarse_and_fine():
    text = "Intro paragraph.\n\nSecond paragraph with more words to ensure some length."
    coarse, fine = chunk_document(
        text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10
    )
    assert coarse, "expected coarse chunks"
    assert fine, "expected fine chunks"
    assert all(c.granularity == "coarse" for c in coarse)
    assert all(f.granularity == "fine" for f in fine)
    assert coarse[0].path
    assert fine[0].path


def test_dedup_removes_duplicates():
    text = "Same para.\n\nSame para."
    coarse, _fine = chunk_document(
        text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10
    )
    deduped, stats = deduplicate(coarse)
    assert stats.dropped >= 1
    assert len(deduped) == 1


def test_chunk_document_enforces_max_caps():
    """Verify chunk_document truncates to max_coarse and max_fine limits."""
    # Create text with many paragraphs to exceed caps
    paragraphs = [f"Paragraph {i} with some content to make it substantial." for i in range(20)]
    text = "\n\n".join(paragraphs)

    # Without caps - should produce many chunks
    coarse_all, _fine_all = chunk_document(
        text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10
    )
    assert len(coarse_all) == 20, "expect 20 coarse chunks without cap"

    # With caps - should truncate
    coarse_capped, fine_capped = chunk_document(
        text,
        short_window=50,
        long_window=40,
        overlap_pct=0.1,
        long_threshold_tokens=10,
        max_coarse=5,
        max_fine=10,
    )

    assert len(coarse_capped) == 5, "coarse chunks should be capped at 5"
    assert len(fine_capped) <= 10, "fine chunks should be capped at 10"

    # Verify chunk_total is updated to reflect truncation
    for chunk in coarse_capped:
        assert chunk.chunk_total == 5, "chunk_total should reflect cap"

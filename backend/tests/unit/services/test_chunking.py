from app.shared.services.chunking.chunker import (
    ChunkText,
    chunk_document,
    compute_content_hash,
)
from app.shared.services.chunking.dedup import (

    DatabaseDedupStats,
    compute_chunk_hash,
    deduplicate,
    deduplicate_with_hashes,
)


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


# =============================================================================
# Issue #215: Token Metadata Tests
# =============================================================================


def test_chunk_has_token_count():
    """Verify chunks have token_count populated (Issue #215)."""
    text = "This is a test paragraph.\n\nAnother paragraph here."
    coarse, fine = chunk_document(
        text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10
    )

    assert all(c.token_count > 0 for c in coarse), "coarse chunks should have token_count"
    assert all(f.token_count > 0 for f in fine), "fine chunks should have token_count"


def test_chunk_has_content_hash():
    """Verify chunks have content_hash populated (Issue #215)."""
    text = "Test paragraph.\n\nSecond test."
    coarse, fine = chunk_document(
        text, short_window=50, long_window=40, overlap_pct=0.1, long_threshold_tokens=10
    )

    assert all(c.content_hash for c in coarse), "coarse chunks should have content_hash"
    assert all(f.content_hash for f in fine), "fine chunks should have content_hash"
    # Verify hash format (SHA256 = 64 hex chars)
    assert all(len(c.content_hash) == 64 for c in coarse), "hash should be 64 chars"


def test_chunk_truncation_tracking():
    """Verify was_truncated is set correctly (Issue #215)."""
    # Normal chunks should not be truncated
    text = "Short paragraph."
    coarse, _fine = chunk_document(
        text,
        short_window=1000,
        long_window=1000,
        overlap_pct=0.1,
        long_threshold_tokens=10,
        max_tokens=7500,
    )

    assert all(not c.was_truncated for c in coarse), "short chunks should not be truncated"


def test_compute_content_hash_normalization():
    """Verify content hash normalizes text (Issue #215)."""
    hash1 = compute_content_hash("Hello World")
    hash2 = compute_content_hash("  hello world  ")
    hash3 = compute_content_hash("HELLO WORLD")

    # All should produce same hash due to normalization
    assert hash1 == hash2 == hash3, "normalized text should produce same hash"


def test_compute_content_hash_different_content():
    """Verify different content produces different hashes."""
    hash1 = compute_content_hash("Hello World")
    hash2 = compute_content_hash("Goodbye World")

    assert hash1 != hash2, "different content should produce different hashes"


# =============================================================================
# Issue #215: Model-Aware Dedup Tests
# =============================================================================


def test_compute_chunk_hash_includes_model():
    """Verify chunk hash includes model info (Issue #215)."""
    text = "Test content"

    hash_v1 = compute_chunk_hash(text, "text-embedding-3-small", "v1")
    hash_v2 = compute_chunk_hash(text, "text-embedding-3-small", "v2")
    hash_large = compute_chunk_hash(text, "text-embedding-3-large", "v1")

    # Same text but different model/version should produce different hashes
    assert hash_v1 != hash_v2, "different version should produce different hash"
    assert hash_v1 != hash_large, "different model should produce different hash"


def test_deduplicate_with_hashes_filters_existing():
    """Verify database-aware dedup filters existing chunks (Issue #215)."""
    # Create test chunks
    chunks = [
        ChunkText(
            text="Chunk A",
            path=["root"],
            section_title=None,
            granularity="fine",
            chunk_idx=0,
            chunk_total=3,
            token_count=5,
            was_truncated=False,
            content_hash="",
        ),
        ChunkText(
            text="Chunk B",
            path=["root"],
            section_title=None,
            granularity="fine",
            chunk_idx=1,
            chunk_total=3,
            token_count=5,
            was_truncated=False,
            content_hash="",
        ),
        ChunkText(
            text="Chunk C",
            path=["root"],
            section_title=None,
            granularity="fine",
            chunk_idx=2,
            chunk_total=3,
            token_count=5,
            was_truncated=False,
            content_hash="",
        ),
    ]

    model = "text-embedding-3-small"
    version = "v1"

    # Simulate existing hashes in database (Chunk A exists)
    existing_hashes = {compute_chunk_hash("Chunk A", model, version)}

    new_chunks, stats = deduplicate_with_hashes(chunks, existing_hashes, model, version)

    assert len(new_chunks) == 2, "should filter out existing chunk"
    assert stats.total == 3
    assert stats.skipped == 1
    assert stats.to_embed == 2
    assert isinstance(stats, DatabaseDedupStats)


def test_deduplicate_with_hashes_empty_existing():
    """Verify dedup passes all chunks when no existing hashes."""
    chunks = [
        ChunkText(
            text="New chunk",
            path=["root"],
            section_title=None,
            granularity="fine",
            chunk_idx=0,
            chunk_total=1,
            token_count=5,
            was_truncated=False,
            content_hash="",
        ),
    ]

    new_chunks, stats = deduplicate_with_hashes(chunks, set(), "text-embedding-3-small", "v1")

    assert len(new_chunks) == 1, "all chunks should pass with no existing hashes"
    assert stats.skipped == 0


def test_deduplicate_with_hashes_all_existing():
    """Verify dedup filters all chunks when all exist."""
    chunks = [
        ChunkText(
            text="Existing",
            path=["root"],
            section_title=None,
            granularity="fine",
            chunk_idx=0,
            chunk_total=1,
            token_count=5,
            was_truncated=False,
            content_hash="",
        ),
    ]

    model = "text-embedding-3-small"
    version = "v1"
    existing_hashes = {compute_chunk_hash("Existing", model, version)}

    new_chunks, stats = deduplicate_with_hashes(chunks, existing_hashes, model, version)

    assert len(new_chunks) == 0, "no chunks should pass when all exist"
    assert stats.total == 1
    assert stats.skipped == 1
    assert stats.to_embed == 0

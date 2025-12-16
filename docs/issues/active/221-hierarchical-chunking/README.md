# Issue 221 – Hierarchical Chunking & Coarse-to-Fine Retrieval

## Summary
- Add heading/paragraph-aware chunking with dynamic token windows and overlap.
- Add shingle/hash dedup before embedding.
- Store dual-granularity embeddings (coarse section-level, fine window/paragraph) plus optional section summaries.
- Attach path-rich metadata (section → subsection → chunk_idx/total) and model/version/hash to each chunk.
- Provide a coarse-to-fine retrieval helper (coarse first, then fine within top sections).
- Add config knobs and telemetry for chunking/dedup/summaries.

## Goals
- Reduce truncation and improve recall on large docs while keeping small-doc latency low.
- Keep structure: section-aware paths for re-rank and better snippets.
- Lower cost and index bloat via dedup and chunk caps.
- Enable coarse-to-fine routing to cut noise/latency for big docs.

## Scope
- Chunker: heading/paragraph-aware; dynamic windows (e.g., 384–768 long, 700–1,000 short), ~10–15% overlap; configurable.
- Dedup: shingle-based dedup with metrics.
- Dual granularity: coarse + fine; optional section summaries (config flag).
- Metadata: path, section/title, chunk_idx/total, content_type, language, model/version, hash, granularity, snippet, timestamps.
- Workflow tasks: `chunk_content` (new), `generate_embedding` (batch-aware update), `store_embeddings` (new).
- Retrieval helper: coarse-to-fine helper (library-level) to constrain fine search to top coarse sections and return path/snippets (API wiring in #216).
- Config knobs: window sizes, overlap, doc-length threshold, enable summaries, enable coarse-to-fine, dedup on/off, max chunk caps; reuse embedding batch/concurrency.
- Telemetry/logs: chunk counts (coarse/fine/summary), dedup hit rate, truncation rate, chunking latency; no raw text.

## Out of Scope
- Full search API wiring (handled in #216).
- Frontend changes.
- Multi-vector/late interaction, heavy quantization (future/elsewhere).

## Deliverables
- `services/chunking/`: `chunker.py`, `dedup.py`, `summaries.py`.
- `workflows/tasks/`: `chunk_content.py` (new), `generate_embedding.py` (updated to batch lists), `store_embeddings.py` (new).
- `workflows/utils/retrieval_routing.py`: coarse-to-fine helper.
- Config additions for chunking/dedup/summaries/coarse-to-fine.
- Telemetry hooks for chunking/dedup.
- Design note (this README) with defaults/metadata contract/usage.

## Data shapes (contract)
```python
ChunkMeta = {
  "analysis_id": str,
  "chunk_id": str,
  "granularity": "coarse" | "fine" | "summary",
  "path": list[str],          # e.g., ["Intro", "Background"]
  "chunk_idx": int,
  "chunk_total": int,
  "section_title": str | None,
  "content_type": str | None,
  "language": str | None,
  "hash": str,
  "model": str | None,
  "model_version": str | None,
  "snippet": str | None,
}

ChunkPayload = {
  "text": str,
  "metadata": ChunkMeta,
}
```

## Implementation outline
1) Chunking & dedup
   - Build chunker (heading/paragraph-aware, dynamic windows, overlap).
   - Add shingle dedup; emit stats.
   - Optional section summaries with `granularity="summary"`.
2) Workflow tasks
   - `chunk_content`: run chunker/dedup/summaries → coarse/fine/(summary) payloads.
   - `generate_embedding`: accept lists, batch, attach model/version/hash, normalize, dimension-check.
   - `store_embeddings`: persist coarse/fine/summary with path/granularity/model/version/hash.
3) Retrieval helper
   - Coarse-to-fine helper: retrieve coarse first, then fine within top sections; include path/snippets.
4) Config & telemetry
   - Knobs: window sizes, overlap, doc-length threshold, summaries on/off, coarse-to-fine on/off, dedup on/off, max chunk caps; reuse embedding batch/concurrency.
   - Metrics/logs: chunk counts, dedup hit rate, truncation rate, chunking latency; no raw text.
5) Tests (for this issue)
   - Unit: chunker (window/overlap/path/idx-total), dedup (drops repeats, stats), summaries (granularity/path), metadata fill, config toggles.
   - Task-level: chunk_content outputs; generate_embedding batches/metadata/normalize; store_embeddings persists and guards vector length.
   - Integration-ish: mock chunk→embed→store; coarse-to-fine helper restricts fine to top coarse sections and returns path/snippets.
   - Telemetry: hooks emit metrics/logs without raw text.
   - (Full retrieval smoke suite is in #223.)

## Config (proposed)
- `CHUNK_WINDOW_SHORT`, `CHUNK_WINDOW_LONG`, `CHUNK_OVERLAP_PCT`
- `DOC_LENGTH_THRESHOLD`
- `ENABLE_SUMMARIES`, `ENABLE_COARSE_TO_FINE`, `DEDUP_ENABLED`
- `MAX_CHUNKS_COARSE`, `MAX_CHUNKS_FINE`
- Reuse embedding batch/concurrency/retry settings.

## Acceptance Criteria
- Truncation rare; chunk counts/overlap logged.
- Dedup reduces repeats; dedup metric emitted.
- Coarse/fine (and summaries if enabled) persisted with path/granularity; model/version recorded.
- Coarse-to-fine helper returns fine hits restricted to top coarse sections with path/snippets.
- Docs updated with defaults/metadata contract/operational guidance.

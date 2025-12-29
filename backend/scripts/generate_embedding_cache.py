#!/usr/bin/env python3
"""Generate pre-computed embeddings for CI evaluation.

This script creates a cache of embeddings for test fixtures to avoid
regenerating them during CI runs, significantly reducing API costs and runtime.

The cache includes embeddings for:
- All document sections from documents_expanded.json (421 sections)
- All queries from queries_expanded.json (208 queries)
- All golden dataset content:
  - Document chunks (415 chunks)
  - Artifact markdown content (112 artifacts)
  - Analysis titles and metadata
- Total: ~1200+ unique text embeddings after deduplication

Embeddings are deduplicated by SHA256 hash of the text content to avoid
storing duplicate vectors for identical text.

Benefits:
- Reduces CI runtime by ~2-3 minutes per evaluation run
- Eliminates OpenAI API costs during CI (saves ~$0.003 per run)
- Ensures deterministic test results across CI runs
- Enables offline development and testing

Usage:
    # Generate cache (requires OPENAI_API_KEY)
    poetry run python scripts/generate_embedding_cache.py

    # Verify cache coverage without regenerating
    poetry run python scripts/generate_embedding_cache.py --verify

    # Force regeneration even if cache exists
    poetry run python scripts/generate_embedding_cache.py --force

Output:
    tests/smoke/retrieval/fixtures/embeddings_cache.json (~6-8 MB)

Cache Schema:
    {
        "version": "1.0",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "generated_at": "ISO timestamp",
        "embeddings": {
            "<sha256_hash>": {
                "text_preview": "first 100 chars...",
                "vector": [float, ...]
            }
        }
    }

Implementation Details:
- Uses asyncio for concurrent embedding generation
- Includes rate limiting (20 requests/second) to avoid API throttling
- Progress bar via tqdm for visibility during generation
- Comprehensive error handling with graceful degradation
- Validates cache structure on verification
- Reports coverage metrics and missing embeddings

Integration:
After generation, update test code to use CachedEmbeddingService:

    from app.shared.services.embeddings import CachedEmbeddingService

    embedding_service = CachedEmbeddingService(
        cache_path="tests/smoke/retrieval/fixtures/embeddings_cache.json"
    )

    # Now embeddings are loaded from cache instead of API
    embedding = await embedding_service.generate_embedding("query text")
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash of text for deduplication.

    Args:
        text: The text content to hash

    Returns:
        Hex string of SHA256 hash

    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_documents(fixtures_dir: Path) -> list[str]:
    """Load all document section content from fixtures.

    Args:
        fixtures_dir: Path to fixtures directory

    Returns:
        List of text content strings

    """
    documents_path = fixtures_dir / "documents_expanded.json"

    if not documents_path.exists():
        print(f"ERROR: {documents_path} not found")
        sys.exit(1)

    with documents_path.open() as f:
        data = json.load(f)

    return [
        section["content"]
        for doc in data.get("documents", [])
        for section in doc.get("sections", [])
        if section.get("content")
    ]


def load_queries(fixtures_dir: Path) -> list[str]:
    """Load all query text from fixtures.

    Args:
        fixtures_dir: Path to fixtures directory

    Returns:
        List of query strings

    """
    queries_path = fixtures_dir / "queries_expanded.json"

    if not queries_path.exists():
        print(f"ERROR: {queries_path} not found")
        sys.exit(1)

    with queries_path.open() as f:
        data = json.load(f)

    return [query["query"] for query in data.get("queries", []) if query.get("query")]


def load_golden_dataset(backend_root: Path) -> dict[str, list[str]]:
    """Load all embeddable content from golden dataset.

    Args:
        backend_root: Path to backend root directory

    Returns:
        Dictionary mapping source type to list of text content

    """
    golden_path = backend_root / "data/golden_dataset_backup.json"
    metadata_path = backend_root / "app/evaluation/datasets/agent_analysis_golden_v2.json"

    texts_by_source: dict[str, list[str]] = {
        "chunks": [],
        "artifacts": [],
        "titles": [],
    }

    # Load main golden dataset backup with chunks and artifacts
    if golden_path.exists():
        with golden_path.open() as f:
            data = json.load(f)

        # Extract chunks (snippet field contains the text)
        chunks = data.get("data", {}).get("chunks", [])
        for chunk in chunks:
            if chunk.get("snippet"):
                texts_by_source["chunks"].append(chunk["snippet"])

        # Extract artifacts (markdown_content field)
        artifacts = data.get("data", {}).get("artifacts", [])
        for artifact in artifacts:
            if artifact.get("markdown_content"):
                texts_by_source["artifacts"].append(artifact["markdown_content"])

        # Extract analysis titles
        analyses = data.get("data", {}).get("analyses", [])
        for analysis in analyses:
            if analysis.get("title"):
                texts_by_source["titles"].append(analysis["title"])

        print("Loaded from golden dataset backup:")
        print(f"  - {len(texts_by_source['chunks'])} chunks")
        print(f"  - {len(texts_by_source['artifacts'])} artifacts")
        print(f"  - {len(texts_by_source['titles'])} analysis titles")
    else:
        print(f"WARNING: Golden dataset backup not found at {golden_path}")

    # Optionally load metadata file for additional titles
    if metadata_path.exists():
        with metadata_path.open() as f:
            metadata = json.load(f)

        examples = metadata.get("examples", [])
        for example in examples:
            if example.get("title") and example["title"] not in texts_by_source["titles"]:
                texts_by_source["titles"].append(example["title"])

        print(f"  - {len(examples)} titles from metadata (deduplicated)")
    else:
        print(f"WARNING: Golden dataset metadata not found at {metadata_path}")

    return texts_by_source


def deduplicate_texts(texts: list[str]) -> dict[str, str]:
    """Deduplicate texts by SHA256 hash.

    Args:
        texts: List of text strings

    Returns:
        Dictionary mapping hash to text content

    """
    unique_texts: dict[str, str] = {}
    for text in texts:
        text_hash = compute_text_hash(text)
        if text_hash not in unique_texts:
            unique_texts[text_hash] = text

    return unique_texts


async def generate_cache(force: bool = False) -> int:
    """Generate embedding cache from fixtures.

    Args:
        force: If True, regenerate even if cache exists

    Returns:
        Exit code (0 for success)

    """
    from app.core.logging import get_logger
    from app.shared.services.embeddings import EmbeddingService

    logger = get_logger(__name__)

    # Determine paths
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    cache_path = fixtures_dir / "embeddings_cache.json"

    # Check if cache exists
    if cache_path.exists() and not force:
        logger.info(f"Cache already exists at {cache_path}")
        logger.info("Use --force to regenerate or --verify to check coverage")
        print(f"\nCache already exists: {cache_path}")
        print("Use --force to regenerate or --verify to check coverage")
        return 0

    # Load fixtures
    print("\n" + "=" * 60)
    print("LOADING FIXTURES")
    print("=" * 60)

    backend_root = Path(__file__).parent.parent
    document_texts = load_documents(fixtures_dir)
    query_texts = load_queries(fixtures_dir)
    golden_texts = load_golden_dataset(backend_root)

    print("\nFixture summary:")
    print(f"  - {len(document_texts)} document sections")
    print(f"  - {len(query_texts)} queries")
    print(f"  - {len(golden_texts['chunks'])} golden dataset chunks")
    print(f"  - {len(golden_texts['artifacts'])} golden dataset artifacts")
    print(f"  - {len(golden_texts['titles'])} golden dataset titles")

    # Combine all texts
    all_texts = (
        document_texts
        + query_texts
        + golden_texts["chunks"]
        + golden_texts["artifacts"]
        + golden_texts["titles"]
    )

    print(f"\nTotal texts before deduplication: {len(all_texts)}")

    # Deduplicate
    print("\n" + "=" * 60)
    print("DEDUPLICATING TEXTS")
    print("=" * 60)

    unique_texts = deduplicate_texts(all_texts)

    print(f"Unique texts after deduplication: {len(unique_texts)}")
    print(f"Duplicates removed: {len(all_texts) - len(unique_texts)}")

    # Initialize embedding service
    print("\n" + "=" * 60)
    print("GENERATING EMBEDDINGS")
    print("=" * 60)

    try:
        embedding_service = EmbeddingService()
    except ValueError as e:
        logger.exception("Failed to initialize embedding service")
        print(f"\nERROR: {e}")
        print("Set OPENAI_API_KEY environment variable to generate embeddings")
        return 1

    # Generate embeddings with progress bar
    cache_data: dict[str, Any] = {
        "version": "1.0",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "generated_at": datetime.now(UTC).isoformat(),
        "embeddings": {},
    }

    # Process texts with progress bar
    text_items = list(unique_texts.items())
    failed_count = 0

    for text_hash, text in tqdm(text_items, desc="Generating embeddings", unit="text"):
        try:
            # Generate embedding with normalization
            embedding = await embedding_service.generate_embedding(
                text=text,
                normalize=True,
            )

            # Store in cache
            cache_data["embeddings"][text_hash] = {
                "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
                "vector": embedding,
            }

            # Add small delay to respect rate limits (adjust as needed)
            await asyncio.sleep(0.05)  # 20 requests/second

        except Exception as e:
            logger.warning(f"Failed to generate embedding for hash {text_hash[:8]}: {e}")
            failed_count += 1
            continue

    # Close embedding service
    await embedding_service.close()

    # Write cache to disk
    print("\n" + "=" * 60)
    print("WRITING CACHE")
    print("=" * 60)

    with cache_path.open("w") as f:
        json.dump(cache_data, f, indent=2)

    print(f"Cache written to: {cache_path}")
    print(f"File size: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")

    # Summary
    print("\n" + "=" * 60)
    print("CACHE GENERATION COMPLETE")
    print("=" * 60)
    print("\nSource breakdown (before deduplication):")
    print(f"  - Document sections: {len(document_texts)}")
    print(f"  - Queries: {len(query_texts)}")
    print(f"  - Golden chunks: {len(golden_texts['chunks'])}")
    print(f"  - Golden artifacts: {len(golden_texts['artifacts'])}")
    print(f"  - Golden titles: {len(golden_texts['titles'])}")
    print(f"  - Total: {len(all_texts)}")
    print("\nDeduplication results:")
    print(f"  - Unique texts: {len(unique_texts)}")
    print(f"  - Duplicates removed: {len(all_texts) - len(unique_texts)}")
    print("\nEmbedding generation:")
    print(f"  - Embeddings generated: {len(cache_data['embeddings'])}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Success rate: {(len(cache_data['embeddings']) / len(unique_texts) * 100):.1f}%")
    print("\nCache metadata:")
    print(f"  - Model: {cache_data['model']}")
    print(f"  - Dimensions: {cache_data['dimensions']}")
    print(f"  - File size: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")
    print("=" * 60)

    return 0 if failed_count == 0 else 1


def validate_embedding_structure(
    cache_data: dict[str, Any],
) -> list[str]:
    """Validate cache structure and return list of errors.

    Args:
        cache_data: The loaded cache data

    Returns:
        List of validation error messages

    """
    validation_errors: list[str] = []
    expected_dims = cache_data.get("dimensions", 1536)

    for text_hash, embedding_data in cache_data.get("embeddings", {}).items():
        if not isinstance(embedding_data, dict):
            validation_errors.append(f"Invalid embedding data type for {text_hash[:8]}")
            continue

        if "vector" not in embedding_data:
            validation_errors.append(f"Missing vector for {text_hash[:8]}")
            continue

        vector = embedding_data["vector"]
        if not isinstance(vector, list):
            validation_errors.append(f"Invalid vector type for {text_hash[:8]}")
            continue

        if len(vector) != expected_dims:
            validation_errors.append(
                f"Wrong dimensions for {text_hash[:8]}: {len(vector)} != {expected_dims}"
            )

    return validation_errors


async def verify_cache() -> int:
    """Verify cache coverage without regenerating.

    Returns:
        Exit code (0 for success)

    """
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    # Determine paths
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    cache_path = fixtures_dir / "embeddings_cache.json"

    # Check if cache exists
    if not cache_path.exists():
        logger.error(f"Cache not found at {cache_path}")
        print(f"\nERROR: Cache not found at {cache_path}")
        print("Run without --verify to generate the cache")
        return 1

    # Load cache
    with cache_path.open() as f:
        cache_data = json.load(f)

    # Load fixtures
    backend_root = Path(__file__).parent.parent
    document_texts = load_documents(fixtures_dir)
    query_texts = load_queries(fixtures_dir)
    golden_texts = load_golden_dataset(backend_root)

    # Combine all texts
    all_texts = (
        document_texts
        + query_texts
        + golden_texts["chunks"]
        + golden_texts["artifacts"]
        + golden_texts["titles"]
    )
    unique_texts = deduplicate_texts(all_texts)

    # Check coverage
    print("\n" + "=" * 60)
    print("CACHE VERIFICATION")
    print("=" * 60)
    print(f"Cache file: {cache_path}")
    print(f"Generated: {cache_data.get('generated_at', 'unknown')}")
    print(f"Model: {cache_data.get('model', 'unknown')}")
    print(f"Dimensions: {cache_data.get('dimensions', 'unknown')}")
    print()

    cached_hashes = set(cache_data.get("embeddings", {}).keys())
    required_hashes = set(unique_texts.keys())

    missing_hashes = required_hashes - cached_hashes
    extra_hashes = cached_hashes - required_hashes

    print("Source breakdown:")
    print(f"  - Document sections: {len(document_texts)}")
    print(f"  - Queries: {len(query_texts)}")
    print(f"  - Golden chunks: {len(golden_texts['chunks'])}")
    print(f"  - Golden artifacts: {len(golden_texts['artifacts'])}")
    print(f"  - Golden titles: {len(golden_texts['titles'])}")
    print(f"  - Total before dedup: {len(all_texts)}")
    print()
    print("Coverage Analysis:")
    print(f"  - Required texts (unique): {len(required_hashes)}")
    print(f"  - Cached embeddings: {len(cached_hashes)}")
    print(f"  - Coverage: {len(cached_hashes & required_hashes)}/{len(required_hashes)}")
    print(
        f"  - Coverage rate: {(len(cached_hashes & required_hashes) / len(required_hashes) * 100):.1f}%"
    )
    print()

    if missing_hashes:
        print(f"WARNING: {len(missing_hashes)} texts missing from cache")
        print("Sample missing text previews:")
        for text_hash in list(missing_hashes)[:3]:
            text = unique_texts[text_hash]
            preview = text[:80] + ("..." if len(text) > 80 else "")
            print(f"  - {text_hash[:8]}... : {preview}")
        print()

    if extra_hashes:
        print(f"WARNING: {len(extra_hashes)} extra embeddings in cache (not in fixtures)")
        print("These may be from old fixture versions")
        print()

    # Validate cache structure
    print("Structure Validation:")
    validation_errors = validate_embedding_structure(cache_data)

    if validation_errors:
        print(f"  Validation errors: {len(validation_errors)}")
        for error in validation_errors[:5]:
            print(f"    - {error}")
        if len(validation_errors) > 5:
            print(f"    ... and {len(validation_errors) - 5} more")
    else:
        print("  All embeddings valid")

    print()

    # Summary
    print("=" * 60)
    if missing_hashes or extra_hashes or validation_errors:
        print("CACHE HAS ISSUES")
        print("=" * 60)
        print("Run without --verify to regenerate the cache")
        return 1

    print("CACHE IS VALID")
    print("=" * 60)
    print(f"File size: {cache_path.stat().st_size / 1024 / 1024:.2f} MB")
    print("Ready for use in CI evaluations")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate or verify embedding cache for CI evaluation"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify cache coverage without regenerating",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if cache exists",
    )

    args = parser.parse_args()

    if args.verify:
        exit_code = asyncio.run(verify_cache())
    else:
        exit_code = asyncio.run(generate_cache(force=args.force))

    sys.exit(exit_code)

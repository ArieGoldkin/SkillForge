#!/usr/bin/env python3
"""Regenerate all derived data from the canonical golden dataset backup.

This script provides a unified way to regenerate:
1. PostgreSQL database content (analyses, artifacts, chunks)
2. Test fixtures (documents.json, queries.json, source_url_map.json)
3. Evaluation datasets (agent_analysis_golden.json, etc.)

All derived data is regenerated from the single source of truth:
    backend/data/golden_dataset_backup.json

Usage:
    # Regenerate everything
    poetry run python scripts/regenerate_from_canonical.py --target all

    # Regenerate specific targets
    poetry run python scripts/regenerate_from_canonical.py --target db
    poetry run python scripts/regenerate_from_canonical.py --target fixtures
    poetry run python scripts/regenerate_from_canonical.py --target eval

    # Replace existing database content
    poetry run python scripts/regenerate_from_canonical.py --target db --replace

Targets:
    db       - Restore PostgreSQL database (analyses, artifacts, chunks with embeddings)
    fixtures - Regenerate test fixtures for smoke tests
    eval     - Regenerate evaluation datasets for quality testing
    all      - All of the above

Notes:
    - Database restoration regenerates embeddings (requires OpenAI API)
    - Use --replace to clear existing database content before restoring
    - Fixtures are always overwritten when regenerated
    - Evaluation datasets are always overwritten when regenerated

"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# File paths
CANONICAL_BACKUP = Path(__file__).parent.parent / "data/golden_dataset_backup.json"
FIXTURES_DIR = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
EVAL_DIR = Path(__file__).parent.parent / "app/evaluation/datasets"


def load_canonical_backup() -> dict[str, Any]:
    """Load the canonical backup file.

    Returns:
        dict: The backup data with metadata and content.

    Raises:
        FileNotFoundError: If backup file doesn't exist.
        json.JSONDecodeError: If backup file is invalid JSON.

    """
    if not CANONICAL_BACKUP.exists():
        msg = (
            f"Canonical backup not found: {CANONICAL_BACKUP}\n"
            "Run 'poetry run python scripts/backup_golden_dataset.py backup' first."
        )
        raise FileNotFoundError(msg)

    with CANONICAL_BACKUP.open() as f:
        data: dict[str, Any] = json.load(f)

    # Validate backup structure
    required_keys = ["version", "created_at", "counts", "data"]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        msg = f"Invalid backup file, missing keys: {missing_keys}"
        raise ValueError(msg)

    print(f"✓ Loaded canonical backup v{data.get('version', '1.0')}")
    print(f"  Created: {data.get('created_at', 'unknown')}")
    print(f"  Analyses:  {len(data['data']['analyses'])}")
    print(f"  Artifacts: {len(data['data']['artifacts'])}")
    print(f"  Chunks:    {len(data['data']['chunks'])}")

    return data


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse ISO datetime string to datetime object.

    Args:
        value: ISO datetime string, datetime object, or None.

    Returns:
        datetime: Parsed datetime object or None.

    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle ISO format with timezone
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def regenerate_database(backup_data: dict[str, Any], replace: bool = False) -> None:
    """Regenerate PostgreSQL database from canonical backup.

    This function:
    1. Optionally clears existing data (if replace=True)
    2. Restores analyses records
    3. Restores artifacts records
    4. Restores chunks with regenerated embeddings

    Args:
        backup_data: The loaded backup data.
        replace: If True, clear existing data before restoring.

    Raises:
        Exception: If database operations fail.

    """
    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.services.embeddings import EmbeddingService

    logger = get_logger(__name__)

    print("\n📦 Regenerating database...")

    # Initialize embedding service
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        if replace:
            logger.info("Clearing existing data...")
            await session.execute(text("DELETE FROM analysis_chunks"))
            await session.execute(text("DELETE FROM artifacts"))
            await session.execute(text("DELETE FROM analyses"))
            await session.commit()
            print("  ✓ Cleared existing data")

        analyses = backup_data["data"]["analyses"]
        artifacts = backup_data["data"]["artifacts"]
        chunks = backup_data["data"]["chunks"]

        # Restore analyses
        logger.info(f"Restoring {len(analyses)} analyses...")
        for analysis in analyses:
            await session.execute(
                text("""
                    INSERT INTO analyses (id, url, content_type, title, status, created_at, updated_at)
                    VALUES (:id, :url, :content_type, :title, :status, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    **analysis,
                    "created_at": parse_datetime(analysis.get("created_at")),
                    "updated_at": parse_datetime(analysis.get("updated_at")),
                },
            )
        await session.flush()
        print(f"  ✓ Restored {len(analyses)} analyses")

        # Restore artifacts
        logger.info(f"Restoring {len(artifacts)} artifacts...")
        for artifact in artifacts:
            await session.execute(
                text("""
                    INSERT INTO artifacts (id, analysis_id, markdown_content, version, artifact_metadata, created_at)
                    VALUES (:id, :analysis_id, :markdown_content, :version, CAST(:artifact_metadata AS jsonb), :created_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    **artifact,
                    "artifact_metadata": json.dumps(artifact.get("artifact_metadata", {})),
                    "created_at": parse_datetime(artifact.get("created_at")),
                },
            )
        await session.flush()
        print(f"  ✓ Restored {len(artifacts)} artifacts")

        # Restore chunks with regenerated embeddings
        logger.info(f"Restoring {len(chunks)} chunks (regenerating embeddings)...")
        for i, chunk in enumerate(chunks):
            # Regenerate embedding
            try:
                embedding = await embedding_service.generate_embedding(
                    text=chunk["snippet"],
                    normalize=True,
                )
            except Exception as e:
                logger.warning(f"Failed to generate embedding for chunk {i}: {e}")
                continue

            # Convert embedding list to pgvector string format: '[1,2,3,...]'
            vector_str = "[" + ",".join(str(x) for x in embedding) + "]"

            chunk_created = parse_datetime(chunk.get("created_at")) or datetime.now(UTC)

            await session.execute(
                text("""
                    INSERT INTO analysis_chunks (
                        id, analysis_id, snippet, vector, granularity, section_title,
                        chunk_idx, chunk_total, path, hash, content_type, language,
                        model, model_version, created_at, updated_at
                    )
                    VALUES (
                        :id, :analysis_id, :snippet, :vector, :granularity, :section_title,
                        :chunk_idx, :chunk_total, CAST(:path AS jsonb), :hash, :content_type, :language,
                        :model, :model_version, :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    **chunk,
                    "vector": vector_str,
                    "path": json.dumps(chunk.get("path", [])),
                    "created_at": chunk_created,
                    "updated_at": chunk_created,  # Set updated_at same as created_at
                },
            )

            if (i + 1) % 50 == 0:
                await session.flush()
                print(f"    Progress: {i + 1}/{len(chunks)} chunks")

        await session.commit()

        # Verify results
        result = await session.execute(
            text("SELECT COUNT(*) FROM analyses WHERE status = 'completed'")
        )
        final_analyses = result.scalar()
        result = await session.execute(text("SELECT COUNT(*) FROM artifacts"))
        final_artifacts = result.scalar()
        result = await session.execute(text("SELECT COUNT(*) FROM analysis_chunks"))
        final_chunks = result.scalar()

        print(f"  ✓ Restored {final_chunks} chunks with regenerated embeddings")
        print("\n  Final counts:")
        print(f"    Analyses:  {final_analyses}")
        print(f"    Artifacts: {final_artifacts}")
        print(f"    Chunks:    {final_chunks}")


def regenerate_fixtures(backup_data: dict[str, Any]) -> None:
    """Regenerate test fixtures from canonical backup.

    Creates:
    - documents.json: Simplified document list (20 docs for fast smoke tests)
    - source_url_map.json: Mapping of doc_id to source_url

    Args:
        backup_data: The loaded backup data.

    """
    print("\n📋 Regenerating test fixtures...")

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    analyses = backup_data["data"]["analyses"]
    artifacts = backup_data["data"]["artifacts"]

    # Create artifact_metadata lookup
    artifact_lookup = {a["analysis_id"]: a for a in artifacts}

    # Generate documents from analyses
    documents = []
    source_url_map = {}

    for analysis in analyses:
        analysis_id = analysis["id"]
        artifact = artifact_lookup.get(analysis_id)

        if not artifact:
            continue

        # Extract document_id from artifact metadata
        metadata = artifact.get("artifact_metadata", {})
        doc_id = metadata.get("document_id")

        if not doc_id:
            # Generate doc_id from title
            title = analysis.get("title", "untitled")
            doc_id = title.lower().replace(" ", "-").replace("_", "-")[:50]

        documents.append(
            {
                "id": doc_id,
                "title": analysis.get("title", "Untitled"),
                "url": analysis.get("url", ""),
                "content_type": analysis.get("content_type", "article"),
            }
        )

        source_url_map[doc_id] = analysis.get("url", "")

    # Write documents.json (simplified, limited to 20 for fast smoke tests)
    documents_simple = documents[:20]
    documents_path = FIXTURES_DIR / "documents.json"
    with documents_path.open("w") as f:
        json.dump(
            {
                "version": "2.0",
                "generated_from": "canonical_backup",
                "generated_at": datetime.now(UTC).isoformat(),
                "documents": documents_simple,
            },
            f,
            indent=2,
        )
    print(f"  ✓ Generated documents.json ({len(documents_simple)} docs)")

    # Write source_url_map.json
    url_map_path = FIXTURES_DIR / "source_url_map.json"
    with url_map_path.open("w") as f:
        json.dump(source_url_map, f, indent=2)
    print(f"  ✓ Generated source_url_map.json ({len(source_url_map)} mappings)")

    # Note: documents_expanded.json and queries.json are maintained manually
    # as they contain detailed test data that isn't in the database backup
    print(
        "  (i) documents_expanded.json and queries.json are maintained manually (not regenerated)"
    )


def regenerate_eval_datasets(backup_data: dict[str, Any]) -> None:
    """Regenerate evaluation datasets from canonical backup.

    Creates:
    - Updated evaluation datasets based on canonical backup content

    Args:
        backup_data: The loaded backup data.

    """
    print("\n🧪 Regenerating evaluation datasets...")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    analyses = backup_data["data"]["analyses"]

    # Sample diverse analyses for evaluation
    # Group by content_type to ensure diversity
    by_type: dict[str, list[dict[str, Any]]] = {}
    for analysis in analyses:
        content_type = analysis.get("content_type", "article")
        if content_type not in by_type:
            by_type[content_type] = []
        by_type[content_type].append(analysis)

    # Take samples from each type
    eval_samples = []
    for _content_type, samples in by_type.items():
        # Take 2-3 samples per type, up to 15 total
        num_samples = min(3, len(samples))
        eval_samples.extend(samples[:num_samples])
        if len(eval_samples) >= 15:
            break

    eval_samples = eval_samples[:15]

    # Generate agent_analysis_golden_v2.json
    agent_golden = {
        "version": "2.0",
        "generated_from": "canonical_backup",
        "generated_at": datetime.now(UTC).isoformat(),
        "description": "Golden dataset examples for agent analysis evaluation",
        "examples": [
            {
                "id": a["id"],
                "url": a.get("url", ""),
                "title": a.get("title", ""),
                "content_type": a.get("content_type", ""),
                "status": a.get("status", "completed"),
                # Note: Expected outputs (core_concepts, key_takeaways, etc.)
                # would come from actual artifact content in a full implementation
            }
            for a in eval_samples
        ],
    }

    agent_golden_path = EVAL_DIR / "agent_analysis_golden_v2.json"
    with agent_golden_path.open("w") as f:
        json.dump(agent_golden, f, indent=2)
    print(f"  ✓ Updated agent_analysis_golden_v2.json ({len(eval_samples)} examples)")

    # Note: Other evaluation datasets (adversarial_v2.json, edge_cases_v2.json, etc.)
    # are manually curated test cases, not derived from the golden dataset
    print("  (i) Other evaluation datasets are manually curated (not regenerated)")


async def main() -> int:
    """Main entry point for the regeneration script.

    Returns:
        int: Exit code (0 for success, 1 for failure).

    """
    parser = argparse.ArgumentParser(
        description="Regenerate derived data from canonical golden dataset backup"
    )
    parser.add_argument(
        "--target",
        choices=["db", "fixtures", "eval", "all"],
        default="all",
        help="What to regenerate (default: all)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing database data (only applies to 'db' target)",
    )

    args = parser.parse_args()

    print("🔄 Regenerating from canonical golden dataset backup")
    print("=" * 60)

    try:
        backup_data = load_canonical_backup()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"\n❌ Error loading backup: {e}")
        return 1

    try:
        if args.target in ("db", "all"):
            await regenerate_database(backup_data, replace=args.replace)

        if args.target in ("fixtures", "all"):
            regenerate_fixtures(backup_data)

        if args.target in ("eval", "all"):
            regenerate_eval_datasets(backup_data)

        print("\n" + "=" * 60)
        print("✅ Regeneration complete!")
        print("=" * 60)

        if args.target in ("db", "all"):
            print("\nNext steps:")
            print("  1. Verify database: poetry run python scripts/backup_golden_dataset.py verify")
            print("  2. Run smoke tests: poetry run pytest tests/smoke/")

        return 0

    except Exception as e:
        print(f"\n❌ Error during regeneration: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

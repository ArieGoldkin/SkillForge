#!/usr/bin/env python3
"""Backup and restore golden dataset to/from JSON files.

This script creates portable backups of the golden dataset that can be:
- Version controlled in git
- Restored on any PostgreSQL instance
- Used for CI/CD database seeding

Usage:
    # Backup current database to JSON
    poetry run python scripts/backup_golden_dataset.py backup

    # Restore from backup
    poetry run python scripts/backup_golden_dataset.py restore [--replace]

    # Verify backup integrity
    poetry run python scripts/backup_golden_dataset.py verify

Output:
    - data/golden_dataset_backup.json (full backup)
    - data/golden_dataset_metadata.json (stats only)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle ISO format with timezone
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


class UUIDEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID objects."""

    def default(self, obj: Any) -> Any:
        """Serialize UUID and datetime objects to JSON-compatible strings."""
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def backup_dataset() -> int:
    """Export golden dataset to JSON files."""
    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal

    logger = get_logger(__name__)

    # Create data directory
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    backup_path = data_dir / "golden_dataset_backup.json"
    metadata_path = data_dir / "golden_dataset_metadata.json"

    async with AsyncSessionLocal() as session:
        # Export analyses
        #
        # IMPORTANT: Only back up the *golden dataset* subset, not all completed analyses.
        # We identify golden dataset analyses by the presence of artifact_metadata.document_id,
        # which is set by our fixture-based loader.
        result = await session.execute(
            text("""
                WITH golden AS (
                    SELECT DISTINCT analysis_id
                    FROM artifacts
                    WHERE artifact_metadata ? 'document_id'
                )
                SELECT a.id, a.url, a.content_type, a.title, a.status, a.created_at, a.updated_at
                FROM analyses a
                INNER JOIN golden g ON a.id = g.analysis_id
                WHERE a.status = 'completed'
                ORDER BY a.created_at
            """)
        )
        analyses = [dict(row._mapping) for row in result]
        logger.info(f"Exporting {len(analyses)} analyses")

        # Export artifacts
        result = await session.execute(
            text("""
                WITH golden AS (
                    SELECT DISTINCT analysis_id
                    FROM artifacts
                    WHERE artifact_metadata ? 'document_id'
                )
                SELECT art.id, art.analysis_id, art.markdown_content, art.version, art.artifact_metadata, art.created_at
                FROM artifacts art
                INNER JOIN golden g ON art.analysis_id = g.analysis_id
                ORDER BY art.created_at
            """)
        )
        artifacts = [dict(row._mapping) for row in result]
        logger.info(f"Exporting {len(artifacts)} artifacts")

        # Export chunks (without vectors for portability - they'll be regenerated)
        result = await session.execute(
            text("""
                SELECT
                    id, analysis_id, snippet, granularity, section_title,
                    chunk_idx, chunk_total, path, hash, content_type, language,
                    model, model_version, created_at
                FROM analysis_chunks
                WHERE analysis_id IN (
                    SELECT DISTINCT analysis_id
                    FROM artifacts
                    WHERE artifact_metadata ? 'document_id'
                )
                ORDER BY analysis_id, chunk_idx
            """)
        )
        chunks = [dict(row._mapping) for row in result]
        logger.info(
            f"Exporting {len(chunks)} chunks (vectors excluded - will regenerate on restore)"
        )

        # Create backup
        backup_data = {
            "version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "source": "SkillForge Golden Dataset Backup",
            "counts": {
                "analyses": len(analyses),
                "artifacts": len(artifacts),
                "chunks": len(chunks),
            },
            "data": {
                "analyses": analyses,
                "artifacts": artifacts,
                "chunks": chunks,
            },
        }

        # Write backup
        with backup_path.open("w") as f:
            json.dump(backup_data, f, cls=UUIDEncoder, indent=2)
        logger.info(f"Backup written to: {backup_path}")

        # Write metadata (for quick verification without loading full backup)
        metadata = {
            "version": "1.0",
            "created_at": datetime.now(UTC).isoformat(),
            "counts": backup_data["counts"],
            "content_types": {},
            "sample_titles": [],
        }

        # Content type distribution
        for analysis in analyses:
            ct = analysis.get("content_type", "unknown")
            metadata["content_types"][ct] = metadata["content_types"].get(ct, 0) + 1

        # Sample titles
        metadata["sample_titles"] = [a["title"] for a in analyses[:10]]

        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata written to: {metadata_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("BACKUP COMPLETE")
        print("=" * 60)
        print(f"   Analyses:  {len(analyses)}")
        print(f"   Artifacts: {len(artifacts)}")
        print(f"   Chunks:    {len(chunks)}")
        print(f"   Location:  {backup_path}")
        print("=" * 60)

        return 0


async def restore_dataset(replace: bool = False) -> int:
    """Restore golden dataset from JSON backup."""
    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.services.embeddings import EmbeddingService

    logger = get_logger(__name__)

    backup_path = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"

    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        logger.error("Run 'backup' command first or ensure backup file exists")
        return 1

    # Load backup
    with backup_path.open() as f:
        backup_data = json.load(f)

    logger.info(f"Loaded backup from: {backup_path}")
    logger.info(f"Backup version: {backup_data['version']}")
    logger.info(f"Backup created: {backup_data['created_at']}")

    analyses = backup_data["data"]["analyses"]
    artifacts = backup_data["data"]["artifacts"]
    chunks = backup_data["data"]["chunks"]

    # Initialize embedding service for regenerating vectors
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        if replace:
            logger.info("Clearing existing data...")
            await session.execute(text("DELETE FROM analysis_chunks"))
            await session.execute(text("DELETE FROM artifacts"))
            await session.execute(text("DELETE FROM analyses"))
            await session.commit()
            logger.info("Cleared existing data")

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
                logger.info(f"  Restored {i + 1}/{len(chunks)} chunks")

        await session.commit()

        # Verify
        result = await session.execute(
            text("SELECT COUNT(*) FROM analyses WHERE status = 'completed'")
        )
        final_analyses = result.scalar()
        result = await session.execute(text("SELECT COUNT(*) FROM artifacts"))
        final_artifacts = result.scalar()
        result = await session.execute(text("SELECT COUNT(*) FROM analysis_chunks"))
        final_chunks = result.scalar()

        print("\n" + "=" * 60)
        print("RESTORE COMPLETE")
        print("=" * 60)
        print(f"   Analyses:  {final_analyses}")
        print(f"   Artifacts: {final_artifacts}")
        print(f"   Chunks:    {final_chunks}")
        print("=" * 60)

        return 0


async def verify_backup() -> int:
    """Verify backup file integrity."""
    backup_path = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"

    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}")
        return 1

    # Load and verify backup
    with backup_path.open() as f:
        backup_data = json.load(f)

    analyses = backup_data["data"]["analyses"]
    artifacts = backup_data["data"]["artifacts"]
    chunks = backup_data["data"]["chunks"]

    # Verify URLs are not placeholder skillforge.dev hosts
    placeholder_prefixes = (
        "https://docs.skillforge.dev/",
        "https://learn.skillforge.dev/",
        "https://papers.skillforge.dev/",
        "https://content.skillforge.dev/",
    )
    placeholder_analyses = [
        a
        for a in analyses
        if isinstance(a.get("url"), str) and a["url"].startswith(placeholder_prefixes)
    ]

    # Verify counts
    expected = backup_data["counts"]
    actual = {
        "analyses": len(analyses),
        "artifacts": len(artifacts),
        "chunks": len(chunks),
    }

    print("\n" + "=" * 60)
    print("BACKUP VERIFICATION")
    print("=" * 60)
    print(f"   File: {backup_path}")
    print(f"   Created: {backup_data['created_at']}")
    print(f"   Version: {backup_data['version']}")
    print()
    print("   Counts:")
    print(f"     Analyses:  {actual['analyses']} (expected: {expected['analyses']})")
    print(f"     Artifacts: {actual['artifacts']} (expected: {expected['artifacts']})")
    print(f"     Chunks:    {actual['chunks']} (expected: {expected['chunks']})")
    print()

    # Verify referential integrity
    analysis_ids = {a["id"] for a in analyses}
    orphan_artifacts = [a for a in artifacts if a["analysis_id"] not in analysis_ids]
    orphan_chunks = [c for c in chunks if c["analysis_id"] not in analysis_ids]

    if orphan_artifacts or orphan_chunks:
        print(
            f"   WARNING: {len(orphan_artifacts)} orphan artifacts, {len(orphan_chunks)} orphan chunks"
        )
    else:
        print("   Referential Integrity: OK")

    if placeholder_analyses:
        print(
            f"   WARNING: {len(placeholder_analyses)} analyses still use placeholder URLs "
            f"(example: {placeholder_analyses[0].get('url')})"
        )

    # Verify all analyses have artifacts
    artifact_analysis_ids = {a["analysis_id"] for a in artifacts}
    missing_artifacts = [a for a in analyses if a["id"] not in artifact_analysis_ids]
    if missing_artifacts:
        print(f"   WARNING: {len(missing_artifacts)} analyses without artifacts")
    else:
        print("   All analyses have artifacts: OK")

    print("=" * 60)
    print(
        "BACKUP IS VALID"
        if not (orphan_artifacts or orphan_chunks or missing_artifacts or placeholder_analyses)
        else "BACKUP HAS ISSUES"
    )
    print("=" * 60)

    return (
        0
        if not (orphan_artifacts or orphan_chunks or missing_artifacts or placeholder_analyses)
        else 1
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden dataset backup/restore")
    parser.add_argument(
        "command",
        choices=["backup", "restore", "verify"],
        help="Command to execute",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing data on restore",
    )

    args = parser.parse_args()

    if args.command == "backup":
        exit_code = asyncio.run(backup_dataset())
    elif args.command == "restore":
        exit_code = asyncio.run(restore_dataset(replace=args.replace))
    elif args.command == "verify":
        exit_code = asyncio.run(verify_backup())
    else:
        print(f"Unknown command: {args.command}")
        exit_code = 1

    sys.exit(exit_code)

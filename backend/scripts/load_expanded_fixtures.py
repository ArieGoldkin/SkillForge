#!/usr/bin/env python3
"""Load expanded fixture dataset into the development database.

This script:
1. Connects to the PostgreSQL database
2. Creates embeddings for all document sections
3. Inserts chunks into the analysis_chunks table
4. Validates the data was loaded correctly

Usage:
    poetry run python scripts/load_expanded_fixtures.py [--expanded] [--replace]

Options:
    --expanded  Load from documents_expanded.json (default: documents.json)
    --replace   Clear existing chunks before loading

Requires:
    - OPENAI_API_KEY for embedding generation
    - PostgreSQL database running (see docker-compose.yml)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def main(expanded: bool = False, replace: bool = False) -> int:
    """Load fixtures into database.

    Args:
        expanded: Use expanded fixture files
        replace: Replace existing data

    Returns:
        Exit code (0 for success)

    """
    # Import after dotenv to ensure env vars are loaded
    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.models.analysis import Analysis
    from app.models.analysis_chunk import AnalysisChunk
    from app.services.embeddings import EmbeddingService

    logger = get_logger(__name__)

    # Determine fixture path
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    documents_file = "documents_expanded.json" if expanded else "documents.json"
    documents_path = fixtures_dir / documents_file

    if not documents_path.exists():
        logger.error(f"Fixture file not found: {documents_path}")
        return 1

    # Load fixtures
    logger.info(f"Loading fixtures from: {documents_path}")
    with documents_path.open() as f:
        fixture_data = json.load(f)

    documents = fixture_data["documents"]
    total_sections = sum(len(doc.get("sections", [])) for doc in documents)

    logger.info(f"Found {len(documents)} documents with {total_sections} sections")

    # Initialize services
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        # Create or get analysis record for fixtures
        analysis_id = uuid4()
        analysis_name = "expanded-fixtures" if expanded else "original-fixtures"

        # Check if we should replace existing data
        if replace:
            logger.info("Clearing existing fixture data...")
            await session.execute(
                text("""
                    DELETE FROM analysis_chunks
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE url LIKE '%fixture%' OR url LIKE '%smoke-test%'
                    )
                """)
            )
            await session.execute(
                text("""
                    DELETE FROM analyses
                    WHERE url LIKE '%fixture%' OR url LIKE '%smoke-test%'
                """)
            )
            await session.commit()
            logger.info("Cleared existing fixture data")

        # Create analysis record
        analysis = Analysis(
            id=analysis_id,
            url=f"https://fixtures.skillforge.local/{analysis_name}",
            content_type="fixture_dataset",
            status="completed",
        )
        session.add(analysis)
        await session.flush()

        logger.info(f"Created analysis record: {analysis_id}")

        # Process each document
        chunks_created = 0
        for doc_idx, doc in enumerate(documents):
            doc_id = doc["id"]
            doc_title = doc["title"]
            logger.info(f"Processing [{doc_idx + 1}/{len(documents)}]: {doc_title}")

            for section_idx, section in enumerate(doc.get("sections", [])):
                content = section["content"]
                section_id = section["id"]

                # Generate embedding
                try:
                    embedding = await embedding_service.generate_embedding(
                        text=content,
                        normalize=True,
                    )
                except Exception:
                    logger.exception(f"Failed to embed {section_id}")
                    continue

                # Create content hash
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                # Create chunk
                chunk = AnalysisChunk(
                    id=uuid4(),
                    analysis_id=analysis_id,
                    snippet=content,
                    vector=embedding,
                    granularity=section.get("granularity", "coarse"),
                    section_title=section["title"],
                    chunk_idx=section_idx,
                    chunk_total=len(doc["sections"]),
                    path=[doc_id, section_id],
                    hash=content_hash,
                    content_type=doc.get("content_type", "article"),
                    language=doc.get("language", "en"),
                    model="text-embedding-3-small",
                    model_version="v1",
                )

                session.add(chunk)
                chunks_created += 1

                # Flush periodically
                if chunks_created % 10 == 0:
                    await session.flush()
                    logger.info(f"  Created {chunks_created}/{total_sections} chunks")

        # Final commit
        await session.commit()

        # Verify
        result = await session.execute(
            text("SELECT COUNT(*) FROM analysis_chunks WHERE analysis_id = :id"),
            {"id": str(analysis_id)},
        )
        count = result.scalar()

        logger.info(f"✅ Successfully loaded {count} chunks into database")
        logger.info(f"   Analysis ID: {analysis_id}")

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load fixtures into database")
    parser.add_argument(
        "--expanded",
        action="store_true",
        help="Load expanded fixture files",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing fixture data",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(expanded=args.expanded, replace=args.replace))
    sys.exit(exit_code)

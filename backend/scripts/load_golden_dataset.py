#!/usr/bin/env python3
"""Load golden dataset with individual analyses, artifacts, and chunks.

IMPORTANT: This script creates PLACEHOLDER artifacts that should be regenerated
through the real LangGraph workflow. For production-quality artifacts:
1. Use `backup_golden_dataset.py restore` if backup exists
2. Or run real analyses through the workflow API

This script creates a proper library of completed analyses from the golden dataset,
where each document becomes its own analysis with:
- Analysis record (completed status)
- Artifact (PLACEHOLDER - needs real workflow regeneration)
- Chunks (sections with embeddings)

Usage:
    poetry run python scripts/load_golden_dataset.py [--replace]

    # Preferred: Restore from backup with real artifacts
    poetry run python scripts/backup_golden_dataset.py restore [--replace]

Options:
    --replace   Clear existing data before loading
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def generate_placeholder_artifact(doc: dict) -> str:
    """Generate a placeholder artifact that indicates real workflow is needed.

    NOTE: This creates a minimal placeholder. For real artifacts with:
    - AI Assistant prompts
    - Core concepts
    - Exercises
    - Diagrams
    - Quality validation

    Use `backup_golden_dataset.py restore` or run through the real workflow.
    """
    title = doc["title"]
    content_type = doc.get("content_type", "article")
    tags = doc.get("tags", [])
    sections = doc.get("sections", [])

    # Build minimal placeholder markdown
    md_parts = [
        f"# {title}",
        "",
        "> **⚠️ PLACEHOLDER ARTIFACT**",
        "> This artifact was created from fixture data and needs regeneration",
        "> through the real LangGraph workflow for full quality.",
        "",
        "## Overview",
        "",
    ]

    # Add intro from first section if available
    if sections:
        intro = sections[0].get("content", "")
        md_parts.append(intro)
        md_parts.append("")

    # Add section content (the real content from fixtures)
    for section in sections:
        section_title = section.get("title", "Section")
        content = section.get("content", "")
        md_parts.append(f"## {section_title}")
        md_parts.append("")
        md_parts.append(content)
        md_parts.append("")

    # Add tags
    if tags:
        md_parts.append("## Topics")
        md_parts.append("")
        md_parts.append(", ".join(f"`{tag}`" for tag in tags))
        md_parts.append("")

    # Placeholder sections (to be filled by real workflow)
    md_parts.extend(
        [
            "---",
            "",
            "## 🤖 AI Assistant Prompt",
            "",
            "*Pending: Run through LangGraph workflow for AI-ready implementation guide*",
            "",
            "## Core Concepts",
            "",
            "*Pending: Run through LangGraph workflow for structured concepts*",
            "",
            "## Practice Exercises",
            "",
            "*Pending: Run through LangGraph workflow for exercises and quizzes*",
            "",
            "---",
            "",
            f"*Placeholder from SkillForge Golden Dataset - {content_type.title()}*",
            "*Regenerate via workflow for full triple-purpose artifact*",
        ]
    )

    return "\n".join(md_parts)


async def main(replace: bool = False) -> int:
    """Load golden dataset as individual analyses."""
    import os

    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.models.analysis import Analysis
    from app.db.models.analysis_chunk import AnalysisChunk
    from app.db.models.artifact import Artifact
    from app.db.session import AsyncSessionLocal
    from app.shared.services.embeddings import DeterministicEmbeddingService, EmbeddingService

    logger = get_logger(__name__)

    # Use deterministic embeddings in CI/test mode (no API keys required)
    use_deterministic = os.getenv("SKILLFORGE_DETERMINISTIC_EMBEDDINGS", "").lower() == "true"
    if use_deterministic:
        logger.info("Using deterministic embeddings (no API keys required)")
        embedding_service = DeterministicEmbeddingService()
    else:
        embedding_service = EmbeddingService()

    # Load fixture data
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    documents_path = fixtures_dir / "documents_expanded.json"

    if not documents_path.exists():
        logger.error(f"Fixture file not found: {documents_path}")
        return 1

    logger.info(f"Loading fixtures from: {documents_path}")
    with documents_path.open() as f:
        fixture_data = json.load(f)

    documents = fixture_data["documents"]
    total_sections = sum(len(doc.get("sections", [])) for doc in documents)

    logger.info(f"Found {len(documents)} documents with {total_sections} sections")

    async with AsyncSessionLocal() as session:
        if replace:
            logger.info("Clearing ALL existing data...")
            await session.execute(text("DELETE FROM analysis_chunks"))
            await session.execute(text("DELETE FROM artifacts"))
            await session.execute(text("DELETE FROM analyses"))
            await session.commit()
            logger.info("Cleared all existing data")

        # Process each document as a separate analysis
        total_chunks = 0
        for doc_idx, doc in enumerate(documents):
            doc_id = doc["id"]
            doc_title = doc["title"]
            content_type = doc.get("content_type", "article")
            source_url = doc.get("source_url")
            tags = doc.get("tags", [])
            sections = doc.get("sections", [])

            logger.info(f"[{doc_idx + 1}/{len(documents)}] Creating: {doc_title}")

            # Create analysis record
            analysis_id = uuid4()
            artifact_id = uuid4()

            if not source_url:
                logger.error(
                    "golden_dataset_missing_source_url",
                    document_id=doc_id,
                    title=doc_title,
                )
                return 1

            analysis = Analysis(
                id=analysis_id,
                url=source_url,
                content_type=content_type,
                status="complete",
                title=doc_title,
            )
            session.add(analysis)
            # Flush analysis first to satisfy foreign key constraint for artifact
            await session.flush()

            # Generate placeholder artifact (needs real workflow for full quality)
            markdown_content = generate_placeholder_artifact(doc)

            artifact = Artifact(
                id=artifact_id,
                analysis_id=analysis_id,
                markdown_content=markdown_content,
                version=1,
                artifact_metadata={
                    "topics": tags,
                    "complexity": "intermediate",
                    "section_count": len(sections),
                    "source": "golden-dataset-placeholder",
                    "document_id": doc_id,
                    "source_url": source_url,
                    "needs_regeneration": True,
                    "placeholder_reason": "Created from fixtures, needs real workflow",
                },
            )
            session.add(artifact)

            # Create chunks for each section
            for section_idx, section in enumerate(sections):
                content = section["content"]
                section_id = section["id"]
                section_title = section.get("title", f"Section {section_idx + 1}")

                # Generate embedding
                try:
                    embedding = await embedding_service.generate_embedding(
                        text=content,
                        normalize=True,
                    )
                except Exception:
                    logger.exception(f"Failed to embed {section_id}")
                    continue

                content_hash = hashlib.sha256(content.encode()).hexdigest()

                chunk = AnalysisChunk(
                    id=uuid4(),
                    analysis_id=analysis_id,
                    snippet=content,
                    vector=embedding,
                    granularity=section.get("granularity", "coarse"),
                    section_title=section_title,
                    chunk_idx=section_idx,
                    chunk_total=len(sections),
                    path=[doc_id, section_id],
                    hash=content_hash,
                    content_type=content_type,
                    language=doc.get("language", "en"),
                    model="text-embedding-3-small",
                    model_version="v1",
                )
                session.add(chunk)
                total_chunks += 1

            # Flush after each document
            await session.flush()

            if (doc_idx + 1) % 10 == 0:
                logger.info(
                    f"  Progress: {doc_idx + 1}/{len(documents)} documents, {total_chunks} chunks"
                )

        # Final commit
        await session.commit()

        # Verify results
        result = await session.execute(
            text("SELECT COUNT(*) FROM analyses WHERE status = 'complete'")
        )
        analyses_count = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM artifacts"))
        artifacts_count = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM analysis_chunks"))
        chunks_count = result.scalar()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Golden Dataset Loaded Successfully!")
        logger.info("=" * 60)
        logger.info(f"   Analyses:  {analyses_count}")
        logger.info(f"   Artifacts: {artifacts_count}")
        logger.info(f"   Chunks:    {chunks_count}")
        logger.info("=" * 60)

        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load golden dataset")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Clear existing data before loading",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(main(replace=args.replace))
    sys.exit(exit_code)

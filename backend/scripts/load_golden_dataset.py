#!/usr/bin/env python3
"""Load golden dataset with individual analyses, artifacts, and chunks.

This script creates a proper library of completed analyses from the golden dataset,
where each document becomes its own analysis with:
- Analysis record (completed status)
- Artifact (generated markdown implementation guide)
- Chunks (sections with embeddings)

Usage:
    poetry run python scripts/load_golden_dataset.py [--replace]

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


def generate_artifact_markdown(doc: dict) -> str:
    """Generate a realistic implementation guide markdown from document data."""
    title = doc["title"]
    content_type = doc.get("content_type", "article")
    tags = doc.get("tags", [])
    sections = doc.get("sections", [])

    # Build markdown content
    md_parts = [
        f"# {title}",
        "",
        "## Overview",
        "",
    ]

    # Add intro from first section if available
    if sections:
        intro = sections[0].get("content", "")
        md_parts.append(intro)
        md_parts.append("")

    # Add table of contents
    md_parts.append("## Table of Contents")
    md_parts.append("")
    for i, section in enumerate(sections, 1):
        section_title = section.get("title", f"Section {i}")
        anchor = section_title.lower().replace(" ", "-").replace("'", "")
        md_parts.append(f"{i}. [{section_title}](#{anchor})")
    md_parts.append("")

    # Add each section as a chapter
    for section in sections:
        section_title = section.get("title", "Section")
        content = section.get("content", "")

        md_parts.append(f"## {section_title}")
        md_parts.append("")
        md_parts.append(content)
        md_parts.append("")

    # Add implementation notes based on content type
    md_parts.append("## Implementation Notes")
    md_parts.append("")

    if content_type == "tutorial":
        md_parts.append("### Getting Started")
        md_parts.append("")
        md_parts.append("1. Review the concepts above before implementation")
        md_parts.append("2. Start with a minimal working example")
        md_parts.append("3. Iterate and add complexity gradually")
        md_parts.append("4. Test each component independently")
    elif content_type == "research_paper":
        md_parts.append("### Key Takeaways")
        md_parts.append("")
        md_parts.append("- Understand the theoretical foundations first")
        md_parts.append("- Consider tradeoffs between approaches")
        md_parts.append("- Benchmark against your specific use case")
        md_parts.append("- Monitor performance in production")
    else:
        md_parts.append("### Best Practices")
        md_parts.append("")
        md_parts.append("- Apply concepts incrementally to existing code")
        md_parts.append("- Document decisions and rationale")
        md_parts.append("- Review and refactor as understanding deepens")

    md_parts.append("")

    # Add tags as topics
    if tags:
        md_parts.append("## Related Topics")
        md_parts.append("")
        md_parts.append(", ".join(f"`{tag}`" for tag in tags))
        md_parts.append("")

    # Footer
    md_parts.append("---")
    md_parts.append("")
    md_parts.append(f"*Generated from SkillForge Golden Dataset - {content_type.title()}*")

    return "\n".join(md_parts)


async def main(replace: bool = False) -> int:
    """Load golden dataset as individual analyses."""
    from sqlalchemy import text

    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.models.analysis import Analysis
    from app.models.analysis_chunk import AnalysisChunk
    from app.models.artifact import Artifact
    from app.services.embeddings import EmbeddingService

    logger = get_logger(__name__)

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

    # Initialize embedding service
    embedding_service = EmbeddingService()

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
            tags = doc.get("tags", [])
            sections = doc.get("sections", [])

            logger.info(f"[{doc_idx + 1}/{len(documents)}] Creating: {doc_title}")

            # Create analysis record
            analysis_id = uuid4()
            artifact_id = uuid4()

            # Create a realistic URL based on content type
            url_base = {
                "article": "https://docs.skillforge.dev",
                "tutorial": "https://learn.skillforge.dev",
                "research_paper": "https://papers.skillforge.dev",
                "documentation": "https://docs.skillforge.dev",
            }.get(content_type, "https://content.skillforge.dev")

            analysis = Analysis(
                id=analysis_id,
                url=f"{url_base}/{doc_id}",
                content_type=content_type,
                status="completed",
                title=doc_title,
            )
            session.add(analysis)

            # Generate and create artifact
            markdown_content = generate_artifact_markdown(doc)

            artifact = Artifact(
                id=artifact_id,
                analysis_id=analysis_id,
                markdown_content=markdown_content,
                version=1,
                artifact_metadata={
                    "topics": tags,
                    "complexity": "intermediate",
                    "section_count": len(sections),
                    "source": "golden-dataset",
                    "document_id": doc_id,
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
            text("SELECT COUNT(*) FROM analyses WHERE status = 'completed'")
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

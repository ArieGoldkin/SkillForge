#!/usr/bin/env python3
"""Reconcile golden dataset fixture docs with the dev database.

If the fixture `documents_expanded.json` contains documents that do not exist in
the database as golden-dataset artifacts (identified by artifact_metadata.document_id),
this script inserts the missing analyses + placeholder artifacts + chunks.

This is safe to run multiple times (it only inserts missing document_ids).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()


def _load_fixture_documents() -> list[dict]:
    fixtures_dir = Path(__file__).parent.parent / "tests/smoke/retrieval/fixtures"
    documents_path = fixtures_dir / "documents_expanded.json"
    data = json.loads(documents_path.read_text(encoding="utf-8"))
    return data["documents"]


def _generate_placeholder_artifact(doc: dict) -> str:
    title = doc["title"]
    content_type = doc.get("content_type", "article")
    tags = doc.get("tags", [])
    sections = doc.get("sections", [])

    md_parts: list[str] = [
        f"# {title}",
        "",
        "> **⚠️ PLACEHOLDER ARTIFACT**",
        "> This artifact was created from fixture data and needs regeneration",
        "> through the real LangGraph workflow for full quality.",
        "",
        "## Overview",
        "",
    ]

    if sections:
        intro = sections[0].get("content", "")
        md_parts.append(intro)
        md_parts.append("")

    for section in sections:
        section_title = section.get("title", "Section")
        content = section.get("content", "")
        md_parts.append(f"## {section_title}")
        md_parts.append("")
        md_parts.append(content)
        md_parts.append("")

    if tags:
        md_parts.append("## Topics")
        md_parts.append("")
        md_parts.append(", ".join(f"`{tag}`" for tag in tags))
        md_parts.append("")

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


async def main() -> int:
    """Insert any missing fixture documents into the database."""
    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.db.models.analysis import Analysis
    from app.db.models.analysis_chunk import AnalysisChunk
    from app.db.models.artifact import Artifact
    from app.services.embeddings import EmbeddingService

    logger = get_logger(__name__)
    docs = _load_fixture_documents()

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text(
                """
                SELECT DISTINCT artifact_metadata->>'document_id' AS doc_id
                FROM artifacts
                WHERE artifact_metadata ? 'document_id'
                """
            )
        )
        existing = {r[0] for r in res.fetchall() if r[0]}

        embedding_service = EmbeddingService()

        inserted = 0
        for doc in docs:
            doc_id = doc["id"]
            if doc_id in existing:
                continue

            source_url = doc.get("source_url")
            if not source_url:
                logger.error("golden_fixture_missing_source_url", document_id=doc_id)
                return 1

            content_type = doc.get("content_type", "article")
            title = doc["title"]
            tags = doc.get("tags", [])
            sections = doc.get("sections", [])

            analysis_id = uuid4()
            artifact_id = uuid4()

            analysis = Analysis(
                id=analysis_id,
                url=source_url,
                content_type=content_type,
                status="completed",
                title=title,
            )
            session.add(analysis)

            artifact = Artifact(
                id=artifact_id,
                analysis_id=analysis_id,
                markdown_content=_generate_placeholder_artifact(doc),
                version=1,
                artifact_metadata={
                    "topics": tags,
                    "complexity": "intermediate",
                    "section_count": len(sections),
                    "source": "golden-dataset-placeholder",
                    "document_id": doc_id,
                    "source_url": source_url,
                    "needs_regeneration": True,
                    "placeholder_reason": "Inserted by reconcile script (fixture → DB)",
                },
            )
            session.add(artifact)

            for section_idx, section in enumerate(sections):
                content = section["content"]
                section_id = section["id"]
                section_title = section.get("title", f"Section {section_idx + 1}")

                try:
                    embedding = await embedding_service.generate_embedding(
                        text=content,
                        normalize=True,
                    )
                except Exception:
                    logger.exception("golden_dataset_embedding_failed", section_id=section_id)
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

            inserted += 1

        await session.commit()

    logger.info("golden_dataset_reconcile_complete", inserted=inserted, fixture_count=len(docs))
    print(f"Inserted {inserted} missing golden dataset documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

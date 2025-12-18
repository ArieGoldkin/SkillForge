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
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

    from app.core.config import get_settings
    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.db.models.analysis import Analysis
    from app.db.models.analysis_chunk import AnalysisChunk
    from app.db.models.artifact import Artifact
    from app.services.embeddings import EmbeddingService
    from app.services.embeddings.deterministic import DeterministicEmbeddingService

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

    # Initialize embedding service (default to deterministic when API key is absent)
    settings = get_settings()
    force_deterministic = (os.environ.get("SKILLFORGE_DETERMINISTIC_EMBEDDINGS") or "").lower() in {
        "1",
        "true",
        "yes",
    }

    if force_deterministic or not settings.OPENAI_API_KEY:
        logger.info("using_deterministic_embeddings_for_fixtures")
        embedding_service = DeterministicEmbeddingService()
    else:
        embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        # Create or get analysis record for fixtures
        analysis_id = uuid4()
        analysis_name = "expanded-fixtures" if expanded else "original-fixtures"

        # Check if we should replace existing data
        if replace:
            logger.info("Clearing existing fixture data...")
            # Delete chunks first (FK constraint)
            await session.execute(
                text("""
                    DELETE FROM analysis_chunks
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE url LIKE '%fixture%' OR url LIKE '%smoke-test%'
                    )
                """)
            )
            # Delete artifacts (FK constraint)
            await session.execute(
                text("""
                    DELETE FROM artifacts
                    WHERE analysis_id IN (
                        SELECT id FROM analyses
                        WHERE url LIKE '%fixture%' OR url LIKE '%smoke-test%'
                    )
                """)
            )
            # Finally delete analyses
            await session.execute(
                text("""
                    DELETE FROM analyses
                    WHERE url LIKE '%fixture%' OR url LIKE '%smoke-test%'
                """)
            )
            await session.commit()
            logger.info("Cleared existing fixture data")

        # Create analysis record
        artifact_id = uuid4()
        analysis = Analysis(
            id=analysis_id,
            url=f"https://fixtures.skillforge.local/{analysis_name}",
            content_type="fixture_dataset",
            status="completed",
            title="Context Engineering for AI Agents",  # Title for E2E tests
        )
        session.add(analysis)
        await session.flush()

        logger.info(f"Created analysis record: {analysis_id}")

        # Create artifact with sample markdown content for E2E tests
        sample_markdown = """# Context Engineering for AI Agents

## Overview

This implementation guide covers the key concepts and best practices for context engineering in multi-agent AI systems.

## Table of Contents

1. [Introduction](#introduction)
2. [Core Principles](#core-principles)
3. [Implementation Guide](#implementation-guide)
4. [Code Examples](#code-examples)
5. [Best Practices](#best-practices)

## Introduction

Context engineering is the practice of designing, managing, and optimizing the information that AI agents receive to perform tasks effectively. Unlike traditional prompt engineering which focuses on single interactions, context engineering addresses the broader challenge of maintaining relevant information across multi-turn conversations and complex workflows.

## Core Principles

### 1. Relevance-First Design

Only include information pertinent to the current task. Irrelevant information should be actively pruned to maintain focus and reduce token costs.

### 2. Progressive Disclosure

Start with summaries and load details only when needed. This hierarchical approach optimizes both performance and comprehension.

### 3. Context Stability

Frequent context changes can confuse AI agents. Implement careful change management to maintain consistency.

## Implementation Guide

### Setting Up Context Windows

```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ContextWindow:
    \"\"\"Manages context for AI agent interactions.\"\"\"

    system_instructions: str
    session_context: List[Dict[str, Any]]
    task_context: Dict[str, Any]
    working_memory: List[str]

    def get_total_tokens(self) -> int:
        \"\"\"Calculate total token usage.\"\"\"
        # Implementation here
        pass

    def prune_by_relevance(self, threshold: float = 0.5) -> None:
        \"\"\"Remove low-relevance items from context.\"\"\"
        # Implementation here
        pass
```

### Memory Architecture

```typescript
interface MemorySystem {
  workingMemory: ContextItem[];    // 4K-32K tokens
  shortTermMemory: SessionData[];   // 100K-1M tokens
  longTermMemory: KnowledgeBase;    // Unlimited
}

class AgentMemory implements MemorySystem {
  async retrieve(query: string): Promise<ContextItem[]> {
    // Semantic search across memory layers
    const results = await this.vectorSearch(query);
    return this.rankByRelevance(results);
  }
}
```

## Best Practices

1. **Token Budgeting**: Allocate 20-30% for system instructions, 15-25% for history, 30-40% for retrieved context
2. **Cache Frequently Used Context**: Reduce latency with multi-level caching (L1: in-memory, L2: Redis)
3. **Monitor Context Utilization**: Track what percentage of provided context is actually used
4. **Implement Graceful Degradation**: Handle context overflow by pruning least relevant items

## Metrics to Track

| Metric | Target | Description |
|--------|--------|-------------|
| Context Utilization | 60-80% | % of context actually referenced |
| Context Accuracy | 95%+ | Correctness of provided information |
| Retrieval Latency | <200ms | Time to fetch relevant context |
| Token Efficiency | High | Useful information per token |

## Conclusion

Effective context engineering can improve AI agent performance by 40-60% while reducing token costs by 30-50%. The key is to treat context as a first-class concern in your system design.

---

*Generated from SkillForge Golden Dataset - Context Engineering Module*
"""

        artifact = Artifact(
            id=artifact_id,
            analysis_id=analysis_id,
            markdown_content=sample_markdown,
            version=1,
            artifact_metadata={
                "topics": ["context-engineering", "ai-agents", "llm", "memory-systems"],
                "complexity": "intermediate",
                "estimated_read_time": "8 min",
                "code_languages": ["python", "typescript"],
                "source": "golden-dataset-fixture",
            },
        )
        session.add(artifact)
        await session.flush()

        logger.info(f"Created artifact record: {artifact_id}")

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

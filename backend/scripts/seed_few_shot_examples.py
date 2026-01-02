#!/usr/bin/env python3
"""Seed agent_examples table from golden dataset for Few-Shot Prompting.

This script extracts high-quality examples from the 98 golden dataset analyses
and creates agent_examples records with embeddings for semantic retrieval.

Phase 1, Week 1.3: Few-Shot Prompting Infrastructure

Strategy:
- Extract 5-10 examples per agent type from golden dataset
- Generate embeddings for input summaries (first 500 chars)
- Assign quality scores based on artifact metadata (complexity, section_count)
- Bulk insert into agent_examples table

Usage:
    poetry run python scripts/seed_few_shot_examples.py [--dry-run] [--limit N]

Requirements:
    - Golden dataset backup must exist: data/golden_dataset_backup.json
    - Database must have agent_examples table (run migration first)
    - OPENAI_API_KEY environment variable must be set

Output:
    - Inserts agent_examples records with embeddings
    - Prints statistics per agent type
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from app.core.logging import get_logger  # noqa: E402
from app.db.models.agent_example import AgentExample  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.shared.services.embeddings.service import EmbeddingService  # noqa: E402

logger = get_logger(__name__)

# Agent type mapping based on artifact metadata
AGENT_TYPE_PATTERNS = {
    "implementation_planner": ["implementation", "tutorial", "guide", "step-by-step"],
    "tech_comparator": ["comparison", "vs", "versus", "alternatives", "choosing"],
    "dependency_mapper": ["dependency", "requirements", "install", "setup"],
    "performance_analyst": ["performance", "benchmark", "optimization", "latency"],
    "security_auditor": ["security", "vulnerability", "owasp", "authentication"],
    "code_reviewer": ["review", "quality", "best-practices", "patterns"],
    "learning_path": ["learning", "tutorial", "beginner", "advanced"],
    "research_analyst": ["research", "paper", "survey", "theory"],
}


def determine_agent_type(artifact: dict[str, Any]) -> str:
    """Determine primary agent type based on artifact metadata.

    Strategy:
    1. Check topics for agent-specific keywords
    2. Check title for patterns
    3. Check content_type
    4. Default to research_analyst for research papers

    Args:
        artifact: Artifact dict from golden dataset

    Returns:
        Agent type string (e.g., 'implementation_planner')

    """
    metadata = artifact.get("artifact_metadata", {})
    topics = metadata.get("topics", [])
    title = metadata.get("source_url", "").lower()
    content_type = metadata.get("source", "article")

    # Check topics against patterns
    for agent_type, patterns in AGENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            if any(pattern in topic.lower() for topic in topics):
                return agent_type
            if pattern in title:
                return agent_type

    # Default based on content type
    if content_type == "research_paper":
        return "research_analyst"
    if "tutorial" in content_type.lower():
        return "implementation_planner"

    # Default fallback
    return "research_analyst"


def calculate_quality_score(artifact: dict[str, Any]) -> float:
    """Calculate quality score based on artifact metadata.

    Scoring criteria:
    - Base score: 0.7
    - Complexity bonus: +0.1 (advanced), +0.05 (intermediate)
    - Section count bonus: +0.05 per section (max +0.2)
    - Golden dataset bonus: +0.1 (all golden dataset items are high quality)

    Args:
        artifact: Artifact dict from golden dataset

    Returns:
        Quality score between 0.0 and 1.0

    """
    metadata = artifact.get("artifact_metadata", {})

    score = 0.7  # Base score

    # Complexity bonus
    complexity = metadata.get("complexity", "intermediate")
    if complexity == "advanced":
        score += 0.1
    elif complexity == "intermediate":
        score += 0.05

    # Section count bonus (capped at 0.2)
    section_count = metadata.get("section_count", 0)
    section_bonus = min(section_count * 0.05, 0.2)
    score += section_bonus

    # Golden dataset bonus
    if metadata.get("source") == "golden-dataset":
        score += 0.1

    return float(min(score, 1.0))  # Cap at 1.0


def extract_input_summary(markdown_content: str, max_chars: int = 500) -> str:
    """Extract first meaningful content as input summary.

    Strategy:
    - Skip title lines (starting with #)
    - Take first 500 chars of actual content
    - Clean up whitespace

    Args:
        markdown_content: Full markdown artifact content
        max_chars: Maximum characters to extract (default: 500)

    Returns:
        Input summary string

    """
    lines = markdown_content.split("\n")

    # Skip title and TOC
    content_lines = []
    skip_toc = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip title
        if stripped.startswith("# "):
            continue

        # Skip TOC
        if "Table of Contents" in stripped:
            skip_toc = True
            continue
        if skip_toc and (stripped.startswith("##") or stripped.startswith("1.")):
            skip_toc = False

        if not skip_toc and stripped:
            content_lines.append(stripped)

    # Join and truncate
    summary = " ".join(content_lines)[:max_chars]
    return summary.strip()


def create_output_example(artifact: dict[str, Any], agent_type: str) -> dict[str, Any]:
    """Create structured output example for agent.

    Args:
        artifact: Artifact dict from golden dataset
        agent_type: Agent type string

    Returns:
        Output example dict (will be stored as JSONB)

    """
    metadata = artifact.get("artifact_metadata", {})

    # Generic output structure (can be customized per agent type)
    output_example = {
        "content_type": metadata.get("source", "article"),
        "complexity": metadata.get("complexity", "intermediate"),
        "key_topics": metadata.get("topics", []),
        "section_count": metadata.get("section_count", 0),
        "source_url": metadata.get("source_url", ""),
        "analysis_summary": f"Analyzed content related to {', '.join(metadata.get('topics', [])[:3])}",
    }

    # Agent-specific additions
    if agent_type == "implementation_planner":
        output_example["implementation_steps"] = [
            "Identify requirements",
            "Design architecture",
            "Implement core features",
            "Add tests",
            "Deploy",
        ]

    elif agent_type == "tech_comparator":
        output_example["comparison_framework"] = {
            "criteria": ["performance", "ease_of_use", "ecosystem", "cost"],
            "recommendation": "Choose based on project requirements",
        }

    elif agent_type == "security_auditor":
        output_example["security_considerations"] = [
            "Authentication and authorization",
            "Input validation",
            "Data encryption",
        ]

    return output_example


async def seed_examples(dry_run: bool = False, limit: int | None = None) -> None:
    """Seed agent examples from golden dataset.

    Args:
        dry_run: If True, print what would be inserted without inserting
        limit: If set, limit number of examples to process (for testing)

    """
    # Load golden dataset backup
    backup_path = Path(__file__).parent.parent / "data" / "golden_dataset_backup.json"

    if not backup_path.exists():
        logger.error("golden_dataset_backup_not_found", path=str(backup_path))
        print(f"ERROR: Golden dataset backup not found at {backup_path}")
        print("Run: poetry run python scripts/backup_golden_dataset.py backup")
        sys.exit(1)

    logger.info("loading_golden_dataset", path=str(backup_path))
    with backup_path.open() as f:
        backup_data = json.load(f)

    artifacts = backup_data["data"]["artifacts"]
    analyses = {a["id"]: a for a in backup_data["data"]["analyses"]}

    logger.info(
        "golden_dataset_loaded",
        artifact_count=len(artifacts),
        analysis_count=len(analyses),
    )

    # Apply limit if specified
    if limit:
        artifacts = artifacts[:limit]
        logger.info("applying_limit", limit=limit)

    # Initialize services
    embedding_service = EmbeddingService()

    # Create examples
    examples = []
    agent_type_counts: dict[str, int] = {}

    for artifact in artifacts:
        try:
            # Determine agent type
            agent_type = determine_agent_type(artifact)
            agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1

            # Extract input summary
            markdown_content = artifact.get("markdown_content", "")
            input_summary = extract_input_summary(markdown_content)

            if not input_summary:
                logger.warning("empty_input_summary", artifact_id=artifact["id"], skipping=True)
                continue

            # Calculate quality score
            quality_score = calculate_quality_score(artifact)

            # Create output example
            output_example = create_output_example(artifact, agent_type)

            # Get metadata
            metadata = artifact.get("artifact_metadata", {})
            source_analysis_id = artifact.get("analysis_id")

            # Generate embedding
            logger.info(
                "generating_embedding",
                artifact_id=artifact["id"],
                agent_type=agent_type,
                input_length=len(input_summary),
            )

            embedding = await embedding_service.generate_embedding(input_summary, normalize=True)

            # Create AgentExample model - DB generates UUIDs via server_default
            example = AgentExample(
                agent_type=agent_type,
                input_summary=input_summary,
                input_content_preview=markdown_content[:2000],
                output_example=output_example,
                context_note=f"Extracted from golden dataset artifact {artifact['id']}",
                quality_score=quality_score,
                is_golden=True,
                source_analysis_id=UUID(source_analysis_id) if source_analysis_id else None,
                embedding=embedding,
                content_type=metadata.get("source", "article"),
                difficulty_level=metadata.get("complexity", "intermediate"),
            )

            examples.append(example)

            logger.info(
                "example_created",
                example_id=str(example.id),
                agent_type=agent_type,
                quality_score=quality_score,
            )

        except Exception as e:
            logger.exception(
                "example_creation_failed",
                artifact_id=artifact.get("id"),
                error=str(e),
            )
            continue

    # Print statistics
    print("\n" + "=" * 70)
    print("FEW-SHOT EXAMPLE SEEDING SUMMARY")
    print("=" * 70)
    print(f"\nTotal examples created: {len(examples)}")
    print("\nExamples per agent type:")
    for agent_type, count in sorted(agent_type_counts.items()):
        print(f"  {agent_type:30s} {count:3d} examples")

    avg_quality = sum(e.quality_score for e in examples) / len(examples) if examples else 0
    print(f"\nAverage quality score: {avg_quality:.3f}")
    print("=" * 70 + "\n")

    if dry_run:
        print("DRY RUN: No examples inserted into database")
        print(f"Would insert {len(examples)} examples")
        return

    # Insert into database
    logger.info("inserting_examples_into_database", count=len(examples))

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Check if examples already exist
        result = await session.execute(select(AgentExample).limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            print("\nWARNING: Database already contains agent examples!")
            response = input("Do you want to continue and add more examples? [y/N]: ")
            if response.lower() != "y":
                print("Aborted.")
                return

        # Bulk insert
        session.add_all(examples)
        await session.commit()

        logger.info("examples_inserted_successfully", count=len(examples))

    print(f"\n✅ Successfully inserted {len(examples)} examples into database")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Seed agent examples from golden dataset")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without inserting",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of examples to process (for testing)",
    )

    args = parser.parse_args()

    await seed_examples(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())

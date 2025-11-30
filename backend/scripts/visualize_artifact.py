#!/usr/bin/env python3
"""Visualize an artifact with its structure, metadata, and content.

This script fetches an artifact from the database and displays it in a
readable format, showing structure, metadata, and markdown content.

Usage:
    python scripts/visualize_artifact.py --analysis-id <analysis_id>
    python scripts/visualize_artifact.py --artifact-id <artifact_id>
    python scripts/visualize_artifact.py --latest  # Show most recent artifact
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import desc, select

from app.db.repositories.artifact_repository import ArtifactRepository
from app.db.session import AsyncSessionLocal
from app.models.artifact import Artifact


def format_size(size_bytes: int) -> str:
    """Format byte size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def print_section(title: str, content: str = "") -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    if content:
        print(content)
        print()


def print_artifact_info(artifact: Artifact) -> None:
    """Print artifact metadata and information."""
    print_section("Artifact Information")

    print(f"  ID:              {artifact.id}")
    print(f"  Analysis ID:     {artifact.analysis_id}")
    print(f"  Version:         {artifact.version}")
    print(f"  Created At:      {artifact.created_at}")
    print(f"  Download Count:  {artifact.download_count}")
    print(f"  Content Size:    {format_size(len(artifact.markdown_content.encode('utf-8')))}")
    print(f"  Line Count:      {len(artifact.markdown_content.splitlines())}")

    if artifact.artifact_metadata:
        print("\n  Metadata:")
        print(json.dumps(artifact.artifact_metadata, indent=4, default=str))


def analyze_markdown_structure(content: str) -> dict:
    """Analyze markdown structure and extract sections."""
    lines = content.splitlines()
    structure = {
        "headings": [],
        "code_blocks": 0,
        "links": 0,
        "lists": 0,
        "tables": 0,
    }

    in_code_block = False
    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Headings
        if line_stripped.startswith("#"):
            level = len(line_stripped) - len(line_stripped.lstrip("#"))
            text = line_stripped.lstrip("# ").strip()
            structure["headings"].append({"level": level, "text": text, "line": i})

        # Code blocks
        if line_stripped.startswith("```"):
            in_code_block = not in_code_block
            if not in_code_block:  # Count closing blocks
                structure["code_blocks"] += 1

        # Links (basic detection)
        if "](" in line and not in_code_block:
            structure["links"] += line.count("](")

        # Lists
        if line_stripped.startswith("- ") or line_stripped.startswith("* "):
            structure["lists"] += 1

        # Tables
        if "|" in line_stripped and not in_code_block:
            if "---" in lines[max(0, i - 2) : i + 1][-1] if i > 1 else False:
                structure["tables"] += 1

    return structure


def print_markdown_structure(structure: dict) -> None:
    """Print markdown structure analysis."""
    print_section("Markdown Structure")

    print(f"  Headings:        {len(structure['headings'])}")
    print(f"  Code Blocks:     {structure['code_blocks']}")
    print(f"  Links:           {structure['links']}")
    print(f"  List Items:      {structure['lists']}")
    print(f"  Tables:          {structure['tables']}")

    if structure["headings"]:
        print("\n  Document Outline:")
        for heading in structure["headings"][:20]:  # Limit to first 20
            indent = "  " * (heading["level"] - 1)
            print(f"  {indent}{'#' * heading['level']} {heading['text']}")
        if len(structure["headings"]) > 20:
            print(f"  ... and {len(structure['headings']) - 20} more headings")


def print_markdown_preview(content: str, max_lines: int = 50) -> None:
    """Print a preview of the markdown content."""
    print_section("Markdown Preview (First 50 lines)")

    lines = content.splitlines()
    preview_lines = lines[:max_lines]

    for i, line in enumerate(preview_lines, 1):
        print(f"{i:4d} | {line}")

    if len(lines) > max_lines:
        print(f"\n... ({len(lines) - max_lines} more lines)")


async def fetch_artifact_by_id(artifact_id: uuid.UUID) -> Artifact | None:
    """Fetch artifact by ID."""
    async with AsyncSessionLocal() as db_session:
        repository = ArtifactRepository(session=db_session)
        return await repository.get_artifact_by_id(artifact_id)


async def fetch_artifact_by_analysis_id(analysis_id: uuid.UUID) -> Artifact | None:
    """Fetch artifact by analysis ID."""
    async with AsyncSessionLocal() as db_session:
        repository = ArtifactRepository(session=db_session)
        return await repository.get_artifact_by_analysis_id(analysis_id)


async def fetch_latest_artifact() -> Artifact | None:
    """Fetch the most recently created artifact."""
    async with AsyncSessionLocal() as db_session:
        result = await db_session.execute(
            select(Artifact).order_by(desc(Artifact.created_at)).limit(1)
        )
        return result.scalar_one_or_none()


async def visualize_artifact(artifact: Artifact, show_full_content: bool = False) -> None:
    """Visualize an artifact with all its details."""
    print("\n" + "=" * 80)
    print("  ARTIFACT VISUALIZATION")
    print("=" * 80)

    # Artifact information
    print_artifact_info(artifact)

    # Markdown structure analysis
    structure = analyze_markdown_structure(artifact.markdown_content)
    print_markdown_structure(structure)

    # Markdown preview
    if show_full_content:
        print_section("Full Markdown Content")
        print(artifact.markdown_content)
    else:
        print_markdown_preview(artifact.markdown_content)

    # Save to file option
    print_section("Export Options")
    filename = f"artifact_{artifact.id}.md"
    print(f"  To save full content to file:")
    print(f"    echo '{artifact.markdown_content}' > {filename}")
    print(f"\n  Or view in browser (markdown viewer)")
    print(f"    python scripts/visualize_artifact.py --artifact-id {artifact.id} --save {filename}")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Visualize an artifact")
    parser.add_argument("--artifact-id", type=str, help="Artifact ID (UUID)")
    parser.add_argument("--analysis-id", type=str, help="Analysis ID (UUID)")
    parser.add_argument("--latest", action="store_true", help="Show latest artifact")
    parser.add_argument("--full", action="store_true", help="Show full markdown content")
    parser.add_argument("--save", type=str, help="Save artifact to file")

    args = parser.parse_args()

    artifact: Artifact | None = None

    # Fetch artifact based on arguments
    if args.latest:
        print("Fetching latest artifact...")
        artifact = await fetch_latest_artifact()
        if not artifact:
            print("❌ No artifacts found in database")
            sys.exit(1)
    elif args.artifact_id:
        try:
            artifact_id = uuid.UUID(args.artifact_id)
            print(f"Fetching artifact {artifact_id}...")
            artifact = await fetch_artifact_by_id(artifact_id)
        except ValueError:
            print(f"❌ Invalid artifact ID: {args.artifact_id}")
            sys.exit(1)
    elif args.analysis_id:
        try:
            analysis_id = uuid.UUID(args.analysis_id)
            print(f"Fetching artifact for analysis {analysis_id}...")
            artifact = await fetch_artifact_by_analysis_id(analysis_id)
        except ValueError:
            print(f"❌ Invalid analysis ID: {args.analysis_id}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    if not artifact:
        print("❌ Artifact not found")
        sys.exit(1)

    # Save to file if requested
    if args.save:
        output_path = Path(args.save)
        output_path.write_text(artifact.markdown_content, encoding="utf-8")
        print(f"✅ Artifact saved to {output_path}")
        print(f"   Size: {format_size(len(artifact.markdown_content.encode('utf-8')))}")
        return

    # Visualize artifact
    await visualize_artifact(artifact, show_full_content=args.full)


if __name__ == "__main__":
    asyncio.run(main())


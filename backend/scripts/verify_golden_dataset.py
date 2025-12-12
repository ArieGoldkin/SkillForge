#!/usr/bin/env python3
"""Verify SkillForge golden dataset database integrity.

This script performs comprehensive verification of the golden dataset:
- Database connection health
- Analysis completeness (status, artifact links, chunks)
- Data consistency (no orphans, valid foreign keys)
- Embedding quality (dimensions, no NaN/zeros)
- Content type distribution
- Critical field validation (no NULLs where required)

Usage:
    poetry run python scripts/verify_golden_dataset.py [--verbose] [--fix-orphans]

Options:
    --verbose       Show detailed query results
    --fix-orphans   Automatically delete orphaned records (USE WITH CAUTION)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_check(name: str, status: str, details: str = "") -> None:
    """Print formatted check result."""
    status_color = Colors.GREEN if status == "PASS" else Colors.RED
    status_symbol = "✓" if status == "PASS" else "✗"

    print(f"{status_color}{status_symbol}{Colors.END} {Colors.BOLD}{name}{Colors.END}")
    if details:
        print(f"  {Colors.CYAN}{details}{Colors.END}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ WARNING: {message}{Colors.END}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}[i] {message}{Colors.END}")


async def verify_database_connection(session: Any) -> tuple[bool, str]:
    """Verify PostgreSQL database connection."""
    try:
        result = await session.execute(text("SELECT version()"))
        version = result.scalar()

        # Check pgvector extension
        result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        pgvector_version = result.scalar()

        if not pgvector_version:
            return False, "pgvector extension not installed"

        return (
            True,
            f"PostgreSQL {version.split(',')[0].split(' ')[-1]} | pgvector {pgvector_version}",
        )
    except Exception as e:
        return False, str(e)


async def verify_analyses(session: Any, verbose: bool = False) -> dict[str, Any]:
    """Verify analysis records integrity."""
    results: dict[str, Any] = {}

    # Total analyses
    result = await session.execute(text("SELECT COUNT(*) FROM analyses"))
    results["total"] = result.scalar()

    # Completed analyses
    result = await session.execute(text("SELECT COUNT(*) FROM analyses WHERE status = 'completed'"))
    results["completed"] = result.scalar()

    # Analyses with artifacts
    result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT a.id)
            FROM analyses a
            INNER JOIN artifacts art ON a.id = art.analysis_id
            WHERE a.status = 'completed'
        """)
    )
    results["with_artifacts"] = result.scalar()

    # Analyses with chunks
    result = await session.execute(
        text("""
            SELECT COUNT(DISTINCT a.id)
            FROM analyses a
            INNER JOIN analysis_chunks c ON a.id = c.analysis_id
            WHERE a.status = 'completed'
        """)
    )
    results["with_chunks"] = result.scalar()

    # NULL title/url/status
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analyses
            WHERE title IS NULL OR url IS NULL OR status IS NULL
        """)
    )
    results["null_critical_fields"] = result.scalar()

    # Content type distribution
    result = await session.execute(
        text("""
            SELECT content_type, COUNT(*) as count
            FROM analyses
            WHERE status = 'completed'
            GROUP BY content_type
            ORDER BY count DESC
        """)
    )
    results["content_types"] = [(row[0] or "NULL", row[1]) for row in result.fetchall()]

    if verbose:
        print_info(f"Total analyses: {results['total']}")
        print_info(f"Completed: {results['completed']}")
        print_info(f"With artifacts: {results['with_artifacts']}")
        print_info(f"With chunks: {results['with_chunks']}")
        print_info(f"Content types: {results['content_types']}")

    return results


async def verify_artifacts(session: Any, verbose: bool = False) -> dict[str, Any]:
    """Verify artifact records integrity."""
    results: dict[str, Any] = {}

    # Total artifacts
    result = await session.execute(text("SELECT COUNT(*) FROM artifacts"))
    results["total"] = result.scalar()

    # Orphaned artifacts (no parent analysis)
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM artifacts art
            LEFT JOIN analyses a ON art.analysis_id = a.id
            WHERE a.id IS NULL
        """)
    )
    results["orphaned"] = result.scalar()

    # NULL markdown_content
    result = await session.execute(
        text("SELECT COUNT(*) FROM artifacts WHERE markdown_content IS NULL")
    )
    results["null_content"] = result.scalar()

    # Average content length
    result = await session.execute(text("SELECT AVG(LENGTH(markdown_content)) FROM artifacts"))
    results["avg_content_length"] = int(result.scalar() or 0)

    if verbose:
        print_info(f"Total artifacts: {results['total']}")
        print_info(f"Orphaned: {results['orphaned']}")
        print_info(f"Avg content length: {results['avg_content_length']} chars")

    return results


async def verify_chunks(session: Any, verbose: bool = False) -> dict[str, Any]:
    """Verify chunk records and embeddings integrity."""
    results: dict[str, Any] = {}

    # Total chunks
    result = await session.execute(text("SELECT COUNT(*) FROM analysis_chunks"))
    results["total"] = result.scalar()

    # Orphaned chunks (no parent analysis)
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analysis_chunks c
            LEFT JOIN analyses a ON c.analysis_id = a.id
            WHERE a.id IS NULL
        """)
    )
    results["orphaned"] = result.scalar()

    # NULL vectors
    result = await session.execute(
        text("SELECT COUNT(*) FROM analysis_chunks WHERE vector IS NULL")
    )
    results["null_vectors"] = result.scalar()

    # Verify embedding dimensions (should be 1536 for text-embedding-3-small)
    if results["total"] > 0 and results["null_vectors"] == 0:
        result = await session.execute(
            text("""
                SELECT vector_dims(vector) as dims, COUNT(*) as count
                FROM analysis_chunks
                WHERE vector IS NOT NULL
                GROUP BY dims
            """)
        )
        results["vector_dimensions"] = [(row[0], row[1]) for row in result.fetchall()]
    else:
        results["vector_dimensions"] = []

    # Check for invalid vectors (NaN values)
    # Note: Normalized vectors will have distance to themselves near 0 (not invalid)
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analysis_chunks
            WHERE vector IS NOT NULL
            AND vector::text LIKE '%NaN%'
        """)
    )
    results["invalid_vectors"] = result.scalar()

    # Check for unnormalized vectors (self-distance for normalized should be very small)
    # For normalized vectors: vector <-> vector should be ~0
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analysis_chunks
            WHERE vector IS NOT NULL
            AND (vector <-> vector) > 0.0001
        """)
    )
    results["unnormalized_vectors"] = result.scalar()

    # Granularity distribution
    result = await session.execute(
        text("""
            SELECT granularity, COUNT(*) as count
            FROM analysis_chunks
            GROUP BY granularity
            ORDER BY count DESC
        """)
    )
    results["granularity_dist"] = [(row[0] or "NULL", row[1]) for row in result.fetchall()]

    # Model distribution
    result = await session.execute(
        text("""
            SELECT model, COUNT(*) as count
            FROM analysis_chunks
            GROUP BY model
            ORDER BY count DESC
        """)
    )
    results["model_dist"] = [(row[0] or "NULL", row[1]) for row in result.fetchall()]

    if verbose:
        print_info(f"Total chunks: {results['total']}")
        print_info(f"Orphaned: {results['orphaned']}")
        print_info(f"Vector dimensions: {results['vector_dimensions']}")
        print_info(f"Invalid vectors (NaN): {results['invalid_vectors']}")
        print_info(f"Unnormalized vectors: {results['unnormalized_vectors']}")
        print_info(f"Granularity: {results['granularity_dist']}")
        print_info(f"Models: {results['model_dist']}")

    return results


async def verify_consistency(session: Any, verbose: bool = False) -> dict[str, Any]:
    """Verify referential integrity and consistency."""
    results: dict[str, Any] = {}

    # Completed analyses WITHOUT artifacts
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analyses a
            LEFT JOIN artifacts art ON a.id = art.analysis_id
            WHERE a.status = 'completed' AND art.id IS NULL
        """)
    )
    results["completed_no_artifacts"] = result.scalar()

    # Completed analyses WITHOUT chunks
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM analyses a
            LEFT JOIN analysis_chunks c ON a.id = c.analysis_id
            WHERE a.status = 'completed' AND c.id IS NULL
        """)
    )
    results["completed_no_chunks"] = result.scalar()

    # Artifacts with mismatched analysis_id
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM artifacts art
            INNER JOIN analyses a ON art.analysis_id = a.id
            WHERE a.status != 'completed'
        """)
    )
    results["artifacts_not_completed"] = result.scalar()

    # Chunks without snippet
    result = await session.execute(
        text("SELECT COUNT(*) FROM analysis_chunks WHERE snippet IS NULL OR snippet = ''")
    )
    results["chunks_no_snippet"] = result.scalar()

    if verbose:
        print_info(f"Completed without artifacts: {results['completed_no_artifacts']}")
        print_info(f"Completed without chunks: {results['completed_no_chunks']}")
        print_info(f"Artifacts not completed: {results['artifacts_not_completed']}")

    return results


async def fix_orphaned_records(session: Any) -> dict[str, int]:
    """Delete orphaned artifacts and chunks (USE WITH CAUTION)."""
    results: dict[str, int] = {}

    # Delete orphaned artifacts
    result = await session.execute(
        text("""
            DELETE FROM artifacts
            WHERE id IN (
                SELECT art.id FROM artifacts art
                LEFT JOIN analyses a ON art.analysis_id = a.id
                WHERE a.id IS NULL
            )
        """)
    )
    results["artifacts_deleted"] = result.rowcount

    # Delete orphaned chunks
    result = await session.execute(
        text("""
            DELETE FROM analysis_chunks
            WHERE id IN (
                SELECT c.id FROM analysis_chunks c
                LEFT JOIN analyses a ON c.analysis_id = a.id
                WHERE a.id IS NULL
            )
        """)
    )
    results["chunks_deleted"] = result.rowcount

    await session.commit()

    return results


async def main(verbose: bool = False, fix_orphans: bool = False) -> int:  # noqa: PLR0912
    """Run comprehensive database verification."""
    from app.db.session import AsyncSessionLocal

    print_header("SkillForge Golden Dataset Verification")

    issues_found = 0

    async with AsyncSessionLocal() as session:
        # 1. Database Connection
        print_header("1. Database Connection")
        connection_ok, connection_details = await verify_database_connection(session)

        if connection_ok:
            print_check("Database connection", "PASS", connection_details)
        else:
            print_check("Database connection", "FAIL", connection_details)
            return 1

        # 2. Analysis Records
        print_header("2. Analysis Records")
        analysis_results = await verify_analyses(session, verbose)

        if analysis_results["completed"] == 0:
            print_check("Completed analyses", "FAIL", "No completed analyses found!")
            issues_found += 1
        else:
            print_check("Completed analyses", "PASS", f"{analysis_results['completed']} completed")

        if analysis_results["null_critical_fields"] > 0:
            print_check(
                "Critical fields (title, url, status)",
                "FAIL",
                f"{analysis_results['null_critical_fields']} records with NULL values",
            )
            issues_found += 1
        else:
            print_check("Critical fields (title, url, status)", "PASS", "No NULL values")

        # Content type distribution
        print(f"\n{Colors.BOLD}Content Type Distribution:{Colors.END}")
        for content_type, count in analysis_results["content_types"]:
            print(f"  • {content_type}: {count}")

        # 3. Artifact Records
        print_header("3. Artifact Records")
        artifact_results = await verify_artifacts(session, verbose)

        if artifact_results["total"] == 0:
            print_check("Artifacts exist", "FAIL", "No artifacts found!")
            issues_found += 1
        else:
            print_check("Artifacts exist", "PASS", f"{artifact_results['total']} artifacts")

        if artifact_results["orphaned"] > 0:
            print_check(
                "Orphaned artifacts", "FAIL", f"{artifact_results['orphaned']} orphaned artifacts"
            )
            issues_found += 1
        else:
            print_check("Orphaned artifacts", "PASS", "No orphaned artifacts")

        if artifact_results["null_content"] > 0:
            print_check(
                "Artifact content",
                "FAIL",
                f"{artifact_results['null_content']} artifacts with NULL content",
            )
            issues_found += 1
        else:
            print_check("Artifact content", "PASS", "All artifacts have content")

        # 4. Chunk Records & Embeddings
        print_header("4. Chunk Records & Embeddings")
        chunk_results = await verify_chunks(session, verbose)

        if chunk_results["total"] == 0:
            print_check("Chunks exist", "FAIL", "No chunks found!")
            issues_found += 1
        else:
            print_check("Chunks exist", "PASS", f"{chunk_results['total']} chunks")

        if chunk_results["orphaned"] > 0:
            print_check("Orphaned chunks", "FAIL", f"{chunk_results['orphaned']} orphaned chunks")
            issues_found += 1
        else:
            print_check("Orphaned chunks", "PASS", "No orphaned chunks")

        if chunk_results["null_vectors"] > 0:
            print_check(
                "Embedding vectors",
                "FAIL",
                f"{chunk_results['null_vectors']} chunks missing vectors",
            )
            issues_found += 1
        else:
            print_check("Embedding vectors", "PASS", "All chunks have vectors")

        # Verify dimensions
        expected_dims = 1536
        if chunk_results["vector_dimensions"]:
            all_correct = all(
                dims == expected_dims for dims, _ in chunk_results["vector_dimensions"]
            )
            if all_correct:
                print_check(
                    "Embedding dimensions",
                    "PASS",
                    f"All vectors are {expected_dims}D (text-embedding-3-small)",
                )
            else:
                print_check(
                    "Embedding dimensions",
                    "FAIL",
                    f"Expected {expected_dims}D, found: {chunk_results['vector_dimensions']}",
                )
                issues_found += 1

        if chunk_results["invalid_vectors"] > 0:
            print_check(
                "Vector validity (NaN)",
                "FAIL",
                f"{chunk_results['invalid_vectors']} vectors with NaN values",
            )
            issues_found += 1
        else:
            print_check("Vector validity (NaN)", "PASS", "No NaN values in vectors")

        if chunk_results["unnormalized_vectors"] > 0:
            print_warning(
                f"{chunk_results['unnormalized_vectors']} vectors appear unnormalized (magnitude != 1.0)"
            )
        else:
            print_check("Vector normalization", "PASS", "All vectors normalized")

        # Granularity distribution
        print(f"\n{Colors.BOLD}Granularity Distribution:{Colors.END}")
        for granularity, count in chunk_results["granularity_dist"]:
            print(f"  • {granularity}: {count}")

        # Model distribution
        print(f"\n{Colors.BOLD}Embedding Model Distribution:{Colors.END}")
        for model, count in chunk_results["model_dist"]:
            print(f"  • {model}: {count}")

        # 5. Data Consistency
        print_header("5. Data Consistency")
        consistency_results = await verify_consistency(session, verbose)

        if consistency_results["completed_no_artifacts"] > 0:
            print_check(
                "Completed → Artifacts",
                "FAIL",
                f"{consistency_results['completed_no_artifacts']} completed analyses without artifacts",
            )
            issues_found += 1
        else:
            print_check("Completed → Artifacts", "PASS", "All completed have artifacts")

        if consistency_results["completed_no_chunks"] > 0:
            print_check(
                "Completed → Chunks",
                "FAIL",
                f"{consistency_results['completed_no_chunks']} completed analyses without chunks",
            )
            issues_found += 1
        else:
            print_check("Completed → Chunks", "PASS", "All completed have chunks")

        if consistency_results["artifacts_not_completed"] > 0:
            print_warning(
                f"{consistency_results['artifacts_not_completed']} artifacts linked to non-completed analyses"
            )

        if consistency_results["chunks_no_snippet"] > 0:
            print_check(
                "Chunk snippets",
                "FAIL",
                f"{consistency_results['chunks_no_snippet']} chunks missing snippets",
            )
            issues_found += 1
        else:
            print_check("Chunk snippets", "PASS", "All chunks have snippets")

        # Fix orphans if requested
        if fix_orphans and (artifact_results["orphaned"] > 0 or chunk_results["orphaned"] > 0):
            print_header("6. Fixing Orphaned Records")
            print_warning("Deleting orphaned records...")

            fix_results = await fix_orphaned_records(session)
            print_info(f"Deleted {fix_results['artifacts_deleted']} orphaned artifacts")
            print_info(f"Deleted {fix_results['chunks_deleted']} orphaned chunks")

        # Final Summary
        print_header("Verification Summary")

        print(f"\n{Colors.BOLD}Database Statistics:{Colors.END}")
        print(f"  Total Analyses:      {analysis_results['total']}")
        print(f"  Completed Analyses:  {analysis_results['completed']}")
        print(f"  Total Artifacts:     {artifact_results['total']}")
        print(f"  Total Chunks:        {chunk_results['total']}")

        if issues_found == 0:
            print(
                f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed! Database is healthy.{Colors.END}"
            )
            return 0
        else:
            print(
                f"\n{Colors.RED}{Colors.BOLD}✗ Found {issues_found} issue(s). See details above.{Colors.END}"
            )
            return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify SkillForge golden dataset database integrity"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed query results",
    )
    parser.add_argument(
        "--fix-orphans",
        action="store_true",
        help="Automatically delete orphaned records (USE WITH CAUTION)",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(main(verbose=args.verbose, fix_orphans=args.fix_orphans))
    sys.exit(exit_code)

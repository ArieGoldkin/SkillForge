#!/usr/bin/env python3
"""Add documents to the golden dataset with multi-agent validation.

This script provides comprehensive tooling for curating the golden dataset:
- Fetch and analyze content from URLs
- Classify content type and difficulty
- Generate test queries
- Validate against schema and duplicates
- Write to fixture files with Langfuse tracing

Usage:
    # Add a new document
    poetry run python scripts/data/add_to_golden_dataset.py add \
        --url "https://example.com/article" \
        --content-type article

    # Validate a document before adding
    poetry run python scripts/data/add_to_golden_dataset.py validate \
        --url "https://example.com/article"

    # Check for duplicates
    poetry run python scripts/data/add_to_golden_dataset.py check-duplicate \
        --url "https://example.com/article"

    # Analyze coverage gaps
    poetry run python scripts/data/add_to_golden_dataset.py coverage

    # Validate entire dataset
    poetry run python scripts/data/add_to_golden_dataset.py validate-all

Issue: #599
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

# Langfuse imports (optional, graceful degradation)
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None  # type: ignore

# Constants
FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests/smoke/retrieval/fixtures"
DOCUMENTS_FILE = FIXTURES_DIR / "documents_expanded.json"
QUERIES_FILE = FIXTURES_DIR / "queries.json"
SOURCE_URL_MAP_FILE = FIXTURES_DIR / "source_url_map.json"

FORBIDDEN_URL_PATTERNS = [
    "skillforge.dev",
    "placeholder",
    "example.com",
    "localhost",
    "127.0.0.1",
]

CONTENT_TYPES = [
    "article",
    "tutorial",
    "research_paper",
    "documentation",
    "video_transcript",
    "code_repository",
]

DIFFICULTY_LEVELS = ["trivial", "easy", "medium", "hard", "adversarial"]

DIFFICULTY_THRESHOLDS = {
    "trivial": 0.85,
    "easy": 0.70,
    "medium": 0.55,
    "hard": 0.40,
    "adversarial": 0.20,
}


@dataclass
class ValidationResult:
    """Result of document validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_check: dict[str, Any] = field(default_factory=dict)


@dataclass
class CurationResult:
    """Result of multi-agent curation analysis."""

    quality_score: float
    confidence: float
    decision: Literal["include", "review", "exclude"]

    # Quality dimensions
    accuracy: float
    coherence: float
    depth: float
    relevance: float

    # Classification
    content_type: str
    difficulty: str
    tags: list[str]

    # Generated queries
    suggested_queries: list[dict[str, Any]]

    # Metadata
    warnings: list[str] = field(default_factory=list)
    langfuse_trace_id: str | None = None


def get_langfuse() -> Any | None:
    """Get Langfuse client if available."""
    if not LANGFUSE_AVAILABLE:
        return None
    try:
        return Langfuse()
    except Exception:
        return None


def load_documents() -> list[dict[str, Any]]:
    """Load existing documents from fixture file."""
    if not DOCUMENTS_FILE.exists():
        return []
    with DOCUMENTS_FILE.open() as f:
        data = json.load(f)
        return data.get("documents", [])


def load_queries() -> list[dict[str, Any]]:
    """Load existing queries from fixture file."""
    if not QUERIES_FILE.exists():
        return []
    with QUERIES_FILE.open() as f:
        data = json.load(f)
        return data.get("queries", [])


def load_source_url_map() -> dict[str, str]:
    """Load source URL mappings."""
    if not SOURCE_URL_MAP_FILE.exists():
        return {}
    with SOURCE_URL_MAP_FILE.open() as f:
        return json.load(f)


def save_documents(documents: list[dict[str, Any]]) -> None:
    """Save documents to fixture file."""
    data = {
        "version": "2.0",
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "source": "SkillForge Golden Dataset",
        "documents": documents,
    }
    with DOCUMENTS_FILE.open("w") as f:
        json.dump(data, f, indent=2)


def save_queries(queries: list[dict[str, Any]]) -> None:
    """Save queries to fixture file."""
    data = {
        "version": "1.1",
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "queries": queries,
    }
    with QUERIES_FILE.open("w") as f:
        json.dump(data, f, indent=2)


def save_source_url_map(url_map: dict[str, str]) -> None:
    """Save source URL mappings."""
    with SOURCE_URL_MAP_FILE.open("w") as f:
        json.dump(url_map, f, indent=2)


def generate_document_id(title: str, url: str) -> str:
    """Generate a unique document ID from title."""
    # Convert to kebab-case
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")

    # Truncate if too long
    if len(slug) > 50:
        slug = slug[:50].rsplit("-", 1)[0]

    # Add hash suffix for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:6]

    return f"{slug}-{url_hash}"


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL is not a placeholder and uses HTTPS."""
    for pattern in FORBIDDEN_URL_PATTERNS:
        if pattern in url.lower():
            return False, f"URL contains forbidden pattern: {pattern}"

    parsed = urlparse(url)
    if not parsed.scheme:
        return False, "URL must include scheme (https://)"

    if parsed.scheme != "https":
        # Allow http for arxiv (redirects to https)
        if "arxiv.org" not in url:
            return False, "URL must use HTTPS"

    return True, "OK"


def check_url_duplicate(url: str, source_url_map: dict[str, str]) -> str | None:
    """Check if URL already exists in dataset. Returns doc_id if duplicate."""
    normalized = normalize_url(url)
    for doc_id, existing_url in source_url_map.items():
        if normalize_url(existing_url) == normalized:
            return doc_id
    return None


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    parsed = urlparse(url.lower())
    netloc = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"


def validate_document_schema(document: dict[str, Any]) -> list[str]:
    """Validate document against schema. Returns list of errors."""
    errors = []

    # Required fields
    required = ["id", "title", "source_url", "content_type", "sections"]
    for field in required:
        if field not in document:
            errors.append(f"Missing required field: {field}")

    # ID format
    doc_id = document.get("id", "")
    if not re.match(r"^[a-z0-9-]+$", doc_id):
        errors.append(f"Invalid ID format (must be kebab-case): {doc_id}")

    # Content type
    content_type = document.get("content_type")
    if content_type and content_type not in CONTENT_TYPES:
        errors.append(f"Invalid content_type: {content_type}")

    # Title length
    title = document.get("title", "")
    if len(title) < 10:
        errors.append("Title too short (min 10 chars)")
    if len(title) > 200:
        errors.append("Title too long (max 200 chars)")

    # Sections
    sections = document.get("sections", [])
    if not sections:
        errors.append("Document must have at least 1 section")

    for i, section in enumerate(sections):
        if "id" not in section:
            errors.append(f"Section {i} missing 'id' field")
        if "title" not in section:
            errors.append(f"Section {i} missing 'title' field")
        if "content" not in section:
            errors.append(f"Section {i} missing 'content' field")
        elif len(section.get("content", "")) < 50:
            errors.append(f"Section {section.get('id', i)} content too short (min 50 chars)")

    # Tags
    tags = document.get("tags", [])
    if len(tags) < 2:
        errors.append("Document must have at least 2 tags")

    return errors


def validate_query_references(
    queries: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[str]:
    """Validate query expected_chunks reference valid section IDs."""
    errors = []

    # Build set of valid section IDs
    valid_sections = set()
    for doc in documents:
        for section in doc.get("sections", []):
            valid_sections.add(section["id"])

    # Check each query
    for query in queries:
        for chunk_id in query.get("expected_chunks", []):
            if chunk_id not in valid_sections:
                errors.append(f"Query {query['id']} references invalid section: {chunk_id}")

    return errors


def analyze_coverage(
    documents: list[dict[str, Any]], queries: list[dict[str, Any]]
) -> dict[str, Any]:
    """Analyze dataset coverage and identify gaps."""
    # Content type distribution
    content_types: dict[str, int] = {}
    for doc in documents:
        ct = doc.get("content_type", "unknown")
        content_types[ct] = content_types.get(ct, 0) + 1

    # Tag distribution
    all_tags: list[str] = []
    for doc in documents:
        all_tags.extend(doc.get("tags", []))
    tag_counts: dict[str, int] = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Difficulty distribution
    difficulties: dict[str, int] = {}
    for query in queries:
        diff = query.get("difficulty", "unknown")
        difficulties[diff] = difficulties.get(diff, 0) + 1

    # Identify gaps
    gaps = []
    total_docs = len(documents)

    if total_docs > 0:
        if content_types.get("tutorial", 0) / total_docs < 0.15:
            gaps.append("Under-represented: tutorials (<15%)")
        if content_types.get("research_paper", 0) / total_docs < 0.05:
            gaps.append("Under-represented: research papers (<5%)")

    # Domain coverage
    expected_domains = ["ai-ml", "backend", "frontend", "devops", "security"]
    for domain in expected_domains:
        if tag_counts.get(domain, 0) < 5:
            gaps.append(f"Under-represented domain: {domain} (<5 docs)")

    # Difficulty balance
    total_queries = len(queries)
    if total_queries > 0:
        if difficulties.get("hard", 0) / total_queries < 0.10:
            gaps.append("Under-represented: hard queries (<10%)")
        if difficulties.get("adversarial", 0) / total_queries < 0.05:
            gaps.append("Under-represented: adversarial queries (<5%)")

    return {
        "content_type_distribution": content_types,
        "tag_distribution": dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:20]),
        "difficulty_distribution": difficulties,
        "gaps": gaps,
        "total_documents": total_docs,
        "total_queries": total_queries,
    }


async def fetch_content(url: str) -> dict[str, Any]:
    """Fetch content from URL."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

        return {
            "url": str(response.url),
            "status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content": response.text[:50000],  # Limit size
            "length": len(response.text),
        }


async def validate_before_add(
    url: str,
    content_type: str | None = None,
) -> ValidationResult:
    """Run full validation before adding document."""
    errors = []
    warnings = []

    # Load existing data
    documents = load_documents()
    source_url_map = load_source_url_map()

    # 1. URL validation
    url_valid, url_msg = validate_url(url)
    if not url_valid:
        errors.append(url_msg)

    # 2. URL duplicate check
    url_dup = check_url_duplicate(url, source_url_map)
    duplicate_check = {
        "is_duplicate": url_dup is not None,
        "similar_to": url_dup,
    }
    if url_dup:
        errors.append(f"URL already exists in dataset as: {url_dup}")

    # 3. Content type validation
    if content_type and content_type not in CONTENT_TYPES:
        errors.append(f"Invalid content type: {content_type}")

    # 4. Try to fetch content
    try:
        content_result = await fetch_content(url)
        if content_result["length"] < 500:
            warnings.append("Content is very short (<500 chars)")
        if content_result["length"] > 100000:
            warnings.append("Content is very long (>100k chars)")
    except Exception as e:
        errors.append(f"Failed to fetch URL: {e}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        duplicate_check=duplicate_check,
    )


async def validate_full_dataset() -> dict[str, Any]:
    """Run comprehensive validation on entire dataset."""
    documents = load_documents()
    queries = load_queries()
    source_url_map = load_source_url_map()

    all_errors = []
    all_warnings = []

    # 1. Schema validation for all documents
    for doc in documents:
        errors = validate_document_schema(doc)
        all_errors.extend([f"[{doc.get('id', 'unknown')}] {e}" for e in errors])

    # 2. Unique ID validation
    doc_ids = [d["id"] for d in documents]
    if len(doc_ids) != len(set(doc_ids)):
        duplicates = [id for id in doc_ids if doc_ids.count(id) > 1]
        all_errors.append(f"Duplicate document IDs: {set(duplicates)}")

    query_ids = [q["id"] for q in queries]
    if len(query_ids) != len(set(query_ids)):
        duplicates = [id for id in query_ids if query_ids.count(id) > 1]
        all_errors.append(f"Duplicate query IDs: {set(duplicates)}")

    # 3. Referential integrity
    ref_errors = validate_query_references(queries, documents)
    all_errors.extend(ref_errors)

    # 4. URL validation
    for doc in documents:
        url = doc.get("source_url", "")
        valid, msg = validate_url(url)
        if not valid:
            all_errors.append(f"[{doc['id']}] {msg}")

    # 5. Source URL map consistency
    for doc in documents:
        doc_id = doc["id"]
        if doc_id not in source_url_map:
            all_warnings.append(f"Document {doc_id} not in source_url_map")

    # 6. Difficulty distribution
    requirements = {"trivial": 3, "easy": 3, "medium": 5, "hard": 3}
    difficulties: dict[str, int] = {}
    for query in queries:
        diff = query.get("difficulty", "unknown")
        difficulties[diff] = difficulties.get(diff, 0) + 1

    for level, min_count in requirements.items():
        actual = difficulties.get(level, 0)
        if actual < min_count:
            all_warnings.append(f"Insufficient {level} queries: {actual}/{min_count}")

    # 7. Coverage analysis
    coverage = analyze_coverage(documents, queries)
    all_warnings.extend(coverage["gaps"])

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": all_warnings,
        "coverage": coverage,
        "stats": {
            "documents": len(documents),
            "queries": len(queries),
            "sections": sum(len(d.get("sections", [])) for d in documents),
        },
    }


def print_validation_result(result: dict[str, Any]) -> None:
    """Print validation result in a formatted way."""
    print("\n" + "=" * 60)
    print("GOLDEN DATASET VALIDATION")
    print("=" * 60)

    stats = result["stats"]
    print("\nDataset Statistics:")
    print(f"  Documents: {stats['documents']}")
    print(f"  Queries:   {stats['queries']}")
    print(f"  Sections:  {stats['sections']}")

    if result["errors"]:
        print(f"\n❌ ERRORS ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  • {error}")
    else:
        print("\n✅ No errors found")

    if result["warnings"]:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
        for warning in result["warnings"]:
            print(f"  • {warning}")

    coverage = result["coverage"]
    print("\nContent Type Distribution:")
    for ct, count in coverage["content_type_distribution"].items():
        print(f"  {ct}: {count}")

    print("\nDifficulty Distribution:")
    for diff, count in coverage["difficulty_distribution"].items():
        print(f"  {diff}: {count}")

    print("\n" + "=" * 60)
    print("RESULT:", "✅ VALID" if result["valid"] else "❌ INVALID")
    print("=" * 60)


def print_coverage_analysis(coverage: dict[str, Any]) -> None:
    """Print coverage analysis in a formatted way."""
    print("\n" + "=" * 60)
    print("GOLDEN DATASET COVERAGE ANALYSIS")
    print("=" * 60)

    print(f"\nTotal Documents: {coverage['total_documents']}")
    print(f"Total Queries:   {coverage['total_queries']}")

    print("\nContent Type Distribution:")
    for ct, count in coverage["content_type_distribution"].items():
        pct = count / coverage["total_documents"] * 100 if coverage["total_documents"] > 0 else 0
        print(f"  {ct}: {count} ({pct:.1f}%)")

    print("\nTop Tags:")
    for tag, count in list(coverage["tag_distribution"].items())[:15]:
        print(f"  {tag}: {count}")

    print("\nDifficulty Distribution:")
    for diff, count in coverage["difficulty_distribution"].items():
        pct = count / coverage["total_queries"] * 100 if coverage["total_queries"] > 0 else 0
        print(f"  {diff}: {count} ({pct:.1f}%)")

    if coverage["gaps"]:
        print("\n⚠️  Coverage Gaps:")
        for gap in coverage["gaps"]:
            print(f"  • {gap}")
    else:
        print("\n✅ No coverage gaps identified")

    print("\n" + "=" * 60)


async def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a URL before adding to dataset."""
    result = await validate_before_add(args.url, args.content_type)

    print("\n" + "=" * 60)
    print("PRE-ADDITION VALIDATION")
    print("=" * 60)
    print(f"\nURL: {args.url}")

    if result.errors:
        print(f"\n❌ ERRORS ({len(result.errors)}):")
        for error in result.errors:
            print(f"  • {error}")
    else:
        print("\n✅ No blocking errors")

    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  • {warning}")

    dup = result.duplicate_check
    if dup.get("is_duplicate"):
        print(f"\n🔄 DUPLICATE: Already exists as '{dup['similar_to']}'")

    print("\n" + "=" * 60)
    print("RESULT:", "✅ VALID" if result.valid else "❌ INVALID")
    print("=" * 60)

    return 0 if result.valid else 1


async def cmd_validate_all(args: argparse.Namespace) -> int:
    """Validate entire dataset."""
    result = await validate_full_dataset()
    print_validation_result(result)
    return 0 if result["valid"] else 1


async def cmd_coverage(args: argparse.Namespace) -> int:
    """Analyze dataset coverage."""
    documents = load_documents()
    queries = load_queries()
    coverage = analyze_coverage(documents, queries)
    print_coverage_analysis(coverage)
    return 0


async def cmd_check_duplicate(args: argparse.Namespace) -> int:
    """Check if URL is a duplicate."""
    source_url_map = load_source_url_map()
    dup = check_url_duplicate(args.url, source_url_map)

    print("\n" + "=" * 60)
    print("DUPLICATE CHECK")
    print("=" * 60)
    print(f"\nURL: {args.url}")

    if dup:
        print(f"\n🔄 DUPLICATE FOUND: '{dup}'")
        return 1
    print("\n✅ No duplicate found")
    return 0


async def cmd_add(args: argparse.Namespace) -> int:
    """Add a document to the golden dataset (placeholder for full implementation)."""
    print("\n" + "=" * 60)
    print("ADD TO GOLDEN DATASET")
    print("=" * 60)
    print(f"\nURL: {args.url}")
    print(f"Content Type: {args.content_type or 'auto-detect'}")

    # Validate first
    result = await validate_before_add(args.url, args.content_type)
    if not result.valid:
        print("\n❌ Validation failed:")
        for error in result.errors:
            print(f"  • {error}")
        return 1

    print("\n⚠️  Full add functionality requires the /add-golden command")
    print("   which uses multi-agent analysis for quality evaluation.")
    print("\n   Use Claude Code with: /add-golden " + args.url)

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Golden dataset management tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate URL before adding")
    validate_parser.add_argument("--url", required=True, help="URL to validate")
    validate_parser.add_argument("--content-type", help="Content type hint")

    # validate-all command
    subparsers.add_parser("validate-all", help="Validate entire dataset")

    # coverage command
    subparsers.add_parser("coverage", help="Analyze dataset coverage")

    # check-duplicate command
    dup_parser = subparsers.add_parser("check-duplicate", help="Check for duplicate URL")
    dup_parser.add_argument("--url", required=True, help="URL to check")

    # add command
    add_parser = subparsers.add_parser("add", help="Add document to dataset")
    add_parser.add_argument("--url", required=True, help="Source URL")
    add_parser.add_argument("--content-type", help="Content type")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run appropriate command
    if args.command == "validate":
        return asyncio.run(cmd_validate(args))
    if args.command == "validate-all":
        return asyncio.run(cmd_validate_all(args))
    if args.command == "coverage":
        return asyncio.run(cmd_coverage(args))
    if args.command == "check-duplicate":
        return asyncio.run(cmd_check_duplicate(args))
    if args.command == "add":
        return asyncio.run(cmd_add(args))
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

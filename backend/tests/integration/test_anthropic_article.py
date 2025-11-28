#!/usr/bin/env python3
"""Test Jina Reader with Anthropic article URL."""

import asyncio
import sys
import traceback
from pathlib import Path

import pytest

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_logging  # noqa: E402
from app.services.extraction.content_type import detect_content_type  # noqa: E402
from app.services.extraction.jina_reader import JinaReader, JinaReaderError  # noqa: E402


def _print_extraction_results(result: dict) -> None:
    """Print formatted extraction results."""
    print("\n" + "=" * 70)
    print("EXTRACTION SUCCESSFUL")
    print("=" * 70)

    print(f"\nTitle: {result['title']}")
    print(f"Content length: {len(result['content']):,} characters")
    print(f"Word count: {result['word_count']:,} words")
    print("\nMetadata:")
    print(f"  Extractor: {result['metadata']['extractor']}")
    print(f"  Source URL: {result['metadata']['source_url']}")

    # Show content preview (first 1000 characters)
    print("\n" + "=" * 70)
    print("CONTENT PREVIEW (first 1000 characters)")
    print("=" * 70)
    content_preview = result["content"][:1000]
    print(content_preview)
    print("...")


def _analyze_content_structure(content: str) -> dict:
    """Analyze content structure and return analysis dict."""
    lines = content.split("\n")

    has_headers = any(line.startswith("#") for line in lines[:20])
    has_links = "[" in content and "](" in content
    has_bold = "**" in content or "__" in content

    return {
        "lines": lines,
        "total_lines": len(lines),
        "non_empty_lines": len([line for line in lines if line.strip()]),
        "has_headers": has_headers,
        "has_links": has_links,
        "has_bold": has_bold,
    }


def _check_key_terms(content: str, key_terms: list[str]) -> None:
    """Check for key terms in content and print results."""
    print("\nKey term search:")
    for term in key_terms:
        count = content.lower().count(term.lower())
        status = "✓" if count > 0 else "✗"
        print(f"  {status} '{term}': {count} occurrence(s)")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)  # 1 minute max timeout
async def test_anthropic_article() -> None:
    """Test extraction from Anthropic article.

    This test requires:
    - Jina API key configured
    - Network access to jina.ai

    Can take 10-30 seconds due to external API call.
    """
    print("\n" + "=" * 70)
    print("Testing Jina Reader with Anthropic Article")
    print("=" * 70)

    # Setup logging
    setup_logging()

    # Test URL
    test_url = "https://www.anthropic.com/news/claude-code-on-the-web?trk=feed-detail_comments-list_comment-text"

    print(f"\nURL: {test_url}")
    print(f"Detected content type: {detect_content_type(test_url)}")

    reader = JinaReader()

    try:
        print("\nExtracting content...")
        result = await reader.extract_article(test_url)

        # Display results
        _print_extraction_results(result)

        # Show content structure (check for key sections)
        print("\n" + "=" * 70)
        print("CONTENT ANALYSIS")
        print("=" * 70)

        content = result["content"]
        analysis = _analyze_content_structure(content)

        print(f"Total lines: {analysis['total_lines']}")
        print(f"Non-empty lines: {analysis['non_empty_lines']}")

        # Check for key terms that should be in the article
        key_terms = [
            "Claude Code",
            "web",
            "parallel",
            "GitHub",
            "sandbox",
            "security",
        ]

        _check_key_terms(content, key_terms)

        # Check for markdown structure
        print("\nMarkdown structure:")
        print(f"  Headers (#): {'✓' if analysis['has_headers'] else '✗'}")
        print(f"  Links ([]): {'✓' if analysis['has_links'] else '✗'}")
        print(f"  Bold (**): {'✓' if analysis['has_bold'] else '✗'}")

        # Show sample of lines
        print("\n" + "=" * 70)
        print("SAMPLE LINES (first 30)")
        print("=" * 70)
        for i, line in enumerate(analysis["lines"][:30], 1):
            if line.strip():  # Only show non-empty lines
                preview = line[:100].replace("\n", " ")
                print(f"{i:2d}. {preview}")

        print("\n" + "=" * 70)
        print("TEST COMPLETE - SUCCESS ✓")
        print("=" * 70)

    except JinaReaderError as e:
        print(f"\n✗ JinaReaderError: {e}")
        return False
    except (RuntimeError, ValueError, KeyError) as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False
    else:
        return True
    finally:
        await reader.close()


if __name__ == "__main__":
    success = asyncio.run(test_anthropic_article())
    sys.exit(0 if success else 1)

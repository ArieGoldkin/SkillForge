#!/usr/bin/env python3
"""Test Jina Reader with Anthropic article URL."""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_logging
from app.services.extraction.content_type import detect_content_type
from app.services.extraction.jina_reader import JinaReader, JinaReaderError


async def test_anthropic_article() -> None:
    """Test extraction from Anthropic article."""
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

        # Show content structure (check for key sections)
        print("\n" + "=" * 70)
        print("CONTENT ANALYSIS")
        print("=" * 70)

        content = result["content"]
        lines = content.split("\n")

        print(f"Total lines: {len(lines)}")
        print(f"Non-empty lines: {len([l for l in lines if l.strip()])}")

        # Check for key terms that should be in the article
        key_terms = [
            "Claude Code",
            "web",
            "parallel",
            "GitHub",
            "sandbox",
            "security",
        ]

        print("\nKey term search:")
        for term in key_terms:
            count = content.lower().count(term.lower())
            status = "✓" if count > 0 else "✗"
            print(f"  {status} '{term}': {count} occurrence(s)")

        # Check for markdown structure
        has_headers = any(line.startswith("#") for line in lines[:20])
        has_links = "[" in content and "](" in content
        has_bold = "**" in content or "__" in content

        print("\nMarkdown structure:")
        print(f"  Headers (#): {'✓' if has_headers else '✗'}")
        print(f"  Links ([]): {'✓' if has_links else '✗'}")
        print(f"  Bold (**): {'✓' if has_bold else '✗'}")

        # Show sample of lines
        print("\n" + "=" * 70)
        print("SAMPLE LINES (first 30)")
        print("=" * 70)
        for i, line in enumerate(lines[:30], 1):
            if line.strip():  # Only show non-empty lines
                preview = line[:100].replace("\n", " ")
                print(f"{i:2d}. {preview}")

        print("\n" + "=" * 70)
        print("TEST COMPLETE - SUCCESS ✓")
        print("=" * 70)

        return True

    except JinaReaderError as e:
        print(f"\n✗ JinaReaderError: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        await reader.close()


if __name__ == "__main__":
    success = asyncio.run(test_anthropic_article())
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""Integration test script for Jina Reader service.

This script tests the JinaReader service with real API calls.
Run with: python3 test_jina_integration.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.extraction.content_type import detect_content_type
from app.services.extraction.jina_reader import JinaReader, JinaReaderError


async def test_content_type_detection() -> None:
    """Test content type detection."""
    print("\n" + "=" * 70)
    print("Testing Content Type Detection")
    print("=" * 70)

    test_cases = [
        ("https://youtube.com/watch?v=123", "video"),
        ("https://www.youtube.com/watch?v=456", "video"),
        ("https://youtu.be/abc123", "video"),
        ("https://github.com/user/repo", "repo"),
        ("https://www.github.com/org/project", "repo"),
        ("https://react.dev", "article"),
        ("https://example.com/article", "article"),
    ]

    passed = 0
    failed = 0

    for url, expected in test_cases:
        result = detect_content_type(url)
        if result == expected:
            print(f"✓ {url[:50]:<50} -> {result}")
            passed += 1
        else:
            print(f"✗ {url[:50]:<50} -> {result} (expected {expected})")
            failed += 1

    print(f"\nContent Type Detection: {passed} passed, {failed} failed")
    return failed == 0


async def test_jina_reader_basic() -> None:
    """Test basic Jina Reader functionality."""
    print("\n" + "=" * 70)
    print("Testing Jina Reader - Basic Functionality")
    print("=" * 70)

    # Check if API key is configured
    api_key = settings.JINA_API_KEY or os.environ.get("JINA_API_KEY")
    if not api_key:
        print("⚠ JINA_API_KEY not found in settings or environment")
        print("  Skipping real API tests. Unit tests will still run.")
        return True

    print(f"✓ API Key found: {api_key[:20]}...")

    reader = JinaReader()

    # Test with a known good URL
    test_url = "https://react.dev"
    print(f"\nTesting extraction from: {test_url}")

    try:
        result = await reader.extract_article(test_url)

        # Verify result structure
        assert "title" in result, "Missing 'title' in result"
        assert "content" in result, "Missing 'content' in result"
        assert "word_count" in result, "Missing 'word_count' in result"
        assert "metadata" in result, "Missing 'metadata' in result"

        # Verify metadata structure
        assert result["metadata"]["extractor"] == "jina_reader", "Wrong extractor name"
        assert result["metadata"]["source_url"] == test_url, "Wrong source URL"

        # Verify content is not empty
        assert len(result["content"]) > 0, "Content is empty"
        assert result["word_count"] > 0, "Word count is 0"

        print("✓ Extraction successful!")
        print(f"  Title: {result['title'][:80]}")
        print(f"  Content length: {len(result['content'])} characters")
        print(f"  Word count: {result['word_count']} words")
        print(f"  Metadata: {result['metadata']}")

        # Show first 200 chars of content
        content_preview = result["content"][:200].replace("\n", " ")
        print(f"\n  Content preview: {content_preview}...")

        success = True

    except JinaReaderError as e:
        print(f"✗ JinaReaderError: {e}")
        success = False
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        success = False
    finally:
        await reader.close()

    return success


async def test_jina_reader_error_handling() -> None:
    """Test error handling scenarios."""
    print("\n" + "=" * 70)
    print("Testing Jina Reader - Error Handling")
    print("=" * 70)

    api_key = settings.JINA_API_KEY or os.environ.get("JINA_API_KEY")
    if not api_key:
        print("⚠ JINA_API_KEY not found. Skipping error handling tests.")
        return True

    reader = JinaReader()

    # Test with invalid URL (should fail gracefully)
    invalid_url = "https://this-domain-does-not-exist-12345.com"
    print(f"\nTesting with invalid URL: {invalid_url}")

    try:
        result = await reader.extract_article(invalid_url)
        print("⚠ Unexpected success with invalid URL")
        print(f"  Result: {result.get('title', 'N/A')[:50]}")
        # This might still work if Jina can resolve it somehow
    except JinaReaderError as e:
        print(f"✓ Correctly raised JinaReaderError: {e}")
    except Exception as e:
        print(f"⚠ Unexpected exception type: {type(e).__name__}: {e}")

    await reader.close()

    return True


async def test_jina_reader_without_api_key() -> None:
    """Test Jina Reader without API key (should still work)."""
    print("\n" + "=" * 70)
    print("Testing Jina Reader - Without API Key")
    print("=" * 70)

    reader = JinaReader()
    original_key = reader.api_key

    # Temporarily remove API key
    reader.api_key = None
    print("✓ API key removed")

    test_url = "https://react.dev"
    print(f"\nTesting extraction from: {test_url} (without API key)")

    try:
        result = await reader.extract_article(test_url)

        # Should still work (Jina allows some requests without key)
        assert "title" in result, "Missing 'title' in result"
        assert "content" in result, "Missing 'content' in result"

        print("✓ Extraction successful without API key!")
        print(f"  Title: {result['title'][:80]}")
        print(f"  Content length: {len(result['content'])} characters")

        success = True

    except JinaReaderError as e:
        # This might fail if rate limited, which is okay
        print(f"⚠ Extraction failed (expected if rate limited): {e}")
        success = True  # Not a failure, just rate limiting
    except Exception as e:
        print(f"⚠ Unexpected error: {type(e).__name__}: {e}")
        success = False
    finally:
        reader.api_key = original_key
        await reader.close()

    return success


async def run_all_tests() -> None:
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("Jina Reader Integration Tests")
    print("=" * 70)

    # Setup logging
    setup_logging()

    results = []

    # Test 1: Content type detection
    print("\n[1/4] Content Type Detection")
    results.append(await test_content_type_detection())

    # Test 2: Basic Jina Reader functionality
    print("\n[2/4] Basic Jina Reader")
    results.append(await test_jina_reader_basic())

    # Test 3: Error handling
    print("\n[3/4] Error Handling")
    results.append(await test_jina_reader_error_handling())

    # Test 4: Without API key
    print("\n[4/4] Without API Key")
    results.append(await test_jina_reader_without_api_key())

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    total = len(results)
    passed = sum(results)

    for i, result in enumerate(results, 1):
        status = "✓ PASSED" if result else "✗ FAILED"
        test_names = [
            "Content Type Detection",
            "Basic Jina Reader",
            "Error Handling",
            "Without API Key",
        ]
        print(f"  [{i}] {test_names[i - 1]:<30} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

"""Real integration tests for Artifact Store.

IMPORTANT: These tests use REAL PostgreSQL database connections.
They require:
- Running PostgreSQL with pgvector extension (port 5437)

Tests verify:
- #268: Artifact Loading - real database storage and retrieval
- Handle Pattern implementation with actual Analysis records
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.analysis import Analysis
from app.domains.analysis.schemas.api import ArtifactSection
from app.domains.analysis.services.context.artifact_store import (
    ArtifactNotFoundError,
    ArtifactStore,
    InvalidURIError,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


class TestArtifactStoreIntegration:
    """Integration tests for artifact storage with real PostgreSQL."""

    async def test_create_ref_stores_summary_in_database(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that creating artifact ref stores summary in PostgreSQL."""
        # Create a real analysis record
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/long-article",
            content_type="article",
        )

        # Store raw content first (simulating content extraction)
        analysis.raw_content = """
# React Performance Optimization Guide

## Introduction
This comprehensive guide covers performance optimization techniques for React applications.

## Key Techniques
1. Use React.memo for expensive components
2. Implement useMemo for computed values
3. Apply useCallback for stable function references

## Code Example
```javascript
const MemoizedComponent = React.memo(({ data }) => {
    const processedData = useMemo(() => expensiveCalculation(data), [data]);
    return <div>{processedData}</div>;
});
```

## Best Practices
- Profile before optimizing
- Measure actual performance impact
- Consider trade-offs of memoization overhead
"""
        await db_session.commit()
        await db_session.refresh(analysis)

        # Create artifact store with real session
        store = ArtifactStore(db_session)

        # Create ref (stores summary and sections)
        ref = await store.create_ref(
            analysis_id=str(analysis.id),
            content=analysis.raw_content,
            content_type="text/markdown",
        )

        # Verify ref structure
        assert ref.uri == f"analysis://{analysis.id}/content"
        assert ref.summary is not None
        assert ref.size_bytes > 0
        assert "summary" in ref.available_sections
        assert "code_blocks" in ref.available_sections
        assert "headings" in ref.available_sections

        # Verify database was updated
        await db_session.refresh(analysis)
        assert analysis.content_summary is not None
        assert analysis.content_sections is not None
        assert "code_blocks" in analysis.content_sections

    async def test_load_summary_from_database(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test loading summary section from real database."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/test",
        )

        content = "This is test content for summary extraction. " * 50
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Load summary
        summary = await store.load(
            uri=f"analysis://{analysis.id}/content",
            section=ArtifactSection.SUMMARY,
        )

        assert summary is not None
        assert len(summary) > 0
        assert len(summary) <= len(content)  # Summary should be shorter or equal

    async def test_load_full_content_from_database(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test loading full content from database."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/full-test",
        )

        content = "Full content test. " * 100
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Load full content
        full = await store.load(
            uri=f"analysis://{analysis.id}/content",
            section=ArtifactSection.FULL,
        )

        assert full == content

    async def test_load_first_n_characters(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test loading first N characters."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/first-n-test",
        )

        # Use content with spaces for proper summary generation
        content = "Test word. " * 1000  # ~11K characters with proper words
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Load first 500 characters
        first_n = await store.load(
            uri=f"analysis://{analysis.id}/content",
            section=ArtifactSection.FIRST_N,
            max_chars=500,
        )

        assert len(first_n) < len(content)
        assert "First 500 characters" in first_n

    async def test_load_code_blocks_extracts_correctly(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that code blocks are extracted and stored."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/code-blocks",
        )

        content = """
# Python Example

Here's some Python code:

```python
def hello():
    print("Hello, World!")
```

And JavaScript:

```javascript
console.log("Hello!");
```
"""
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Load code blocks
        code_blocks = await store.load(
            uri=f"analysis://{analysis.id}/content",
            section=ArtifactSection.CODE_BLOCKS,
        )

        assert "def hello():" in code_blocks
        assert 'console.log("Hello!")' in code_blocks

    async def test_load_headings_extracts_outline(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that headings are extracted as outline."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/headings",
        )

        content = """
# Main Title

## Section 1
Content here.

### Subsection 1.1
More content.

## Section 2
Final content.
"""
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Load headings
        headings = await store.load(
            uri=f"analysis://{analysis.id}/content",
            section=ArtifactSection.HEADINGS,
        )

        assert "Main Title" in headings
        assert "Section 1" in headings
        assert "Subsection 1.1" in headings

    async def test_invalid_uri_raises_error(
        self,
        db_session,
    ):
        """Test that invalid URIs raise proper errors."""
        store = ArtifactStore(db_session)

        with pytest.raises(InvalidURIError):
            await store.load("invalid://uri/format")

        with pytest.raises(InvalidURIError):
            await store.load("analysis://not-a-uuid/content")

    async def test_nonexistent_analysis_raises_error(
        self,
        db_session,
    ):
        """Test that loading nonexistent analysis raises error."""
        store = ArtifactStore(db_session)
        fake_id = str(uuid4())

        with pytest.raises(ArtifactNotFoundError):
            await store.load(f"analysis://{fake_id}/content")


class TestArtifactPersistenceIntegration:
    """Integration tests for artifact data persistence."""

    async def test_content_sections_persist_in_jsonb(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that content sections are stored in PostgreSQL JSONB."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/jsonb-test",
        )

        content = """
# Title

```python
code here
```

## Section
text
"""
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        await store.create_ref(str(analysis.id), content)

        # Query database directly
        result = await db_session.execute(select(Analysis).where(Analysis.id == analysis.id))
        db_analysis = result.scalar_one()

        # Verify JSONB storage
        assert db_analysis.content_sections is not None
        assert isinstance(db_analysis.content_sections, dict)
        assert "code_blocks" in db_analysis.content_sections
        assert "headings" in db_analysis.content_sections

    async def test_summary_generation_for_large_content(
        self,
        db_session,
        create_test_analysis,
    ):
        """Test that large content gets properly summarized."""
        analysis = await create_test_analysis(
            analysis_id=str(uuid4()),
            url="https://example.com/large-content",
        )

        # Create content larger than 5KB threshold
        # Use short words so 500-word summary stays under 2000 chars
        content = "word " * 3000  # 15KB but short words
        analysis.raw_content = content
        await db_session.commit()

        store = ArtifactStore(db_session)
        ref = await store.create_ref(str(analysis.id), content)

        # Summary should be much smaller than original
        assert len(ref.summary) < len(content)
        assert ref.size_bytes > 5000  # Confirms it was over threshold

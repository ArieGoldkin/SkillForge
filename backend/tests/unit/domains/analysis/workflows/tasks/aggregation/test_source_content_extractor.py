"""Unit tests for source content extraction (Issue #487 - Hallucination Prevention)."""

from app.domains.analysis.workflows.tasks.aggregation.source_content_extractor import (
    extract_key_terms,
    extract_source_summary,
    truncate_at_word_boundary,
)


class TestTruncateAtWordBoundary:
    """Test text truncation at word boundaries."""

    def test_no_truncation_needed(self):
        """Test text shorter than max_chars is not truncated."""
        text = "Hello world"
        result = truncate_at_word_boundary(text, max_chars=100)
        assert result == "Hello world"
        assert "..." not in result

    def test_truncate_at_space(self):
        """Test truncation occurs at last space before max_chars."""
        text = "Hello world this is a test"
        result = truncate_at_word_boundary(text, max_chars=15)
        assert result == "Hello world..."
        assert len(result) <= 15

    def test_exact_boundary(self):
        """Test when text length equals max_chars."""
        text = "Hello world"
        result = truncate_at_word_boundary(text, max_chars=11)
        assert result == "Hello world"

    def test_no_spaces_before_limit(self):
        """Test truncation when no spaces exist before limit."""
        text = "Verylongwordwithoutspaces and more text"
        result = truncate_at_word_boundary(text, max_chars=15)
        # Should truncate at max_chars - 3 for "..."
        assert result.endswith("...")
        assert len(result) == 15

    def test_ellipsis_added(self):
        """Test ellipsis is added when text is truncated."""
        text = "This is a very long sentence that needs truncation"
        result = truncate_at_word_boundary(text, max_chars=20)
        assert result.endswith("...")

    def test_empty_text(self):
        """Test handling of empty text."""
        result = truncate_at_word_boundary("", max_chars=100)
        assert result == ""

    def test_single_word_longer_than_limit(self):
        """Test single long word gets truncated with ellipsis."""
        text = "Supercalifragilisticexpialidocious"
        result = truncate_at_word_boundary(text, max_chars=15)
        # Should truncate at max_chars - 3 for "..."
        assert result.endswith("...")
        assert len(result) == 15

    def test_multiple_spaces(self):
        """Test handling of multiple consecutive spaces."""
        text = "Hello    world    this    is    a    test"
        result = truncate_at_word_boundary(text, max_chars=20)
        assert "..." in result
        assert len(result) <= 20


class TestExtractKeyTerms:
    """Test key term extraction from text."""

    def test_extract_basic_terms(self):
        """Test extraction of basic technical terms."""
        text = "Python FastAPI REST API Python development backend"
        result = extract_key_terms(text, top_n=5)
        assert "python" in result
        assert "fastapi" in result
        # Note: "rest" is only 4 chars and included, "api" is 3 chars and filtered

    def test_filter_stopwords(self):
        """Test common stopwords are filtered out."""
        text = "The and of to with for in that have this but"
        result = extract_key_terms(text, top_n=10)
        assert "the" not in result
        assert "and" not in result
        assert "with" not in result

    def test_filter_short_words(self):
        """Test words shorter than 4 characters are filtered."""
        text = "API SQL DB REST HTTP PostgreSQL database system"
        result = extract_key_terms(text, top_n=10)
        # Short words (3 chars or less) should be filtered
        assert "api" not in result
        assert "sql" not in result
        # Long words should be included
        assert "postgresql" in result
        assert "database" in result
        assert "system" in result

    def test_frequency_ranking(self):
        """Test terms are ranked by frequency."""
        text = "Python Python Python FastAPI FastAPI TypeScript"
        result = extract_key_terms(text, top_n=10)
        # Python appears 3 times, should be first
        assert result[0] == "python"
        assert result[1] == "fastapi"
        assert result[2] == "typescript"

    def test_case_insensitive(self):
        """Test extraction is case-insensitive."""
        text = "PYTHON Python python FASTAPI fastapi"
        result = extract_key_terms(text, top_n=5)
        # Should count all variants together
        assert "python" in result
        assert "fastapi" in result

    def test_alphanumeric_only(self):
        """Test only alphanumeric words are extracted."""
        text = "Python-based FastAPI & PostgreSQL (database) system!"
        result = extract_key_terms(text, top_n=10)
        # Hyphenated words split, special chars removed
        assert "python" in result
        assert "based" in result
        assert "fastapi" in result
        assert "postgresql" in result

    def test_limit_top_n(self):
        """Test only top N terms are returned."""
        text = " ".join([f"term{i}" for i in range(50)])
        result = extract_key_terms(text, top_n=10)
        assert len(result) == 10

    def test_empty_text(self):
        """Test handling of empty text."""
        result = extract_key_terms("", top_n=10)
        assert result == []

    def test_only_stopwords(self):
        """Test handling when only stopwords are present."""
        text = "the and of to with for in that have this"
        result = extract_key_terms(text, top_n=10)
        assert result == []

    def test_only_short_words(self):
        """Test handling when only short words are present."""
        text = "a an is it to by or if on up"
        result = extract_key_terms(text, top_n=10)
        assert result == []

    def test_real_technical_content(self):
        """Test extraction from realistic technical text."""
        text = """
        LangGraph is a framework for building stateful, multi-agent applications
        with LLMs. It extends LangChain to add support for cyclical execution and
        human-in-the-loop workflows. LangGraph uses a graph structure where nodes
        represent functions and edges represent data flow between nodes. The framework
        supports checkpointing for persistence and streaming for real-time updates.
        """
        result = extract_key_terms(text, top_n=10)
        assert "langgraph" in result
        assert "framework" in result
        assert "nodes" in result
        # Note: LangChain appears only once, so it may not be in top 10 by frequency


class TestExtractSourceSummary:
    """Test complete source summary extraction."""

    def test_extract_complete_summary(self):
        """Test extraction with complete metadata and content."""
        raw_content = "Python is a high-level programming language. It supports multiple paradigms."
        metadata = {"title": "Python Guide"}
        result = extract_source_summary(raw_content, metadata, max_chars=100)

        assert result["title"] == "Python Guide"
        assert "Python" in result["summary"]
        assert "python" in result["key_terms"]
        assert "programming" in result["key_terms"]
        assert "language" in result["key_terms"]

    def test_default_title(self):
        """Test default title when not provided."""
        result = extract_source_summary("Some content", {}, max_chars=100)
        assert result["title"] == "Untitled"

    def test_summary_truncation(self):
        """Test summary is truncated to max_chars."""
        long_content = "This is a very long article. " * 100
        result = extract_source_summary(long_content, {}, max_chars=50)

        assert len(result["summary"]) <= 50
        assert result["summary"].endswith("...")

    def test_key_terms_limit(self):
        """Test key terms are limited to top 20."""
        content = " ".join([f"term{i}" for i in range(100)])
        result = extract_source_summary(content, {}, max_chars=5000)

        assert len(result["key_terms"]) <= 20

    def test_empty_content(self):
        """Test handling of empty content."""
        result = extract_source_summary("", {"title": "Empty"}, max_chars=100)

        assert result["title"] == "Empty"
        assert result["summary"] == ""
        assert result["key_terms"] == []

    def test_non_string_title(self):
        """Test handling when title is not a string."""
        result = extract_source_summary("Content", {"title": 123}, max_chars=100)
        assert result["title"] == "123"

    def test_null_title(self):
        """Test handling when title is None."""
        result = extract_source_summary("Content", {"title": None}, max_chars=100)
        assert result["title"] == "Untitled"

    def test_real_article_content(self):
        """Test extraction from realistic article content."""
        content = """
        FastAPI is a modern, fast (high-performance) web framework for building APIs
        with Python 3.8+ based on standard Python type hints. The key features are:

        - Fast to code: Increase the speed to develop features by about 200% to 300%
        - Fewer bugs: Reduce about 40% of human (developer) induced errors
        - Intuitive: Great editor support with completion everywhere
        - Easy: Designed to be easy to use and learn
        - Short: Minimize code duplication with multiple features from each parameter
        - Robust: Get production-ready code with automatic interactive documentation
        - Standards-based: Based on OpenAPI and JSON Schema
        """
        metadata = {"title": "FastAPI Framework Guide", "author": "John Doe"}
        result = extract_source_summary(content, metadata, max_chars=200)

        assert result["title"] == "FastAPI Framework Guide"
        assert len(result["summary"]) <= 200
        assert "fastapi" in result["key_terms"]
        assert "python" in result["key_terms"]
        assert "framework" in result["key_terms"]
        assert "features" in result["key_terms"]

    def test_summary_structure(self):
        """Test returned structure has all required fields."""
        result = extract_source_summary("Test content", {"title": "Test"}, max_chars=100)

        assert "title" in result
        assert "summary" in result
        assert "key_terms" in result
        assert isinstance(result["title"], str)
        assert isinstance(result["summary"], str)
        assert isinstance(result["key_terms"], list)

    def test_very_short_max_chars(self):
        """Test handling with very short max_chars limit."""
        content = "This is a test of the emergency broadcast system"
        result = extract_source_summary(content, {}, max_chars=10)

        assert len(result["summary"]) <= 10
        assert result["summary"].endswith("...")

    def test_technical_content_key_terms(self):
        """Test key terms from technical documentation."""
        content = """
        PostgreSQL is a powerful open-source object-relational database system
        that uses and extends the SQL language combined with many features that
        safely store and scale the most complicated data workloads. PostgreSQL
        supports vector similarity search through the pgvector extension, which
        enables efficient storage and retrieval of embeddings for RAG applications.
        The HNSW index provides fast approximate nearest neighbor search.
        """
        result = extract_source_summary(content, {"title": "PostgreSQL Guide"}, max_chars=2000)

        # Technical terms should be extracted (top terms by frequency)
        assert "postgresql" in result["key_terms"]
        assert "database" in result["key_terms"] or "search" in result["key_terms"]
        # Note: Single-occurrence terms like "pgvector", "hnsw" may not be in top 20
        # if other terms appear more frequently

        # Common words should be filtered
        assert "that" not in result["key_terms"]
        assert "with" not in result["key_terms"]
        assert "the" not in result["key_terms"]

    def test_special_characters_in_content(self):
        """Test handling of special characters in content."""
        content = (
            "Python's FastAPI (v0.115.0) uses type-hints & async/await for high-performance APIs!"
        )
        result = extract_source_summary(content, {}, max_chars=200)

        assert "python" in result["key_terms"]
        assert "fastapi" in result["key_terms"]
        assert "performance" in result["key_terms"]

    def test_unicode_content(self):
        """Test handling of Unicode characters."""
        content = "Python 支持 Unicode 字符串 and multilingual content処理"
        result = extract_source_summary(content, {"title": "Unicode Test"}, max_chars=200)

        assert result["title"] == "Unicode Test"
        assert len(result["summary"]) > 0
        assert "python" in result["key_terms"]

    def test_default_max_chars(self):
        """Test default max_chars parameter."""
        long_content = "Word " * 1000  # 5000 chars
        result = extract_source_summary(long_content, {})

        # Default is 2000 chars
        assert len(result["summary"]) <= 2000

"""Unit tests for grounding_validator module.

Tests the hallucination prevention system that validates LLM synthesis output
is grounded in source content by comparing key technical terms.

Issue #487 - Prevents hallucinations in multi-agent synthesis.
"""

import pytest

from app.domains.analysis.workflows.tasks.aggregation.grounding_validator import (
    COMMON_STOPWORDS,
    calculate_grounding_score,
    extract_key_terms,
    validate_grounding,
)


class TestExtractKeyTerms:
    """Tests for extract_key_terms function."""

    def test_extract_basic_terms(self) -> None:
        """Extract terms from simple text."""
        text = "Python programming language enables developers"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        assert "python" in terms
        assert "programming" in terms
        assert "language" in terms
        assert "enables" in terms
        assert "developers" in terms

    def test_filter_short_words(self) -> None:
        """Words shorter than min_length are filtered out."""
        text = "The API is a new way to code for the web"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        # Short words should be filtered
        assert "the" not in terms
        assert "api" not in terms  # 3 chars
        assert "is" not in terms
        assert "a" not in terms
        assert "new" not in terms  # 3 chars
        assert "way" not in terms  # 3 chars
        assert "to" not in terms
        assert "for" not in terms

        # Long enough words should be kept
        assert "code" in terms

    def test_filter_stopwords(self) -> None:
        """Common stopwords are filtered out."""
        text = "This programming language will have been working with that"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        # These are stopwords
        assert "this" not in terms
        assert "will" not in terms
        assert "have" not in terms
        assert "been" not in terms
        assert "with" not in terms
        assert "that" not in terms

        # These are not stopwords
        assert "programming" in terms
        assert "language" in terms
        assert "working" in terms

    def test_case_insensitive(self) -> None:
        """Terms are normalized to lowercase."""
        text = "PYTHON Python python FASTAPI FastAPI fastapi"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        assert "python" in terms
        assert "fastapi" in terms
        # Original case should not appear
        assert "PYTHON" not in terms
        assert "Python" not in terms
        assert "FASTAPI" not in terms

    def test_limit_top_n(self) -> None:
        """Only top N terms are returned."""
        text = "apple banana cherry date elderberry fig grape honeydew"
        terms = extract_key_terms(text, min_length=4, top_n=3)

        assert len(terms) <= 3

    def test_frequency_ranking(self) -> None:
        """More frequent terms should be included."""
        text = "python python python java java javascript"
        terms = extract_key_terms(text, min_length=4, top_n=2)

        # Python appears 3x, java 2x, javascript 1x
        # Top 2 should be python and java
        assert "python" in terms
        assert "java" in terms or "javascript" in terms

    def test_empty_text(self) -> None:
        """Empty text returns empty set."""
        terms = extract_key_terms("", min_length=4, top_n=10)
        assert terms == set()

    def test_only_stopwords(self) -> None:
        """Text with only stopwords returns empty set."""
        text = "the and or but if then when"
        terms = extract_key_terms(text, min_length=4, top_n=10)
        assert terms == set()

    def test_only_short_words(self) -> None:
        """Text with only short words returns empty set."""
        text = "a is to be or not for"
        terms = extract_key_terms(text, min_length=4, top_n=10)
        assert terms == set()

    def test_punctuation_removal(self) -> None:
        """Punctuation is stripped from terms."""
        text = "python, javascript; typescript: golang. rust!"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        assert "python" in terms
        assert "javascript" in terms
        assert "typescript" in terms
        assert "golang" in terms
        assert "rust" in terms
        # Punctuated versions should not appear
        assert "python," not in terms
        assert "javascript;" not in terms

    def test_alphanumeric_only(self) -> None:
        """Terms must contain at least one letter."""
        text = "12345 6789 http2 h264 mp3 123abc"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        # Pure numbers should be filtered
        assert "12345" not in terms
        assert "6789" not in terms
        # Alphanumeric should be kept
        assert "http2" in terms
        assert "h264" in terms
        assert "123abc" in terms

    def test_real_technical_content(self) -> None:
        """Extract terms from realistic technical content."""
        text = """
        LangGraph enables building stateful, multi-agent applications with LLMs.
        The framework provides checkpointing, state management, and agent coordination.
        Built on LangChain, it supports Python and TypeScript implementations.
        """
        terms = extract_key_terms(text, min_length=4, top_n=20)

        # Technical terms should be extracted
        assert "langgraph" in terms
        assert "stateful" in terms
        assert "applications" in terms
        assert "framework" in terms
        assert "checkpointing" in terms
        assert "python" in terms
        assert "typescript" in terms

    def test_quoted_text(self) -> None:
        """Handle quoted strings properly."""
        text = '"Python" is a "programming" \'language\' with `async` support'
        terms = extract_key_terms(text, min_length=4, top_n=10)

        assert "python" in terms
        assert "programming" in terms
        assert "language" in terms
        assert "async" in terms

    def test_hyphenated_words(self) -> None:
        """Handle hyphenated words by stripping hyphens."""
        text = "multi-agent state-machine real-time"
        terms = extract_key_terms(text, min_length=4, top_n=10)

        # After stripping leading/trailing hyphens
        # "multi-agent" becomes "multi-agent" (internal hyphen kept during split)
        # Actually, split() breaks on whitespace, so "multi-agent" is one word
        # Then strip removes leading/trailing punctuation including hyphens
        # So "multi-agent" -> "multi-agent" (no change, hyphen is internal)
        assert any("multi" in term or "agent" in term for term in terms)


class TestCalculateGroundingScore:
    """Tests for calculate_grounding_score function."""

    def test_full_overlap(self) -> None:
        """Perfect overlap returns 1.0."""
        source = {"python", "fastapi", "postgresql"}
        output = {"python", "fastapi", "postgresql"}
        score = calculate_grounding_score(source, output)
        assert score == 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap returns correct ratio."""
        source = {"python", "fastapi", "postgresql"}
        output = {"python", "fastapi", "mongodb", "redis"}  # 2/4 overlap
        score = calculate_grounding_score(source, output)
        assert score == 0.5

    def test_no_overlap(self) -> None:
        """No overlap returns 0.0."""
        source = {"python", "fastapi", "postgresql"}
        output = {"java", "spring", "mysql"}
        score = calculate_grounding_score(source, output)
        assert score == 0.0

    def test_empty_output_terms(self) -> None:
        """Empty output terms returns 0.0."""
        source = {"python", "fastapi"}
        output: set[str] = set()
        score = calculate_grounding_score(source, output)
        assert score == 0.0

    def test_empty_source_terms(self) -> None:
        """Empty source terms returns 0.0 (no overlap possible)."""
        source: set[str] = set()
        output = {"python", "fastapi"}
        score = calculate_grounding_score(source, output)
        assert score == 0.0

    def test_output_subset_of_source(self) -> None:
        """Output fully contained in source returns 1.0."""
        source = {"python", "fastapi", "postgresql", "redis", "docker"}
        output = {"python", "fastapi"}  # 2/2 overlap
        score = calculate_grounding_score(source, output)
        assert score == 1.0

    def test_single_term_match(self) -> None:
        """Single matching term."""
        source = {"python", "fastapi", "postgresql"}
        output = {"python"}
        score = calculate_grounding_score(source, output)
        assert score == 1.0

    def test_large_output_few_matches(self) -> None:
        """Large output with few source matches."""
        source = {"langchain", "langgraph"}
        output = {
            "anthropic",
            "claude",
            "openai",
            "gpt4",
            "langchain",
            "llm",
            "rag",
            "embeddings",
            "vectors",
            "pinecone",
        }  # 1/10 overlap
        score = calculate_grounding_score(source, output)
        assert score == pytest.approx(0.1, rel=0.01)


class TestValidateGrounding:
    """Tests for validate_grounding function."""

    def test_well_grounded_content(self) -> None:
        """Content with high overlap passes validation."""
        source = """
        LangGraph enables building stateful multi-agent applications.
        It provides checkpointing and state management for LLM workflows.
        Built on LangChain with Python and TypeScript support.
        """
        generated = """
        LangGraph is a framework for multi-agent applications using LLMs.
        Key features include checkpointing and state management.
        Works with LangChain ecosystem and supports Python.
        """
        is_grounded, score, warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert is_grounded is True
        assert score >= 0.15
        assert len(warnings) == 0

    def test_hallucinated_content(self) -> None:
        """Content about unrelated topic fails validation."""
        source = """
        Alibaba announced Qwen3-Next, their next generation AI model.
        The model focuses on improved reasoning capabilities.
        Training includes enhanced Chinese language support.
        """
        generated = """
        Anthropic Claude is an AI assistant built with Constitutional AI.
        The Claude API provides streaming and function calling features.
        Implementation uses Python SDK with async support.
        """
        is_grounded, score, warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert is_grounded is False
        assert score < 0.15
        assert len(warnings) > 0
        assert "hallucination" in warnings[0].lower()

    def test_custom_threshold(self) -> None:
        """Custom min_overlap threshold is respected."""
        source = "python programming fastapi framework"
        generated = "python java spring mongodb redis"

        # With low threshold, should pass
        is_grounded, _score, _ = validate_grounding(source, generated, min_overlap=0.05)
        assert is_grounded is True  # 1/5 = 0.2 >= 0.05

        # With high threshold, should fail
        is_grounded, _score, _ = validate_grounding(source, generated, min_overlap=0.5)
        assert is_grounded is False  # 0.2 < 0.5

    def test_empty_source(self) -> None:
        """Empty source content returns low score."""
        source = ""
        generated = "python fastapi postgresql"
        is_grounded, score, _warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert score == 0.0
        assert is_grounded is False

    def test_empty_generated(self) -> None:
        """Empty generated content returns low score."""
        source = "python fastapi postgresql"
        generated = ""
        is_grounded, score, _warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert score == 0.0
        assert is_grounded is False

    def test_returns_tuple_structure(self) -> None:
        """Validate return type structure."""
        source = "python programming"
        generated = "python coding"
        result = validate_grounding(source, generated)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)  # is_grounded
        assert isinstance(result[1], float)  # score
        assert isinstance(result[2], list)  # warnings

    def test_score_range(self) -> None:
        """Score is always between 0.0 and 1.0."""
        test_cases = [
            ("python", "python"),  # Perfect match
            ("python", "java"),  # No match
            ("a b c", "x y z"),  # Short words filtered
            ("the and or", "is was been"),  # Only stopwords
        ]

        for source, generated in test_cases:
            _, score, _ = validate_grounding(source, generated)
            assert 0.0 <= score <= 1.0

    def test_warnings_content(self) -> None:
        """Warnings contain useful information about hallucination."""
        source = "alibaba qwen3 chinese model training"
        generated = "anthropic claude api streaming implementation"

        is_grounded, _, warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert is_grounded is False
        assert len(warnings) > 0
        warning = warnings[0]
        # Should mention grounding score
        assert "grounding score" in warning.lower()
        # Should mention threshold
        assert "threshold" in warning.lower()

    def test_technical_article_grounding(self) -> None:
        """Test with realistic technical article content."""
        source = """
        FastAPI is a modern Python web framework for building APIs.
        It supports async/await, automatic OpenAPI documentation,
        dependency injection, and type hints with Pydantic validation.
        Performance is comparable to NodeJS and Go frameworks.
        """
        generated = """
        FastAPI provides a high-performance framework for Python APIs.
        Key features include OpenAPI generation, Pydantic validation,
        and async request handling. The framework uses Python type hints
        for automatic documentation and request validation.
        """

        is_grounded, score, warnings = validate_grounding(source, generated, min_overlap=0.15)

        assert is_grounded is True
        assert score > 0.3  # Should have good overlap
        assert len(warnings) == 0

    def test_partial_hallucination(self) -> None:
        """Some grounded content mixed with hallucinations."""
        source = """
        LangGraph is for building multi-agent workflows.
        It uses state graphs for coordination.
        """
        generated = """
        LangGraph enables multi-agent workflows with state management.
        Also consider using AutoGPT for autonomous agents,
        BabyAGI for task planning, and CrewAI for agent teams.
        """
        # Some overlap (langgraph, multi-agent, workflows, state)
        # But also new terms (autogpt, babyagi, crewai)

        _is_grounded, score, _ = validate_grounding(source, generated, min_overlap=0.15)

        # Should still pass with reasonable overlap
        assert score > 0  # Has some valid terms
        # But score won't be very high due to hallucinated terms


class TestCommonStopwords:
    """Tests for COMMON_STOPWORDS constant."""

    def test_stopwords_exist(self) -> None:
        """Stopwords set is populated."""
        assert len(COMMON_STOPWORDS) > 50

    def test_common_words_included(self) -> None:
        """Common English words are in stopwords."""
        common = ["the", "and", "is", "it", "to", "of", "a", "in", "for", "on"]
        for word in common:
            assert word in COMMON_STOPWORDS

    def test_technical_terms_not_included(self) -> None:
        """Technical terms are not stopwords."""
        technical = [
            "python",
            "javascript",
            "api",
            "database",
            "framework",
            "algorithm",
            "function",
            "class",
        ]
        for word in technical:
            assert word not in COMMON_STOPWORDS

    def test_all_lowercase(self) -> None:
        """All stopwords are lowercase."""
        for word in COMMON_STOPWORDS:
            assert word == word.lower()

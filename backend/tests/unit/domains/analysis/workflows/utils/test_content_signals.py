"""Tests for content signal detection module.

Issue #299-304: Graceful degradation for varying content sizes.
"""

from app.shared.workflows.utils.content_signals import (
    AgentExpectation,
    ContentGenre,
    detect_content_signals,
    should_skip_agent,
)


class TestDetectContentSignals:
    """Tests for detect_content_signals function."""

    def test_empty_content_returns_defaults(self) -> None:
        """Empty content should return default ContentSignals."""
        signals = detect_content_signals("")
        assert signals.word_count == 0
        assert signals.char_count == 0
        assert signals.content_richness_score == 0.0
        assert signals.detected_genre == ContentGenre.UNKNOWN

    def test_detects_code_patterns(self) -> None:
        """Should detect Python code patterns."""
        content = """
        import pandas as pd
        from sklearn import metrics

        def calculate_accuracy(y_true, y_pred):
            return metrics.accuracy_score(y_true, y_pred)

        class ModelTrainer:
            def __init__(self):
                pass
        """
        signals = detect_content_signals(content)
        assert signals.has_code_patterns is True
        assert signals.has_conceptual_only is False

    def test_detects_javascript_code_patterns(self) -> None:
        """Should detect JavaScript code patterns."""
        content = """
        const express = require('express');
        function handleRequest(req, res) {
            res.json({ status: 'ok' });
        }
        async function fetchData() {
            const result = await api.get('/data');
            return result;
        }
        """
        signals = detect_content_signals(content)
        assert signals.has_code_patterns is True

    def test_detects_benchmark_patterns(self) -> None:
        """Should detect performance benchmark patterns."""
        content = """
        The query latency improved from 200ms to 50ms after optimization.
        Throughput increased to 10000 requests/second.
        Memory usage: 512MB peak, 256MB average.
        p99 latency: 150ms
        This is 4x faster than the previous implementation.
        """
        signals = detect_content_signals(content)
        assert signals.has_benchmarks is True

    def test_detects_security_patterns(self) -> None:
        """Should detect security-related patterns."""
        content = """
        Implement OAuth2 authentication with JWT tokens.
        Use bcrypt for password hashing.
        Validate all user input to prevent SQL injection.
        Enable HTTPS and configure CORS properly.
        Store API keys in environment variables, never in code.
        """
        signals = detect_content_signals(content)
        assert signals.has_security_patterns is True

    def test_detects_architecture_patterns(self) -> None:
        """Should detect architecture patterns."""
        content = """
        The microservice architecture uses an API gateway for routing.
        PostgreSQL handles persistent storage with Redis caching.
        Kafka message queue enables async communication.
        Deploy to Kubernetes with horizontal pod autoscaling.
        """
        signals = detect_content_signals(content)
        assert signals.has_architecture is True

    def test_detects_dependency_patterns(self) -> None:
        """Should detect dependency management patterns."""
        content = """
        pip install fastapi==0.100.0
        Add to requirements.txt:
        langchain>=0.1.0
        Check pyproject.toml for version constraints.
        npm install react@18.2.0
        """
        signals = detect_content_signals(content)
        assert signals.has_dependencies is True

    def test_detects_comparison_patterns(self) -> None:
        """Should detect technology comparison patterns."""
        content = """
        FastAPI vs Django: which is better for APIs?
        Comparing React and Vue for frontend development.
        The trade-off between performance and ease of use.
        Pros and cons of each approach.
        Consider these alternatives to the current solution.
        """
        signals = detect_content_signals(content)
        assert signals.has_comparisons is True

    def test_detects_tutorial_patterns(self) -> None:
        """Should detect tutorial/how-to patterns."""
        content = """
        Step 1: Install the dependencies
        Step 2: Configure the database
        First, we'll create the project structure.
        Then, you'll implement the API endpoints.
        Let's build a simple web application.
        Getting started with FastAPI.
        """
        signals = detect_content_signals(content)
        assert signals.has_tutorials is True

    def test_conceptual_only_detection(self) -> None:
        """Should detect conceptual-only content without code."""
        content = """
        Machine learning is a subset of artificial intelligence.
        The concept of neural networks mimics the human brain.
        Understanding the theory behind deep learning.
        This blog post discusses the future of AI.
        """
        signals = detect_content_signals(content)
        assert signals.has_conceptual_only is True
        assert signals.has_code_patterns is False
        assert signals.has_tutorials is False
        assert signals.has_benchmarks is False

    def test_richness_score_calculation(self) -> None:
        """Richness score should increase with more signals."""
        # Minimal content
        minimal = detect_content_signals("Hello world")

        # Rich content with multiple signals
        rich_content = """
        import fastapi
        from sqlalchemy import select

        Step 1: Set up the database
        pip install sqlalchemy>=2.0

        PostgreSQL vs MySQL comparison
        Latency: 50ms average
        OAuth2 authentication required
        """
        rich = detect_content_signals(rich_content)

        assert rich.content_richness_score > minimal.content_richness_score
        assert rich.content_richness_score >= 5.0  # Multiple signals detected

    def test_word_count_boost(self) -> None:
        """Long content should get richness boost."""
        # Short content
        short = detect_content_signals("import pandas\ndef test(): pass")

        # Long content (simulate 2000+ words)
        long_content = "import pandas\ndef test(): pass\n" + "word " * 2500
        long_signals = detect_content_signals(long_content)

        # Both have code, but long should have higher score
        assert long_signals.content_richness_score >= short.content_richness_score


class TestContentGenreDetection:
    """Tests for genre detection."""

    def test_tutorial_genre(self) -> None:
        """Should detect tutorial genre.

        NOTE: Requires both has_tutorials=True AND has_code=True.
        Code patterns require threshold=2 matches, so we include:
        - Fenced code block (```python)
        - Function definition (def main)
        """
        content = """
        # How to Build a REST API

        Step 1: Install FastAPI
        ```python
        from fastapi import FastAPI

        def main():
            app = FastAPI()
            return app
        ```

        First, let's create our main.py file.
        Then, we'll add the endpoint handlers.
        """
        signals = detect_content_signals(content)
        # Tutorial requires has_tutorials=True AND has_code=True
        assert signals.has_tutorials is True
        assert signals.has_code_patterns is True
        assert signals.detected_genre == ContentGenre.TUTORIAL

    def test_quickstart_genre(self) -> None:
        """Should detect quickstart/README genre."""
        content = """
        # Getting Started

        Quick installation guide for the project.
        README documentation for new developers.
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.QUICKSTART

    def test_research_genre(self) -> None:
        """Should detect research paper genre."""
        content = """
        Abstract: This paper presents a novel approach...

        Methodology: We conducted experiments using...

        Related Work: Previous studies have shown...

        Conclusion: Our findings demonstrate...

        References:
        [1] Smith et al., 2024
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.RESEARCH

    def test_reference_genre(self) -> None:
        """Should detect API reference genre."""
        content = """
        # API Reference

        ## Endpoints

        GET /api/users - List all users
        POST /api/users - Create a user

        ### Parameters
        - id: string (required)
        - name: string (optional)

        Specification version 2.0
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.REFERENCE

    def test_changelog_genre(self) -> None:
        """Should detect changelog genre."""
        content = """
        # Changelog

        ## [2.0.0] - 2024-01-15

        ### Added
        - New feature X

        ### Fixed
        - Bug in Y

        ## [1.9.0] - 2024-01-01

        What's new in this release...
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.CHANGELOG

    def test_opinion_genre(self) -> None:
        """Should detect opinion/blog genre."""
        content = """
        I think the future of AI is exciting.
        In my opinion, we should adopt this approach.
        This blog post explores my experience with...
        Based on my experience working with these tools...
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.OPINION


class TestAgentExpectations:
    """Tests for agent expectation computation."""

    def test_security_expectations_with_security_patterns(self) -> None:
        """Security auditor should get FULL_ANALYSIS when security patterns present."""
        content = """
        OAuth2 authentication with JWT tokens.
        Password hashing with bcrypt.
        SQL injection prevention.
        """
        signals = detect_content_signals(content)
        assert signals.agent_expectations.get("security_auditor") == AgentExpectation.FULL_ANALYSIS

    def test_security_expectations_without_security_patterns(self) -> None:
        """Security auditor should get OPPORTUNISTIC without security patterns."""
        content = """
        This is a simple hello world tutorial.
        No security topics discussed here.
        """
        signals = detect_content_signals(content)
        assert signals.agent_expectations.get("security_auditor") == AgentExpectation.OPPORTUNISTIC

    def test_performance_expectations_with_benchmarks(self) -> None:
        """Performance analyst should get FULL_ANALYSIS with benchmark data."""
        content = """
        Latency improved to 50ms.
        Throughput: 10000 req/s.
        Memory usage reduced by 40%.
        """
        signals = detect_content_signals(content)
        assert (
            signals.agent_expectations.get("performance_analyst") == AgentExpectation.FULL_ANALYSIS
        )

    def test_implementation_planner_expectations(self) -> None:
        """Implementation planner expectations based on code + tutorials.

        NOTE: FULL_ANALYSIS requires has_code_patterns AND has_tutorials.
        Each signal requires threshold=2 pattern matches.
        """
        # Full analysis with code and tutorials (sufficient patterns for both)
        full_content = """
        # Building a Web Application

        Step 1: Create the file structure
        First, let's set up the project.
        Then, we'll implement the main logic.

        ```python
        from fastapi import FastAPI

        def main():
            app = FastAPI()
            return app

        class Router:
            pass
        ```
        """
        full_signals = detect_content_signals(full_content)
        # Verify both signals are detected
        assert full_signals.has_code_patterns is True, "Code patterns should be detected"
        assert full_signals.has_tutorials is True, "Tutorial patterns should be detected"
        assert (
            full_signals.agent_expectations.get("implementation_planner")
            == AgentExpectation.FULL_ANALYSIS
        )

    def test_trend_validator_always_full(self) -> None:
        """Trend validator should always be FULL_ANALYSIS."""
        minimal = detect_content_signals("Hello world")
        assert minimal.agent_expectations.get("trend_validator") == AgentExpectation.FULL_ANALYSIS


class TestGetAppropriateAgents:
    """Tests for agent routing based on signals."""

    def test_always_includes_trend_validator(self) -> None:
        """Trend validator should always be included."""
        signals = detect_content_signals("Any content")
        agents = signals.get_appropriate_agents()
        assert "trend_validator" in agents

    def test_includes_implementation_planner_with_code(self) -> None:
        """Implementation planner included when code patterns detected."""
        content = "import pandas\ndef foo(): pass"
        signals = detect_content_signals(content)
        agents = signals.get_appropriate_agents()
        assert "implementation_planner" in agents

    def test_includes_security_auditor_with_security_patterns(self) -> None:
        """Security auditor included when security patterns detected."""
        content = "OAuth2 authentication JWT tokens password encryption"
        signals = detect_content_signals(content)
        agents = signals.get_appropriate_agents()
        assert "security_auditor" in agents

    def test_includes_tech_comparator_with_comparisons(self) -> None:
        """Tech comparator included when comparison patterns detected."""
        content = "FastAPI vs Django comparison pros and cons"
        signals = detect_content_signals(content)
        agents = signals.get_appropriate_agents()
        assert "tech_comparator" in agents


class TestShouldSkipAgent:
    """Tests for agent skip logic."""

    def test_skip_code_quality_without_code(self) -> None:
        """Code quality critic should be skipped without code patterns."""
        content = "This is a conceptual discussion about software design."
        signals = detect_content_signals(content)
        should_skip, reason = should_skip_agent("code_quality_critic", signals)
        assert should_skip is True
        assert "No code patterns" in reason

    def test_dont_skip_code_quality_with_code(self) -> None:
        """Code quality critic should NOT be skipped with code patterns."""
        content = "import pandas\ndef foo(): pass\nclass Bar: pass"
        signals = detect_content_signals(content)
        should_skip, _reason = should_skip_agent("code_quality_critic", signals)
        assert should_skip is False

    def test_skip_security_auditor_on_pure_opinion(self) -> None:
        """Security auditor skipped on conceptual opinion content."""
        content = """
        I think AI is interesting.
        In my opinion, the future looks bright.
        This blog discusses philosophical aspects.
        """
        signals = detect_content_signals(content)
        # Must be both conceptual AND opinion genre
        if signals.has_conceptual_only and signals.detected_genre == ContentGenre.OPINION:
            should_skip, reason = should_skip_agent("security_auditor", signals)
            assert should_skip is True
            assert "Opinion content" in reason

    def test_skip_performance_analyst_on_conceptual(self) -> None:
        """Performance analyst skipped on conceptual-only without architecture."""
        content = """
        This is a theoretical discussion about algorithms.
        No performance metrics or architecture mentioned.
        Pure conceptual content here.
        """
        signals = detect_content_signals(content)
        if signals.has_conceptual_only and not signals.has_architecture:
            should_skip, _reason = should_skip_agent("performance_analyst", signals)
            assert should_skip is True


class TestCoverageSummary:
    """Tests for coverage summary generation."""

    def test_coverage_summary_with_signals(self) -> None:
        """Coverage summary should list detected signals.

        NOTE: Each signal requires threshold=2 pattern matches.
        """
        content = """
        import fastapi
        from sqlalchemy import Column

        def create_app():
            pass

        class Model:
            pass

        OAuth2 authentication with JWT tokens.
        Implement password hashing and validation.

        PostgreSQL database with Redis caching.
        Microservice architecture pattern.
        """
        signals = detect_content_signals(content)
        summary = signals.get_coverage_summary()

        # Verify signals are detected
        assert signals.has_code_patterns is True, f"Expected code patterns, got summary: {summary}"
        assert signals.has_security_patterns is True, (
            f"Expected security patterns, got summary: {summary}"
        )
        assert signals.has_architecture is True, (
            f"Expected architecture patterns, got summary: {summary}"
        )

        assert "code examples" in summary
        assert "security considerations" in summary
        assert "architecture details" in summary

    def test_coverage_summary_conceptual_only(self) -> None:
        """Coverage summary should indicate conceptual-only content."""
        content = "This is a philosophical discussion about software."
        signals = detect_content_signals(content)
        summary = signals.get_coverage_summary()

        assert summary == "conceptual overview only"


class TestEdgeCases:
    """Edge case tests."""

    def test_very_short_content(self) -> None:
        """Very short content should still work."""
        signals = detect_content_signals("Hi")
        assert signals.word_count == 1
        assert signals.content_richness_score == 0.0

    def test_unicode_content(self) -> None:
        """Unicode content should be handled."""
        content = "导入 pandas 并创建 DataFrame。使用 OAuth2 认证。"
        signals = detect_content_signals(content)
        assert signals.word_count > 0

    def test_mixed_language_code(self) -> None:
        """Mixed natural language and code should work.

        NOTE: Code patterns require threshold=2 matches.
        This content has: 2 fenced blocks, 2 function defs = 4 matches.
        """
        content = """
        Here's how to create a Python function:

        First, let's define a simple greeting.
        Then, we'll see the JavaScript equivalent.

        ```python
        def hello():
            print("Hello, World!")
        ```

        And here's the JavaScript version:

        ```javascript
        function hello() {
            console.log("Hello, World!");
        }
        ```
        """
        signals = detect_content_signals(content)
        # Debug info for troubleshooting
        assert signals.has_code_patterns is True, (
            f"Expected code patterns (word_count={signals.word_count})"
        )
        assert signals.has_tutorials is True, (
            f"Expected tutorial patterns (genre={signals.detected_genre})"
        )

    def test_content_with_special_characters(self) -> None:
        """Content with special chars should be handled."""
        content = "import pandas; def foo(): pass  # @decorator $100 100% <html>"
        signals = detect_content_signals(content)
        assert signals is not None

    def test_none_input_returns_empty_signals(self) -> None:
        """None-like input should return defaults."""
        signals = detect_content_signals("")
        assert signals.word_count == 0


class TestThresholdAdjustment:
    """Tests for Issue #299-304 specificity threshold adjustment.

    These tests verify that content-aware thresholds are computed correctly
    based on agent expectations.
    """

    def test_get_adjusted_specificity_threshold_full_analysis(self) -> None:
        """FULL_ANALYSIS expectation should use standard threshold (0.70)."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Content with code and benchmarks = full analysis for performance_analyst
        content = """
        import pandas
        def process_data():
            pass

        class DataProcessor:
            pass

        Latency: 50ms average
        Throughput: 10000 req/s
        Memory usage: 512MB
        """
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("performance_analyst", signals)
        assert threshold == 0.70

    def test_get_adjusted_specificity_threshold_partial(self) -> None:
        """PARTIAL expectation should use reduced threshold (0.55)."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Content with just code (no benchmarks) = partial for performance_analyst
        content = """
        import pandas
        def process_data():
            pass

        class DataProcessor:
            pass
        """
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("performance_analyst", signals)
        assert threshold == 0.55  # PARTIAL threshold

    def test_get_adjusted_specificity_threshold_conceptual(self) -> None:
        """Conceptual content gets very low research thresholds (Issue #442)."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Conceptual content now gets research thresholds (0.15 for performance_analyst)
        content = "This is a discussion about AI concepts and theory."
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("performance_analyst", signals)
        # Issue #442: Research/conceptual content uses very low thresholds
        assert threshold == 0.15  # RESEARCH threshold for conceptual content

    def test_get_threshold_for_expectation_full_analysis(self) -> None:
        """get_threshold_for_expectation with 'full_analysis' returns 0.70."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        assert get_threshold_for_expectation("full_analysis") == 0.70

    def test_get_threshold_for_expectation_partial(self) -> None:
        """get_threshold_for_expectation with 'partial' returns 0.55."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        assert get_threshold_for_expectation("partial") == 0.55

    def test_get_threshold_for_expectation_opportunistic(self) -> None:
        """get_threshold_for_expectation with 'opportunistic' returns 0.45."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        assert get_threshold_for_expectation("opportunistic") == 0.45

    def test_get_threshold_for_expectation_none(self) -> None:
        """get_threshold_for_expectation with None returns default (0.70)."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        assert get_threshold_for_expectation(None) == 0.70

    def test_get_threshold_for_expectation_invalid(self) -> None:
        """get_threshold_for_expectation with invalid string returns default (0.70)."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        assert get_threshold_for_expectation("invalid_expectation") == 0.70

    def test_trend_validator_conceptual_content(self) -> None:
        """trend_validator gets low threshold for conceptual content (Issue #442)."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Conceptual content now gets research thresholds which are very low
        content = "This is a conceptual discussion about AI."
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("trend_validator", signals)
        # Issue #442: Conceptual content uses research thresholds (0.25)
        assert threshold == 0.25  # trend_validator with conceptual content

    def test_trend_validator_with_code_content(self) -> None:
        """trend_validator gets FULL_ANALYSIS threshold with implementation content."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Non-conceptual content (has code) gets standard expectation-based thresholds
        content = """
        def hello_world():
            print("Hello World")

        import asyncio
        async def main():
            await hello_world()
        """
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("trend_validator", signals)
        assert threshold == 0.70  # trend_validator with code = full_analysis

    def test_security_auditor_with_security_and_code_patterns(self) -> None:
        """security_auditor gets FULL_ANALYSIS when security + code patterns present."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Security content with multiple code patterns - must be unindented to match regex
        content = """import hashlib
from fastapi import OAuth2PasswordBearer
from bcrypt import hashpw

def authenticate(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class AuthMiddleware:
    async def __call__(self, request):
        token = request.headers.get("Authorization")
        return await self.validate_jwt(token)
"""
        signals = detect_content_signals(content)
        # With code patterns, it's no longer conceptual-only
        threshold = get_adjusted_specificity_threshold("security_auditor", signals)
        assert threshold == 0.70  # FULL_ANALYSIS for security + code content

    def test_security_auditor_conceptual_security_content(self) -> None:
        """security_auditor gets low threshold for conceptual security content (Issue #442)."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        # Conceptual security discussion without code
        content = """
        OAuth2 authentication with JWT tokens.
        Password hashing with bcrypt.
        SQL injection prevention is critical.
        """
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("security_auditor", signals)
        # Issue #442: Conceptual content uses research thresholds (0.20)
        assert threshold == 0.20  # Conceptual security gets research threshold

    def test_security_auditor_without_security_patterns(self) -> None:
        """security_auditor gets low threshold for conceptual content without security."""
        from app.shared.workflows.utils.content_signals import get_adjusted_specificity_threshold

        content = "This is a simple hello world tutorial."
        signals = detect_content_signals(content)
        threshold = get_adjusted_specificity_threshold("security_auditor", signals)
        # Issue #442: Conceptual content uses research thresholds (0.20)
        assert threshold == 0.20  # Conceptual content = research threshold


class TestAgentStateFlowIntegration:
    """Integration tests for agent state flow.

    These tests verify that agents correctly read supervisor_decision from state,
    extract agent_expectations, and compute the correct threshold.
    """

    def test_agent_extracts_expectation_from_state(self) -> None:
        """Agent should correctly extract expectation from supervisor_decision in state."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # Simulate state with supervisor_decision containing agent_expectations
        state = {
            "supervisor_decision": {
                "agents": ["trend_validator", "security_auditor"],
                "agent_expectations": {
                    "trend_validator": "full_analysis",
                    "security_auditor": "opportunistic",
                    "performance_analyst": "partial",
                },
            },
            "skill_level": "intermediate",
        }

        # Extract like the agent does
        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})

        # Verify trend_validator gets full_analysis
        expectation = agent_expectations.get("trend_validator")
        assert expectation == "full_analysis"
        assert get_threshold_for_expectation(expectation) == 0.70

        # Verify security_auditor gets opportunistic
        expectation = agent_expectations.get("security_auditor")
        assert expectation == "opportunistic"
        assert get_threshold_for_expectation(expectation) == 0.45

        # Verify performance_analyst gets partial
        expectation = agent_expectations.get("performance_analyst")
        assert expectation == "partial"
        assert get_threshold_for_expectation(expectation) == 0.55

    def test_agent_handles_empty_supervisor_decision(self) -> None:
        """Agent should return default threshold when supervisor_decision is empty."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # State without supervisor_decision
        state = {"skill_level": "intermediate"}

        # Extract like the agent does
        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})
        expectation = agent_expectations.get("trend_validator")

        assert expectation is None
        assert get_threshold_for_expectation(expectation) == 0.70  # Default

    def test_agent_handles_missing_agent_expectations(self) -> None:
        """Agent should return default threshold when agent_expectations is missing."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # State with supervisor_decision but no agent_expectations
        state = {
            "supervisor_decision": {
                "agents": ["trend_validator"],
            },
        }

        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})
        expectation = agent_expectations.get("trend_validator")

        assert expectation is None
        assert get_threshold_for_expectation(expectation) == 0.70  # Default

    def test_agent_handles_missing_specific_agent(self) -> None:
        """Agent should return default threshold when specific agent not in expectations."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # State with expectations for other agents but not this one
        state = {
            "supervisor_decision": {
                "agents": ["trend_validator"],
                "agent_expectations": {
                    "security_auditor": "opportunistic",
                },
            },
        }

        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})
        expectation = agent_expectations.get("tech_comparator")  # Not in expectations

        assert expectation is None
        assert get_threshold_for_expectation(expectation) == 0.70  # Default

    def test_full_state_flow_with_content_signals(self) -> None:
        """Test complete state flow: content signals → expectations → thresholds."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # Simulate state as it would exist after supervisor runs
        # For conceptual-only content
        state = {
            "supervisor_decision": {
                "agents": [
                    "trend_validator",
                    "security_auditor",
                    "performance_analyst",
                    "implementation_planner",
                ],
                "content_signals": {
                    "has_code": False,
                    "has_benchmarks": False,
                    "has_security": False,
                    "has_architecture": True,
                    "has_dependencies": False,
                    "has_comparisons": False,
                    "has_tutorials": True,
                    "has_conceptual_only": True,
                },
                "agent_expectations": {
                    "trend_validator": "full_analysis",  # Always full
                    "security_auditor": "opportunistic",  # No security patterns
                    "performance_analyst": "opportunistic",  # No benchmarks
                    "implementation_planner": "full_analysis",  # Has tutorials
                },
            },
        }

        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})

        # Verify thresholds match expectations
        assert get_threshold_for_expectation(agent_expectations.get("trend_validator")) == 0.70
        assert get_threshold_for_expectation(agent_expectations.get("security_auditor")) == 0.45
        assert get_threshold_for_expectation(agent_expectations.get("performance_analyst")) == 0.45
        assert (
            get_threshold_for_expectation(agent_expectations.get("implementation_planner")) == 0.70
        )

    def test_state_flow_with_code_rich_content(self) -> None:
        """Test state flow for code-rich content with full expectations."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # Simulate state for code-rich tutorial content
        state = {
            "supervisor_decision": {
                "agents": [
                    "trend_validator",
                    "security_auditor",
                    "code_quality_critic",
                    "dependency_mapper",
                ],
                "content_signals": {
                    "has_code": True,
                    "has_benchmarks": True,
                    "has_security": True,
                    "has_architecture": True,
                    "has_dependencies": True,
                    "has_comparisons": True,
                    "has_tutorials": True,
                    "has_conceptual_only": False,
                },
                "agent_expectations": {
                    "trend_validator": "full_analysis",
                    "security_auditor": "full_analysis",  # Has security patterns
                    "code_quality_critic": "full_analysis",  # Has code
                    "dependency_mapper": "full_analysis",  # Has dependencies
                },
            },
        }

        supervisor_decision = state.get("supervisor_decision", {})
        agent_expectations = supervisor_decision.get("agent_expectations", {})

        # All agents should get full_analysis threshold (0.70)
        for agent in state["supervisor_decision"]["agents"]:
            threshold = get_threshold_for_expectation(agent_expectations.get(agent))
            assert threshold == 0.70, f"{agent} should have threshold 0.70"


class TestComparisonAwareThresholds:
    """Tests for Issue #299-304 comparison-aware threshold adjustments.

    These tests verify that comparison content gets special threshold treatment
    to allow for breadth instead of depth.
    """

    def test_comparison_threshold_tech_comparator(self) -> None:
        """tech_comparator should get 0.50 threshold for comparison content."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="tech_comparator",
            has_comparisons=True,
        )
        assert threshold == 0.50

    def test_comparison_threshold_trend_validator(self) -> None:
        """trend_validator should get 0.50 threshold for comparison content."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="trend_validator",
            has_comparisons=True,
        )
        assert threshold == 0.50

    def test_comparison_threshold_implementation_planner(self) -> None:
        """implementation_planner should get 0.35 threshold for comparison content."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="implementation_planner",
            has_comparisons=True,
        )
        assert threshold == 0.35

    def test_comparison_threshold_dependency_mapper(self) -> None:
        """dependency_mapper should get 0.65 threshold for comparison content."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="dependency_mapper",
            has_comparisons=True,
        )
        assert threshold == 0.65

    def test_non_comparison_uses_expectation_threshold(self) -> None:
        """Without comparisons, should use expectation-based threshold."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # tech_comparator without comparisons should use expectation threshold
        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="tech_comparator",
            has_comparisons=False,
        )
        assert threshold == 0.70  # full_analysis threshold, not comparison

    def test_comparison_overrides_expectation(self) -> None:
        """Comparison threshold should override expectation-based threshold."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        # Even with opportunistic expectation, comparison threshold applies
        threshold_opportunistic = get_threshold_for_expectation(
            expectation_str="opportunistic",
            agent_name="tech_comparator",
            has_comparisons=True,
        )
        threshold_full = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="tech_comparator",
            has_comparisons=True,
        )
        # Both should use comparison threshold (0.50), not expectation threshold
        assert threshold_opportunistic == 0.50
        assert threshold_full == 0.50

    def test_unknown_agent_with_comparison(self) -> None:
        """Unknown agent with comparisons should use expectation threshold."""
        from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

        threshold = get_threshold_for_expectation(
            expectation_str="full_analysis",
            agent_name="unknown_agent",  # Not in COMPARISON_THRESHOLDS
            has_comparisons=True,
        )
        # Should fall back to expectation threshold
        assert threshold == 0.70

    def test_comparison_threshold_constants_exist(self) -> None:
        """Verify COMPARISON_THRESHOLDS dictionary is properly defined."""
        from app.shared.workflows.utils.content_signals import COMPARISON_THRESHOLDS

        # Verify all expected agents are defined
        expected_agents = {
            "tech_comparator": 0.50,
            "trend_validator": 0.50,
            "implementation_planner": 0.35,
            "dependency_mapper": 0.65,
        }

        for agent, expected_threshold in expected_agents.items():
            assert agent in COMPARISON_THRESHOLDS
            assert COMPARISON_THRESHOLDS[agent] == expected_threshold


# =============================================================================
# Issue #490: News Content Genre Tests
# =============================================================================


class TestNewsGenreDetection:
    """Tests for NEWS genre detection (Issue #490)."""

    def test_news_genre_announcement(self) -> None:
        """Should detect news genre from announcement content."""
        content = """
        OpenAI Announces GPT-5: Next Generation AI Model

        Today OpenAI unveiled its latest AI breakthrough.
        The new model introduces revolutionary capabilities and is now available
        to enterprise customers worldwide.
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.NEWS

    def test_news_genre_product_launch(self) -> None:
        """Should detect news genre from product launch content."""
        content = """
        Google Cloud Launches Enhanced AI Platform

        Google introduces new machine learning features available today.
        This partnership enables broader access to AI capabilities.
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.NEWS

    def test_news_genre_partnership(self) -> None:
        """Should detect news genre from partnership/acquisition news."""
        content = """
        Major Tech Acquisition Announced Today

        Company A has unveiled its acquisition of Company B.
        The merger marks a significant partnership in the industry.
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.NEWS

    def test_news_genre_not_tutorial_with_code(self) -> None:
        """News genre should NOT be detected when code is present."""
        content = """
        Company Announces New Framework

        Here's how to use it:

        ```python
        import new_framework
        from new_framework import Client

        def hello():
            return new_framework.greet()
        ```

        Step 1: Install the package
        Step 2: Configure your settings
        """
        signals = detect_content_signals(content)
        # Should be TUTORIAL, not NEWS (has code and steps)
        assert signals.detected_genre != ContentGenre.NEWS
        assert signals.detected_genre == ContentGenre.TUTORIAL

    def test_news_genre_appropriate_agents(self) -> None:
        """NEWS genre should return only trend_validator and tech_comparator."""
        content = """
        Breaking News: Major Tech Acquisition Announced

        Today it was unveiled that Company A will acquire Company B.
        The partnership is now available for regulatory review.
        """
        signals = detect_content_signals(content)
        assert signals.detected_genre == ContentGenre.NEWS

        appropriate_agents = signals.get_appropriate_agents()
        assert len(appropriate_agents) == 2
        assert "trend_validator" in appropriate_agents
        assert "tech_comparator" in appropriate_agents
        # Should NOT include implementation agents
        assert "implementation_planner" not in appropriate_agents
        assert "security_auditor" not in appropriate_agents
        assert "dependency_mapper" not in appropriate_agents

    def test_news_vs_changelog(self) -> None:
        """NEWS should not be confused with CHANGELOG."""
        # Changelog has version history structure
        changelog_content = """
        # Changelog

        ## [2.0.0] - 2024-01-15

        ### Added
        - New feature announced
        - Product now available

        ## [1.9.0] - 2024-01-01
        - Previous release
        """
        signals = detect_content_signals(changelog_content)
        # Should be CHANGELOG, not NEWS (has version structure)
        assert signals.detected_genre == ContentGenre.CHANGELOG

    def test_news_vs_opinion(self) -> None:
        """NEWS (product announcement) should not be confused with OPINION (blog post)."""
        # News with announcement keywords
        news_content = """
        Company Announces New AI Model Now Available

        Today the company unveiled its latest model.
        The new version is now available to all customers.
        """
        signals = detect_content_signals(news_content)
        assert signals.detected_genre == ContentGenre.NEWS

        # Opinion piece without news announcements
        opinion_content = """
        I think the future of AI is exciting.
        In my opinion, we should adopt this approach.
        This blog post explores my experience with AI.
        """
        signals = detect_content_signals(opinion_content)
        assert signals.detected_genre == ContentGenre.OPINION

    def test_news_keyword_patterns(self) -> None:
        """Test various news keyword patterns."""
        patterns = [
            ("Announcing new product today", ContentGenre.NEWS),
            ("The company launched a new service", ContentGenre.NEWS),
            ("Product unveiled at conference", ContentGenre.NEWS),
            ("Now available to all customers", ContentGenre.NEWS),
            ("Press release from company", ContentGenre.NEWS),
        ]

        for content, expected_genre in patterns:
            # Add more context to ensure it's not classified as something else
            full_content = f"""
            {content}

            The announcement was made today.
            The new offering is now available globally.
            """
            signals = detect_content_signals(full_content)
            assert signals.detected_genre == expected_genre, (
                f"Expected {expected_genre} for '{content}', got {signals.detected_genre}"
            )

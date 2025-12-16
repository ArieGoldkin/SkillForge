"""Unit tests for LLM evaluation evaluators.

Tests cover all evaluator modules:
- correctness.py: supervisor, agent, and synthesis correctness evaluators
- latency.py: latency and TTFT evaluators
- cost.py: cost and cost-per-correct evaluators

Each test validates:
- Correct return structure: {"key": str, "score": float, "comment": str}
- Score ranges: 0.0 to 1.0
- Edge cases: empty outputs, missing fields, None values
- Specific logic: scoring algorithms, metric calculations
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

@pytest.mark.unit

# =============================================================================
# MOCK CLASSES (avoiding LangSmith imports)
# =============================================================================


@dataclass
class MockRun:
    """Mock LangSmith Run class."""

    outputs: dict[str, Any] | None = None
    inputs: dict[str, Any] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    extra: dict[str, Any] | None = None
    feedback: list[Any] = field(default_factory=list)


@dataclass
class MockExample:
    """Mock LangSmith Example class."""

    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None


@dataclass
class MockFeedback:
    """Mock LangSmith Feedback class."""

    key: str
    score: float


# =============================================================================
# CORRECTNESS EVALUATORS TESTS
# =============================================================================


class TestSupervisorCorrectnessEvaluator:
    """Tests for supervisor_correctness_evaluator."""

    def test_perfect_match(self):
        """Test perfect match returns 1.0 score."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator", "security_auditor"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator", "security_auditor"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] == 1.0
        assert "coverage: 100%" in result["comment"]
        assert "precision: 100%" in result["comment"]

    def test_partial_match_missing_agent(self):
        """Test partial match returns score between 0 and 1."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator", "security_auditor"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert 0.0 < result["score"] < 1.0
        assert "missing:" in result["comment"]

    def test_no_match_wrong_agent(self):
        """Test selecting wrong agent returns low score."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"agents": ["wrong_agent"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] < 0.5

    def test_no_agents_selected(self):
        """Test no agents selected returns 0.0 score."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"agents": []})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] == 0.0
        assert "No agents selected" in result["comment"]

    def test_optional_agents_not_penalized(self):
        """Test optional agents don't penalize precision."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(
            outputs={"agents": ["tech_comparator", "dependency_mapper", "security_auditor"]}
        )
        example = MockExample(
            outputs={
                "expected_agents": ["tech_comparator"],
                "optional_agents": ["dependency_mapper", "security_auditor"],
            }
        )

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] >= 0.85  # High score, no penalty for optional
        assert "auto-activated:" in result["comment"]

    def test_supports_selected_agents_key(self):
        """Test supports both 'agents' and 'selected_agents' keys."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"selected_agents": ["tech_comparator"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] == 1.0

    def test_empty_expected_and_actual(self):
        """Test trivial case where no agents expected or selected."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs={"agents": []})
        example = MockExample(outputs={"expected_agents": []})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] == 1.0
        assert "trivial case" in result["comment"]

    def test_none_outputs(self):
        """Test handles None outputs gracefully."""
        from app.evaluation.evaluators.correctness import supervisor_correctness_evaluator

        run = MockRun(outputs=None)
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_correctness_evaluator(run, example)

        assert result["key"] == "supervisor_correctness"
        assert result["score"] == 0.0


class TestSupervisorCoverageEvaluator:
    """Tests for supervisor_coverage_evaluator."""

    def test_full_coverage_with_extra(self):
        """Test all required agents selected returns 1.0 (extra OK)."""
        from app.evaluation.evaluators.correctness import supervisor_coverage_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator", "security_auditor", "extra_agent"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator", "security_auditor"]})

        result = supervisor_coverage_evaluator(run, example)

        assert result["key"] == "supervisor_coverage"
        assert result["score"] == 1.0
        assert "2/2 required agents covered" in result["comment"]

    def test_partial_coverage(self):
        """Test partial coverage returns proportional score."""
        from app.evaluation.evaluators.correctness import supervisor_coverage_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator", "security_auditor"]})

        result = supervisor_coverage_evaluator(run, example)

        assert result["key"] == "supervisor_coverage"
        assert result["score"] == 0.5
        assert "1/2 required agents covered" in result["comment"]

    def test_no_required_agents(self):
        """Test no required agents returns 1.0."""
        from app.evaluation.evaluators.correctness import supervisor_coverage_evaluator

        run = MockRun(outputs={"agents": ["any_agent"]})
        example = MockExample(outputs={"expected_agents": []})

        result = supervisor_coverage_evaluator(run, example)

        assert result["key"] == "supervisor_coverage"
        assert result["score"] == 1.0


class TestSupervisorPrecisionEvaluator:
    """Tests for supervisor_precision_evaluator."""

    def test_perfect_precision(self):
        """Test all selected agents relevant returns 1.0."""
        from app.evaluation.evaluators.correctness import supervisor_precision_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator", "security_auditor"]})
        example = MockExample(
            outputs={
                "expected_agents": ["tech_comparator"],
                "optional_agents": ["security_auditor"],
            }
        )

        result = supervisor_precision_evaluator(run, example)

        assert result["key"] == "supervisor_precision"
        assert result["score"] == 1.0

    def test_partial_precision(self):
        """Test some irrelevant agents returns proportional score."""
        from app.evaluation.evaluators.correctness import supervisor_precision_evaluator

        run = MockRun(outputs={"agents": ["tech_comparator", "irrelevant_agent"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_precision_evaluator(run, example)

        assert result["key"] == "supervisor_precision"
        assert result["score"] == 0.5
        assert "irrelevant:" in result["comment"]

    def test_no_agents_selected(self):
        """Test no agents selected returns 0.0."""
        from app.evaluation.evaluators.correctness import supervisor_precision_evaluator

        run = MockRun(outputs={"agents": []})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        result = supervisor_precision_evaluator(run, example)

        assert result["key"] == "supervisor_precision"
        assert result["score"] == 0.0


class TestAgentCorrectnessEvaluator:
    """Tests for agent_correctness_evaluator."""

    def test_valid_tech_comparator_output(self):
        """Test valid tech comparator output returns high score."""
        from app.evaluation.evaluators.correctness import agent_correctness_evaluator

        run = MockRun(
            outputs={
                "primary_tech": "FastAPI",
                "alternatives": ["Flask", "Django"],
                "comparison_matrix": [],
                "recommendations": "Use FastAPI for async support",
            }
        )
        example = MockExample(
            inputs={"agent_type": "tech_comparator"},
            outputs={
                "agent_type": "tech_comparator",
                "primary_tech": "FastAPI",
                "expected_alternatives": ["flask", "django"],
            },
        )

        result = agent_correctness_evaluator(run, example)

        assert result["key"] == "agent_correctness"
        assert result["score"] >= 0.5  # Schema valid + some key fields
        assert "schema:" in result["comment"]

    def test_schema_validation_failure(self):
        """Test schema validation failure returns low score."""
        from app.evaluation.evaluators.correctness import agent_correctness_evaluator

        run = MockRun(outputs={"incomplete": "data"})
        example = MockExample(
            inputs={"agent_type": "tech_comparator"},
            outputs={"agent_type": "tech_comparator"},
        )

        result = agent_correctness_evaluator(run, example)

        assert result["key"] == "agent_correctness"
        # Schema failure gives 0.0 schema score, but key_field_score=1.0 when no refs
        # Combined: 0.4*0 + 0.6*1.0 = 0.6
        assert result["score"] <= 0.7

    def test_generic_schema_with_required_fields(self):
        """Test generic schema validation for unknown agent types."""
        from app.evaluation.evaluators.correctness import agent_correctness_evaluator

        run = MockRun(outputs={"field1": "value1", "field2": "value2"})
        example = MockExample(
            inputs={"agent_type": "unknown"},
            outputs={"agent_type": "unknown", "required_fields": ["field1", "field2"]},
        )

        result = agent_correctness_evaluator(run, example)

        assert result["key"] == "agent_correctness"
        assert result["score"] >= 0.7


class TestSynthesisCorrectnessEvaluator:
    """Tests for synthesis_correctness_evaluator."""

    def test_valid_synthesis_output(self):
        """Test valid synthesis output returns high score."""
        from app.evaluation.evaluators.correctness import synthesis_correctness_evaluator

        run = MockRun(
            outputs={
                "executive_summary": "This is a comprehensive analysis of the technology stack",
                "key_findings": [
                    "FastAPI is recommended for async support",
                    "Security risks identified in authentication",
                ],
                "cross_domain_connections": [{"domain1": "tech", "domain2": "security"}],
                "coverage_score": 0.85,
                "conflicts": [],
            }
        )
        example = MockExample(
            outputs={
                "expected_key_findings": ["fastapi", "security"],
                "expected_summary_keywords": ["analysis", "technology"],
                "expected_coverage": 0.85,
                "expected_min_connections": 1,
            }
        )

        result = synthesis_correctness_evaluator(run, example)

        assert result["key"] == "synthesis_correctness"
        assert result["score"] >= 0.7
        assert "schema:" in result["comment"]

    def test_schema_validation_failure(self):
        """Test schema validation failure returns low score."""
        from app.evaluation.evaluators.correctness import synthesis_correctness_evaluator

        run = MockRun(outputs={"incomplete": "data"})
        example = MockExample(outputs={})

        result = synthesis_correctness_evaluator(run, example)

        assert result["key"] == "synthesis_correctness"
        assert result["score"] < 0.5


# =============================================================================
# LATENCY EVALUATORS TESTS
# =============================================================================


class TestLatencyEvaluator:
    """Tests for latency_evaluator."""

    def test_fast_response(self):
        """Test fast response returns high score."""
        from app.evaluation.evaluators.latency import latency_evaluator

        start = datetime.now(UTC)
        end = start + timedelta(milliseconds=500)

        run = MockRun(start_time=start, end_time=end)
        example = MockExample()

        result = latency_evaluator(run, example)

        assert result["key"] == "latency_ms"
        assert result["score"] >= 0.9
        assert "500" in result["comment"]

    def test_slow_response(self):
        """Test slow response returns low score."""
        from app.evaluation.evaluators.latency import latency_evaluator

        start = datetime.now(UTC)
        end = start + timedelta(seconds=8)

        run = MockRun(start_time=start, end_time=end)
        example = MockExample()

        result = latency_evaluator(run, example)

        assert result["key"] == "latency_ms"
        assert result["score"] <= 0.3

    def test_no_timing_data(self):
        """Test no timing data returns 0.0 score."""
        from app.evaluation.evaluators.latency import latency_evaluator

        run = MockRun(start_time=None, end_time=None)
        example = MockExample()

        result = latency_evaluator(run, example)

        assert result["key"] == "latency_ms"
        assert result["score"] == 0.0
        assert "No timing data" in result["comment"]


class TestTTFTEvaluator:
    """Tests for ttft_evaluator."""

    def test_fast_ttft(self):
        """Test fast TTFT returns high score."""
        from app.evaluation.evaluators.latency import ttft_evaluator

        run = MockRun(extra={"ttft_ms": 100})
        example = MockExample()

        result = ttft_evaluator(run, example)

        assert result["key"] == "ttft_ms"
        assert result["score"] >= 0.9

    def test_no_ttft_data(self):
        """Test no TTFT data returns 0.0 score."""
        from app.evaluation.evaluators.latency import ttft_evaluator

        run = MockRun(extra={})
        example = MockExample()

        result = ttft_evaluator(run, example)

        assert result["key"] == "ttft_ms"
        assert result["score"] == 0.0

    def test_none_extra(self):
        """Test None extra field handles gracefully."""
        from app.evaluation.evaluators.latency import ttft_evaluator

        run = MockRun(extra=None)
        example = MockExample()

        result = ttft_evaluator(run, example)

        assert result["key"] == "ttft_ms"
        assert result["score"] == 0.0


# =============================================================================
# COST EVALUATORS TESTS
# =============================================================================


class TestCostEvaluator:
    """Tests for cost_evaluator."""

    def test_valid_cost_calculation(self):
        """Test valid cost calculation returns correct structure."""
        from app.evaluation.evaluators.cost import cost_evaluator

        run = MockRun(
            outputs={"usage": {"input_tokens": 1000, "output_tokens": 500}},
            extra={"model_id": "gpt-4o-mini"},
        )
        example = MockExample()

        result = cost_evaluator(run, example)

        assert result["key"] == "cost_usd"
        assert 0.0 <= result["score"] <= 1.0
        assert "$" in result["comment"]

    def test_no_usage_data(self):
        """Test no usage data returns 0.0 score."""
        from app.evaluation.evaluators.cost import cost_evaluator

        run = MockRun(outputs={}, extra={"model_id": "gpt-4o-mini"})
        example = MockExample()

        result = cost_evaluator(run, example)

        assert result["key"] == "cost_usd"
        assert result["score"] == 0.0


class TestCostPerCorrectEvaluator:
    """Tests for cost_per_correct_evaluator."""

    def test_cost_effectiveness_calculation(self):
        """Test cost-effectiveness calculation."""
        from app.evaluation.evaluators.cost import cost_per_correct_evaluator

        feedback = MockFeedback(key="supervisor_correctness", score=0.8)
        run = MockRun(
            outputs={"usage": {"input_tokens": 1000, "output_tokens": 500}},
            extra={"model_id": "gpt-4o-mini"},
            feedback=[feedback],
        )
        example = MockExample()

        result = cost_per_correct_evaluator(run, example)

        assert result["key"] == "cost_per_correct"
        assert 0.0 <= result["score"] <= 1.0


# =============================================================================
# EDGE CASES AND STRUCTURE VALIDATION
# =============================================================================


class TestEvaluatorStructure:
    """Test all evaluators return correct structure."""

    def test_correctness_evaluators_return_structure(self):
        """Test correctness evaluators return proper dict structure."""
        from app.evaluation.evaluators.correctness import (
            supervisor_correctness_evaluator,
            supervisor_coverage_evaluator,
            supervisor_precision_evaluator,
        )

        run = MockRun(outputs={"agents": ["tech_comparator"]})
        example = MockExample(outputs={"expected_agents": ["tech_comparator"]})

        evaluators = [
            supervisor_correctness_evaluator,
            supervisor_coverage_evaluator,
            supervisor_precision_evaluator,
        ]

        for evaluator in evaluators:
            result = evaluator(run, example)
            assert isinstance(result, dict)
            assert "key" in result
            assert "score" in result
            assert "comment" in result
            assert isinstance(result["key"], str)
            assert isinstance(result["score"], (int, float))
            assert isinstance(result["comment"], str)
            assert 0.0 <= result["score"] <= 1.0

    def test_latency_evaluator_returns_structure(self):
        """Test latency evaluator returns proper dict structure."""
        from app.evaluation.evaluators.latency import latency_evaluator

        run = MockRun(
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(seconds=1),
        )
        example = MockExample()

        result = latency_evaluator(run, example)

        assert isinstance(result, dict)
        assert "key" in result
        assert "score" in result
        assert "comment" in result
        assert 0.0 <= result["score"] <= 1.0

    def test_cost_evaluator_returns_structure(self):
        """Test cost evaluator returns proper dict structure."""
        from app.evaluation.evaluators.cost import cost_evaluator

        run = MockRun(
            outputs={"usage": {"input_tokens": 100, "output_tokens": 50}},
            extra={"model_id": "gpt-4o-mini"},
        )
        example = MockExample()

        result = cost_evaluator(run, example)

        assert isinstance(result, dict)
        assert "key" in result
        assert "score" in result
        assert "comment" in result
        assert 0.0 <= result["score"] <= 1.0

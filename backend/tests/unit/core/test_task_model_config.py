"""Unit tests for task model configuration."""

import pytest

from app.core.task_model_config import (
    SELECTION_RATIONALE,
    SUPERVISOR_BENCHMARK_RESULTS,
    TASK_MODELS,
    TaskModelConfig,
    get_model_for_task,
    get_task_config,
    is_validated,
)

@pytest.mark.unit


class TestTaskModelConfig:
    """Tests for TaskModelConfig dataclass."""

    def test_config_creation(self):
        """Test creating a TaskModelConfig."""
        config = TaskModelConfig(
            primary="gpt-4o",
            fallback="gpt-4o-mini",
            status="validated",
            correctness=0.95,
            cost_per_call=0.01,
            latency_p50_ms=2000,
        )
        assert config.primary == "gpt-4o"
        assert config.fallback == "gpt-4o-mini"
        assert config.status == "validated"
        assert config.correctness == 0.95

    def test_config_defaults(self):
        """Test TaskModelConfig default values."""
        config = TaskModelConfig(
            primary="test",
            fallback="test-fallback",
            status="hypothesis",
        )
        assert config.correctness is None
        assert config.cost_per_call is None
        assert config.latency_p50_ms is None

    def test_config_frozen(self):
        """Test that TaskModelConfig is immutable."""
        config = TaskModelConfig(primary="a", fallback="b", status="validated")
        with pytest.raises(AttributeError):
            config.primary = "changed"  # type: ignore[misc]


class TestGetModelForTask:
    """Tests for get_model_for_task function."""

    def test_get_primary_model(self):
        """Test getting primary model for a task."""
        model = get_model_for_task("supervisor")
        assert model == "gemini-2.5-flash"

    def test_get_fallback_model(self):
        """Test getting fallback model for a task."""
        model = get_model_for_task("supervisor", use_fallback=True)
        assert model == "gemini-2.0-flash"  # Updated Dec 2025

    def test_unknown_task_returns_none(self):
        """Test that unknown task returns None."""
        model = get_model_for_task("nonexistent_task")
        assert model is None

    def test_all_tasks_have_models(self):
        """Test all configured tasks return models."""
        for task in TASK_MODELS:
            assert get_model_for_task(task) is not None


class TestGetTaskConfig:
    """Tests for get_task_config function."""

    def test_get_valid_config(self):
        """Test getting config for valid task."""
        config = get_task_config("supervisor")
        assert config is not None
        assert isinstance(config, TaskModelConfig)
        assert config.status == "validated"

    def test_get_invalid_config(self):
        """Test getting config for invalid task."""
        config = get_task_config("invalid_task")
        assert config is None


class TestIsValidated:
    """Tests for is_validated function."""

    def test_validated_task(self):
        """Test that supervisor is validated."""
        assert is_validated("supervisor") is True

    def test_hypothesis_task(self):
        """Test that agent_analysis is hypothesis."""
        assert is_validated("agent_analysis") is False

    def test_unknown_task(self):
        """Test unknown task returns False."""
        assert is_validated("unknown") is False


class TestTaskModelsDict:
    """Tests for TASK_MODELS dictionary."""

    def test_supervisor_exists(self):
        """Test supervisor task is configured."""
        assert "supervisor" in TASK_MODELS

    def test_all_required_tasks(self):
        """Test all expected tasks are present."""
        expected = {"supervisor", "agent_analysis", "synthesis", "tutoring", "code_analysis"}
        assert set(TASK_MODELS.keys()) == expected

    def test_supervisor_metrics(self):
        """Test supervisor has validation metrics."""
        supervisor = TASK_MODELS["supervisor"]
        assert supervisor.correctness is not None
        assert supervisor.cost_per_call is not None
        assert supervisor.latency_p50_ms is not None


class TestBenchmarkResults:
    """Tests for benchmark results archive."""

    def test_benchmark_has_timestamp(self):
        """Test benchmark results have timestamp."""
        assert "timestamp" in SUPERVISOR_BENCHMARK_RESULTS

    def test_benchmark_has_models(self):
        """Test benchmark has model results."""
        assert "models" in SUPERVISOR_BENCHMARK_RESULTS
        assert len(SUPERVISOR_BENCHMARK_RESULTS["models"]) > 0


class TestSelectionRationale:
    """Tests for selection rationale documentation."""

    def test_supervisor_rationale_exists(self):
        """Test supervisor has rationale."""
        assert "supervisor" in SELECTION_RATIONALE
        assert "VALIDATED" in SELECTION_RATIONALE["supervisor"]

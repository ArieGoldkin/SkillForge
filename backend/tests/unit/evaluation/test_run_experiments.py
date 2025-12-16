"""Tests for run_experiments module."""

from __future__ import annotations
import pytest

from unittest.mock import MagicMock, patch

from app.evaluation.run_experiments import (

@pytest.mark.unit
    DEFAULT_MODELS,
    TASK_DATASETS,
    run_preflight_checks,
)


class TestDefaultModels:
    """Tests for DEFAULT_MODELS configuration."""

    def test_default_models_has_all_task_types(self):
        """DEFAULT_MODELS contains all required task types."""
        assert "supervisor" in DEFAULT_MODELS
        assert "agent" in DEFAULT_MODELS
        assert "synthesis" in DEFAULT_MODELS

    def test_default_models_supervisor_has_multiple_providers(self):
        """Supervisor models include multiple providers."""
        supervisor_models = DEFAULT_MODELS["supervisor"]
        assert len(supervisor_models) >= 3

        # Check for different providers
        model_names = " ".join(supervisor_models)
        assert "gpt" in model_names.lower() or "mini" in model_names.lower()
        assert "claude" in model_names.lower() or "haiku" in model_names.lower()
        assert "gemini" in model_names.lower()

    def test_default_models_are_lists(self):
        """All model entries are non-empty lists."""
        for task_type, models in DEFAULT_MODELS.items():
            assert isinstance(models, list), f"{task_type} should be a list"
            assert len(models) > 0, f"{task_type} should have at least one model"


class TestTaskDatasets:
    """Tests for TASK_DATASETS configuration."""

    def test_task_datasets_has_all_task_types(self):
        """TASK_DATASETS contains all required task types."""
        assert "supervisor" in TASK_DATASETS
        assert "agent" in TASK_DATASETS
        assert "synthesis" in TASK_DATASETS

    def test_task_datasets_are_strings(self):
        """All dataset names are non-empty strings."""
        for task_type, dataset_name in TASK_DATASETS.items():
            assert isinstance(dataset_name, str), f"{task_type} dataset should be a string"
            assert len(dataset_name) > 0, f"{task_type} dataset should not be empty"


class TestRunPreflightChecks:
    """Tests for run_preflight_checks function."""

    @patch("app.evaluation.run_experiments.LLMBenchmark")
    @patch("app.evaluation.run_experiments.load_dataset")
    def test_preflight_all_pass(self, mock_load_dataset, mock_benchmark_class):
        """Preflight checks pass when all API keys and datasets are valid."""
        # Setup mocks
        mock_benchmark = MagicMock()
        mock_benchmark.validate_api_key.return_value = (True, None)
        mock_benchmark.get_available_models.return_value = (["model1", "model2"], {})
        mock_benchmark_class.return_value = mock_benchmark

        mock_load_dataset.return_value = [{"id": 1}, {"id": 2}]

        # Run preflight
        passed, results = run_preflight_checks(verbose=False)

        assert passed is True
        assert results["overall_status"] == "passed"

    @patch("app.evaluation.run_experiments.LLMBenchmark")
    @patch("app.evaluation.run_experiments.load_dataset")
    def test_preflight_missing_api_key(self, mock_load_dataset, mock_benchmark_class):
        """Preflight checks fail when API key is missing."""
        # Setup mocks
        mock_benchmark = MagicMock()
        mock_benchmark.validate_api_key.return_value = (False, "Missing OPENAI_API_KEY")
        mock_benchmark.get_available_models.return_value = ([], {"model1": "Missing key"})
        mock_benchmark_class.return_value = mock_benchmark

        mock_load_dataset.return_value = [{"id": 1}]

        # Run preflight
        passed, results = run_preflight_checks(verbose=False)

        assert passed is False
        assert results["overall_status"] == "failed"

    @patch("app.evaluation.run_experiments.LLMBenchmark")
    @patch("app.evaluation.run_experiments.load_dataset")
    def test_preflight_missing_dataset(self, mock_load_dataset, mock_benchmark_class):
        """Preflight checks fail when dataset is missing."""
        # Setup mocks
        mock_benchmark = MagicMock()
        mock_benchmark.validate_api_key.return_value = (True, None)
        mock_benchmark.get_available_models.return_value = (["model1"], {})
        mock_benchmark_class.return_value = mock_benchmark

        # Dataset not found
        mock_load_dataset.side_effect = FileNotFoundError("Dataset not found")

        # Run preflight
        passed, results = run_preflight_checks(verbose=False)

        assert passed is False
        assert results["overall_status"] == "failed"

    @patch("app.evaluation.run_experiments.LLMBenchmark")
    @patch("app.evaluation.run_experiments.load_dataset")
    def test_preflight_results_structure(self, mock_load_dataset, mock_benchmark_class):
        """Preflight results have expected structure."""
        # Setup mocks
        mock_benchmark = MagicMock()
        mock_benchmark.validate_api_key.return_value = (True, None)
        mock_benchmark.get_available_models.return_value = (["model1"], {})
        mock_benchmark_class.return_value = mock_benchmark

        mock_load_dataset.return_value = [{"id": 1}]

        # Run preflight
        _passed, results = run_preflight_checks(verbose=False)

        # Check structure
        assert "api_keys" in results
        assert "datasets" in results
        assert "models_available" in results
        assert "overall_status" in results

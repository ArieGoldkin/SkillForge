"""Unit tests for evaluation dataset v2.0 validation.

Tests cover:
- JSON Schema validation
- Business logic validation (weights, approvals)
- ValidationResult dataclass
- Directory validation
- Report generation
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.evaluation.schemas.validation import (
    ValidationResult,
    generate_validation_report,
    validate_dataset,
    validate_directory,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_defaults(self):
        """Test ValidationResult has correct defaults."""
        result = ValidationResult(is_valid=False, dataset_name="test.json")
        assert result.is_valid is False
        assert result.example_count == 0
        assert result.validated_examples == 0
        assert result.draft_examples == 0
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_with_values(self):
        """Test ValidationResult with explicit values."""
        result = ValidationResult(
            dataset_name="test.json",
            is_valid=True,
            example_count=5,
            validated_examples=3,
            draft_examples=2,
            errors=["error1"],
            warnings=["warning1"],
        )
        assert result.is_valid is True
        assert result.example_count == 5
        assert result.validated_examples == 3
        assert result.draft_examples == 2
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]


class TestValidateDataset:
    """Tests for validate_dataset function."""

    @pytest.fixture
    def valid_dataset(self, tmp_path):
        """Create a valid v2.0 dataset file."""
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": "test_dataset",
                "task_type": "agent",
                "agent_types": ["security_auditor"],
                "domains": ["security"],
                "created_at": "2025-12-10T00:00:00Z",
                "updated_at": "2025-12-10T00:00:00Z",
                "release_tag": "v2.0.0",
                "description": "Test dataset",
                "maintainers": ["tester"],
            },
            "examples": [
                {
                    "id": "test-001",
                    "inputs": {
                        "content": "Test content for evaluation - this needs to be at least 20 characters long",
                        "content_type": "article",
                        "agent_type": "security_auditor",
                    },
                    "expected_outputs": {
                        "primary": {"key": "value"},
                        "acceptable_alternatives": [],
                        "forbidden_outputs": [],
                    },
                    "evaluation_criteria": {
                        "scoring_rubric": {
                            "correctness": {
                                "weight": 0.5,
                                "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.5},
                                "description": "Test correctness criteria",
                            },
                            "completeness": {"weight": 0.3, "required_fields": ["key"]},
                            "quality": {"weight": 0.2, "min_length": 10, "max_length": 1000},
                        },
                        "custom_evaluators": [],
                    },
                    "provenance": {
                        "source": "synthetic",
                        "created_at": "2025-12-10T00:00:00Z",
                        "created_by": "tester",
                    },
                    "validation": {
                        "status": "draft",
                        "validated_by": [],
                    },
                    "metadata": {
                        "difficulty": "medium",
                        "edge_case": False,
                        "adversarial": False,
                        "tags": ["test"],
                    },
                }
            ],
        }
        filepath = tmp_path / "valid_dataset.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)
        return filepath

    @pytest.fixture
    def invalid_weights_dataset(self, tmp_path):
        """Create dataset with invalid weights (don't sum to 1.0)."""
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": "test",
                "task_type": "agent",
                "agent_types": [],
                "domains": [],
                "created_at": "2025-12-10T00:00:00Z",
                "updated_at": "2025-12-10T00:00:00Z",
                "release_tag": "v1.0.0",
                "description": "Test",
                "maintainers": ["test"],
            },
            "examples": [
                {
                    "id": "test-001",
                    "inputs": {
                        "content": "Test content that is long enough for validation",
                        "content_type": "article",
                    },
                    "expected_outputs": {
                        "primary": {},
                        "acceptable_alternatives": [],
                        "forbidden_outputs": [],
                    },
                    "evaluation_criteria": {
                        "scoring_rubric": {
                            "correctness": {
                                "weight": 0.5,
                                "thresholds": {"perfect": 1.0, "acceptable": 0.7, "failing": 0.5},
                            },
                            "completeness": {"weight": 0.5, "required_fields": []},
                            "quality": {"weight": 0.5, "min_length": 10, "max_length": 1000},  # Total = 1.5
                        },
                        "custom_evaluators": [],
                    },
                    "provenance": {
                        "source": "synthetic",
                        "created_at": "2025-12-10T00:00:00Z",
                        "created_by": "tester",
                    },
                    "validation": {"status": "draft", "validated_by": []},
                    "metadata": {"difficulty": "easy", "edge_case": False, "adversarial": False},
                }
            ],
        }
        filepath = tmp_path / "invalid_weights.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)
        return filepath

    @pytest.fixture
    def insufficient_approvals_dataset(self, tmp_path):
        """Create dataset with validated status but insufficient approvals."""
        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": "test",
                "task_type": "agent",
                "agent_types": [],
                "domains": [],
                "created_at": "2025-12-10T00:00:00Z",
                "updated_at": "2025-12-10T00:00:00Z",
                "release_tag": "v1.0.0",
                "description": "Test",
                "maintainers": ["test"],
            },
            "examples": [
                {
                    "id": "test-001",
                    "inputs": {"content": "Test", "content_type": "article"},
                    "expected_outputs": {
                        "primary": {},
                        "acceptable_alternatives": [],
                        "forbidden_outputs": [],
                    },
                    "evaluation_criteria": {
                        "scoring_rubric": {
                            "correctness": {"weight": 0.5},
                            "completeness": {"weight": 0.3},
                            "quality": {"weight": 0.2},
                        },
                        "custom_evaluators": [],
                    },
                    "provenance": {
                        "source": "synthetic",
                        "created_at": "2025-12-10T00:00:00Z",
                        "created_by": "tester",
                    },
                    "validation": {
                        "status": "validated",  # Requires 2+ approvals
                        "validated_by": [
                            {
                                "reviewer": "reviewer1",
                                "validated_at": "2025-12-10T00:00:00Z",
                                "approved": True,
                            }
                        ],  # Only 1 approval
                    },
                    "metadata": {"difficulty": "easy", "edge_case": False, "adversarial": False},
                }
            ],
        }
        filepath = tmp_path / "insufficient_approvals.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)
        return filepath

    def test_validate_valid_dataset(self, valid_dataset):
        """Test validation passes for valid dataset."""
        result = validate_dataset(str(valid_dataset))
        assert result.is_valid is True
        assert result.example_count == 1
        assert result.draft_examples == 1
        assert result.errors == []

    def test_validate_invalid_weights(self, invalid_weights_dataset):
        """Test validation fails when weights don't sum to 1.0."""
        result = validate_dataset(str(invalid_weights_dataset))
        assert result.is_valid is False
        # Error message format: "test-001: Scoring rubric weights sum to 1.50, must sum to 1.0"
        assert any("must sum to 1.0" in e for e in result.errors)

    def test_validate_insufficient_approvals(self, insufficient_approvals_dataset):
        """Test validation fails with insufficient approvals for validated status."""
        result = validate_dataset(str(insufficient_approvals_dataset))
        assert result.is_valid is False
        assert any("requires ≥2 approvals" in e for e in result.errors)

    def test_validate_nonexistent_file(self):
        """Test validation handles missing file gracefully."""
        result = validate_dataset("/nonexistent/path/dataset.json")
        assert result.is_valid is False
        assert any("not found" in e.lower() or "no such file" in e.lower() for e in result.errors)

    def test_validate_invalid_json(self, tmp_path):
        """Test validation handles invalid JSON."""
        filepath = tmp_path / "invalid.json"
        with open(filepath, "w") as f:
            f.write("not valid json {{{")

        result = validate_dataset(str(filepath))
        assert result.is_valid is False
        assert len(result.errors) > 0


class TestValidateDirectory:
    """Tests for validate_directory function."""

    @pytest.fixture
    def dataset_directory(self, tmp_path):
        """Create directory with multiple datasets."""
        # Valid dataset
        valid = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": "valid",
                "task_type": "agent",
                "agent_types": [],
                "domains": [],
                "created_at": "2025-12-10T00:00:00Z",
                "updated_at": "2025-12-10T00:00:00Z",
                "release_tag": "v1.0.0",
                "description": "Test",
                "maintainers": ["test"],
            },
            "examples": [],
        }
        with open(tmp_path / "valid.json", "w") as f:
            json.dump(valid, f)

        # Invalid dataset
        invalid = {"version": "1.0.0"}  # Missing required fields
        with open(tmp_path / "invalid.json", "w") as f:
            json.dump(invalid, f)

        # Non-JSON file (should be skipped)
        with open(tmp_path / "readme.txt", "w") as f:
            f.write("Not a dataset")

        return tmp_path

    def test_validate_directory(self, dataset_directory):
        """Test validating a directory of datasets."""
        results = validate_directory(str(dataset_directory))
        assert len(results) == 2  # Should find 2 JSON files
        assert "valid.json" in results
        assert "invalid.json" in results

    def test_validate_directory_recursive(self, dataset_directory):
        """Test recursive directory validation."""
        # Create subdirectory with another dataset
        subdir = dataset_directory / "subdir"
        subdir.mkdir()
        nested = {"version": "2.0.0", "metadata": {}, "examples": []}
        with open(subdir / "nested.json", "w") as f:
            json.dump(nested, f)

        results = validate_directory(str(dataset_directory), recursive=True)
        assert len(results) >= 3  # At least 3 JSON files


class TestGenerateValidationReport:
    """Tests for generate_validation_report function."""

    def test_generate_report_single_result(self):
        """Test report generation for single result."""
        results = {
            "test.json": ValidationResult(
                dataset_name="test.json",
                is_valid=True,
                example_count=5,
                validated_examples=3,
                draft_examples=2,
            )
        }
        report = generate_validation_report(results)
        assert "test.json" in report
        assert "✅" in report or "PASS" in report.upper()
        assert "5" in report  # example count

    def test_generate_report_with_errors(self):
        """Test report includes errors."""
        results = {
            "bad.json": ValidationResult(
                dataset_name="bad.json",
                is_valid=False,
                errors=["Weight sum error", "Missing field"],
            )
        }
        report = generate_validation_report(results)
        assert "bad.json" in report
        assert "Weight sum error" in report or "error" in report.lower()

    def test_generate_report_multiple_results(self):
        """Test report for multiple datasets."""
        results = {
            "good.json": ValidationResult(
                dataset_name="good.json", is_valid=True, example_count=3
            ),
            "bad.json": ValidationResult(
                dataset_name="bad.json", is_valid=False, errors=["Error"]
            ),
        }
        report = generate_validation_report(results)
        assert "good.json" in report
        assert "bad.json" in report
        assert "Summary" in report or "2" in report  # Total count


class TestRealDatasetValidation:
    """Integration tests against real golden dataset."""

    def test_validate_golden_dataset(self):
        """Test validation against the actual golden dataset."""
        golden_path = Path(__file__).parent.parent.parent.parent / "app" / "evaluation" / "datasets" / "agent_analysis_golden_v2.json"

        if not golden_path.exists():
            pytest.skip("Golden dataset not found")

        result = validate_dataset(str(golden_path))

        # The golden dataset should be valid
        assert result.is_valid is True, f"Golden dataset validation failed: {result.errors}"
        assert result.example_count > 0, "Golden dataset should have examples"

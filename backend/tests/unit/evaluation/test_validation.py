"""Unit tests for evaluation dataset v2.0 validation.

Tests cover:
- JSON Schema validation
- Business logic validation (weights, approvals)
- ValidationResult dataclass
- Directory validation
- Report generation
"""

import json
from pathlib import Path

import pytest

from app.evaluation.schemas.validation import (
    MIN_QUERIES_PER_DIFFICULTY,
    VALID_DIFFICULTY_LEVELS,
    ValidationResult,
    generate_validation_report,
    validate_dataset,
    validate_difficulty_distribution,
    validate_directory,
    validate_query_fixtures,
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
        with filepath.open("w") as f:
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
                            "quality": {
                                "weight": 0.5,
                                "min_length": 10,
                                "max_length": 1000,
                            },  # Total = 1.5
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
        with filepath.open("w") as f:
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
        with filepath.open("w") as f:
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
        with filepath.open("w") as f:
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
        with (tmp_path / "valid.json").open("w") as f:
            json.dump(valid, f)

        # Invalid dataset
        invalid = {"version": "1.0.0"}  # Missing required fields
        with (tmp_path / "invalid.json").open("w") as f:
            json.dump(invalid, f)

        # Non-JSON file (should be skipped)
        with (tmp_path / "readme.txt").open("w") as f:
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
        with (subdir / "nested.json").open("w") as f:
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
            "good.json": ValidationResult(dataset_name="good.json", is_valid=True, example_count=3),
            "bad.json": ValidationResult(dataset_name="bad.json", is_valid=False, errors=["Error"]),
        }
        report = generate_validation_report(results)
        assert "good.json" in report
        assert "bad.json" in report
        assert "Summary" in report or "2" in report  # Total count


class TestRealDatasetValidation:
    """Integration tests against real golden dataset."""

    def test_validate_golden_dataset(self):
        """Test validation against the actual golden dataset."""
        golden_path = (
            Path(__file__).parent.parent.parent.parent
            / "app"
            / "evaluation"
            / "datasets"
            / "agent_analysis_golden_v2.json"
        )

        if not golden_path.exists():
            pytest.skip("Golden dataset not found")

        result = validate_dataset(str(golden_path))

        # The golden dataset should be valid
        assert result.is_valid is True, f"Golden dataset validation failed: {result.errors}"
        assert result.example_count > 0, "Golden dataset should have examples"


class TestDifficultyValidation:
    """Tests for difficulty stratification validation functions."""

    def test_valid_difficulty_levels_constant(self):
        """Test VALID_DIFFICULTY_LEVELS contains correct values."""
        expected = {"trivial", "easy", "medium", "hard", "adversarial"}
        assert expected == VALID_DIFFICULTY_LEVELS

    def test_min_queries_per_difficulty_constant(self):
        """Test MIN_QUERIES_PER_DIFFICULTY is reasonable."""
        assert MIN_QUERIES_PER_DIFFICULTY == 3

    def test_validate_difficulty_distribution_all_valid(self):
        """Test validation passes for valid difficulty distribution."""
        examples = [
            {"id": "ex-1", "metadata": {"difficulty": "trivial"}},
            {"id": "ex-2", "metadata": {"difficulty": "easy"}},
            {"id": "ex-3", "metadata": {"difficulty": "medium"}},
            {"id": "ex-4", "metadata": {"difficulty": "hard"}},
            {"id": "ex-5", "metadata": {"difficulty": "adversarial"}},
        ]
        errors, _warnings, distribution = validate_difficulty_distribution(
            examples, min_per_level=1
        )

        assert errors == []
        assert distribution["trivial"] == 1
        assert distribution["easy"] == 1
        assert distribution["medium"] == 1
        assert distribution["hard"] == 1
        assert distribution["adversarial"] == 1

    def test_validate_difficulty_distribution_missing_field(self):
        """Test validation catches missing difficulty field."""
        examples = [
            {"id": "ex-1", "metadata": {"difficulty": "easy"}},
            {"id": "ex-2", "metadata": {}},  # Missing difficulty
        ]
        errors, _warnings, _distribution = validate_difficulty_distribution(examples)

        assert len(errors) == 1
        assert "ex-2" in errors[0]
        assert "Missing metadata.difficulty" in errors[0]

    def test_validate_difficulty_distribution_invalid_value(self):
        """Test validation catches invalid difficulty values."""
        examples = [
            {
                "id": "ex-1",
                "metadata": {"difficulty": "expert"},
            },  # Invalid - "expert" not in new schema
            {"id": "ex-2", "metadata": {"difficulty": "easy"}},
        ]
        errors, _warnings, _distribution = validate_difficulty_distribution(examples)

        assert len(errors) == 1
        assert "ex-1" in errors[0]
        assert "Invalid difficulty 'expert'" in errors[0]

    def test_validate_difficulty_distribution_warns_low_count(self):
        """Test validation warns when difficulty count is below minimum."""
        examples = [
            {"id": "ex-1", "metadata": {"difficulty": "easy"}},
            {"id": "ex-2", "metadata": {"difficulty": "easy"}},  # Only 2 easy
        ]
        _errors, warnings, _distribution = validate_difficulty_distribution(
            examples, min_per_level=3
        )

        # Should warn about missing levels and low counts
        assert any("No examples with difficulty='adversarial'" in w for w in warnings)
        assert any("Only 2 examples with difficulty='easy'" in w for w in warnings)

    def test_validate_difficulty_distribution_no_metadata(self):
        """Test validation handles examples without metadata section."""
        examples = [
            {"id": "ex-1"},  # No metadata at all
        ]
        errors, _warnings, _distribution = validate_difficulty_distribution(examples)

        assert len(errors) == 1
        assert "Missing metadata.difficulty" in errors[0]


class TestValidateQueryFixtures:
    """Tests for validate_query_fixtures function."""

    @pytest.fixture
    def valid_queries_fixture(self, tmp_path):
        """Create valid queries.json with all difficulty levels."""
        queries = {
            "version": "1.1",
            "queries": [
                {"id": "q-1", "query": "test", "difficulty": "trivial"},
                {"id": "q-2", "query": "test", "difficulty": "trivial"},
                {"id": "q-3", "query": "test", "difficulty": "trivial"},
                {"id": "q-4", "query": "test", "difficulty": "easy"},
                {"id": "q-5", "query": "test", "difficulty": "easy"},
                {"id": "q-6", "query": "test", "difficulty": "easy"},
                {"id": "q-7", "query": "test", "difficulty": "medium"},
                {"id": "q-8", "query": "test", "difficulty": "medium"},
                {"id": "q-9", "query": "test", "difficulty": "medium"},
                {"id": "q-10", "query": "test", "difficulty": "hard"},
                {"id": "q-11", "query": "test", "difficulty": "hard"},
                {"id": "q-12", "query": "test", "difficulty": "hard"},
                {"id": "q-13", "query": "test", "difficulty": "adversarial"},
                {"id": "q-14", "query": "test", "difficulty": "adversarial"},
                {"id": "q-15", "query": "test", "difficulty": "adversarial"},
            ],
        }
        filepath = tmp_path / "valid_queries.json"
        with filepath.open("w") as f:
            json.dump(queries, f)
        return filepath

    @pytest.fixture
    def missing_difficulty_fixture(self, tmp_path):
        """Create queries.json with missing difficulty fields."""
        queries = {
            "version": "1.0",
            "queries": [
                {"id": "q-1", "query": "test"},  # No difficulty
                {"id": "q-2", "query": "test", "difficulty": "easy"},
            ],
        }
        filepath = tmp_path / "missing_diff.json"
        with filepath.open("w") as f:
            json.dump(queries, f)
        return filepath

    @pytest.fixture
    def invalid_difficulty_fixture(self, tmp_path):
        """Create queries.json with invalid difficulty value."""
        queries = {
            "version": "1.0",
            "queries": [
                {"id": "q-1", "query": "test", "difficulty": "expert"},  # Invalid
            ],
        }
        filepath = tmp_path / "invalid_diff.json"
        with filepath.open("w") as f:
            json.dump(queries, f)
        return filepath

    def test_validate_valid_queries_fixture(self, valid_queries_fixture):
        """Test validation passes for well-distributed queries fixture."""
        result = validate_query_fixtures(str(valid_queries_fixture))

        assert result.is_valid is True
        assert result.example_count == 15
        assert result.errors == []
        # Should have distribution summary in warnings
        assert any("Distribution:" in w for w in result.warnings)

    def test_validate_missing_difficulty(self, missing_difficulty_fixture):
        """Test validation fails for missing difficulty field."""
        result = validate_query_fixtures(str(missing_difficulty_fixture))

        assert result.is_valid is False
        assert any("q-1" in e and "Missing difficulty" in e for e in result.errors)

    def test_validate_invalid_difficulty(self, invalid_difficulty_fixture):
        """Test validation fails for invalid difficulty value."""
        result = validate_query_fixtures(str(invalid_difficulty_fixture))

        assert result.is_valid is False
        assert any("Invalid difficulty 'expert'" in e for e in result.errors)

    def test_validate_nonexistent_fixture(self):
        """Test validation handles missing fixture file."""
        result = validate_query_fixtures("/nonexistent/queries.json")

        assert result.is_valid is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_validate_invalid_json_fixture(self, tmp_path):
        """Test validation handles invalid JSON fixture."""
        filepath = tmp_path / "bad.json"
        with filepath.open("w") as f:
            f.write("not valid json")

        result = validate_query_fixtures(str(filepath))

        assert result.is_valid is False
        assert any("Invalid JSON" in e for e in result.errors)


class TestRealQueryFixtureValidation:
    """Integration tests against real queries.json fixture."""

    def test_validate_real_queries_fixture(self):
        """Test validation against the actual queries.json fixture."""
        fixture_path = (
            Path(__file__).parent.parent.parent.parent
            / "tests"
            / "smoke"
            / "retrieval"
            / "fixtures"
            / "queries.json"
        )

        if not fixture_path.exists():
            pytest.skip("Queries fixture not found")

        result = validate_query_fixtures(str(fixture_path))

        # The queries fixture should be valid after #255 implementation
        assert result.is_valid is True, f"Queries fixture validation failed: {result.errors}"
        assert result.example_count == 21, "Queries fixture should have 21 queries"

        # Check distribution warning for minimum coverage
        distribution_warning = next((w for w in result.warnings if "Distribution:" in w), None)
        assert distribution_warning is not None, "Should include distribution summary"

        # Verify all difficulty levels are represented
        assert "trivial: 3" in distribution_warning
        assert "easy: 5" in distribution_warning
        assert "medium: 6" in distribution_warning
        assert "hard: 3" in distribution_warning
        assert "adversarial: 4" in distribution_warning

"""Unit tests for upload_datasets_to_langfuse script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from upload_datasets_to_langfuse import (  # type: ignore[import-not-found]
    DATASET_MAPPING,
    check_langfuse_enabled,
    format_agent_analysis_item,
    format_supervisor_item,
    format_synthesis_item,
    upload_dataset,
)


class TestCheckLangfuseEnabled:
    """Tests for check_langfuse_enabled function."""

    def test_disabled_when_env_not_set(self, monkeypatch):
        """Test that Langfuse is disabled when LANGFUSE_ENABLED is not set."""
        monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
        assert check_langfuse_enabled() is False

    def test_disabled_when_env_false(self, monkeypatch):
        """Test that Langfuse is disabled when LANGFUSE_ENABLED=false."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "false")
        assert check_langfuse_enabled() is False

    def test_disabled_when_missing_public_key(self, monkeypatch):
        """Test that Langfuse is disabled when LANGFUSE_PUBLIC_KEY is missing."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "true")
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
        assert check_langfuse_enabled() is False

    def test_disabled_when_missing_secret_key(self, monkeypatch):
        """Test that Langfuse is disabled when LANGFUSE_SECRET_KEY is missing."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "true")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        assert check_langfuse_enabled() is False

    def test_enabled_when_all_credentials_set(self, monkeypatch):
        """Test that Langfuse is enabled when all credentials are set."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "true")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
        assert check_langfuse_enabled() is True


class TestFormatSupervisorItem:
    """Tests for format_supervisor_item function."""

    def test_format_supervisor_item(self):
        """Test formatting supervisor dataset item."""
        example = {
            "id": "sup-001",
            "inputs": {
                "content": "Test content",
                "content_type": "article",
                "url": "https://example.com",
                "extraction_metadata": {"title": "Test Article"},
            },
            "outputs": {
                "expected_agents": ["tech_comparator"],
                "optional_agents": ["security_auditor"],
                "reasoning": "Test reasoning",
            },
            "metadata": {
                "complexity": "medium",
                "primary_agent": "tech_comparator",
                "source": "synthetic",
            },
        }

        input_data, expected_output, metadata = format_supervisor_item(example)

        assert input_data["content"] == "Test content"
        assert input_data["content_type"] == "article"
        assert input_data["url"] == "https://example.com"
        assert expected_output["expected_agents"] == ["tech_comparator"]
        assert expected_output["optional_agents"] == ["security_auditor"]
        assert metadata["id"] == "sup-001"
        assert metadata["complexity"] == "medium"


class TestFormatAgentAnalysisItem:
    """Tests for format_agent_analysis_item function."""

    def test_format_agent_analysis_item(self):
        """Test formatting agent_analysis dataset item."""
        example = {
            "id": "rag-001",
            "inputs": {
                "content": "RAG survey paper",
                "content_type": "article",
                "agent_type": "tech_comparator",
                "metadata": {"url": "https://arxiv.org/abs/123"},
            },
            "expected_outputs": {
                "primary": {"key_findings": ["RAG", "retrieval"]},
            },
            "evaluation_criteria": {
                "scoring_rubric": {"correctness": {"weight": 0.5}},
            },
        }

        input_data, expected_output, metadata = format_agent_analysis_item(example)

        assert input_data["content"] == "RAG survey paper"
        assert input_data["agent_type"] == "tech_comparator"
        assert expected_output["primary"]["key_findings"] == ["RAG", "retrieval"]
        assert metadata["id"] == "rag-001"
        assert "scoring_rubric" in metadata["evaluation_criteria"]


class TestFormatSynthesisItem:
    """Tests for format_synthesis_item function."""

    def test_format_synthesis_item(self):
        """Test formatting synthesis dataset item."""
        example = {
            "id": "synth-001",
            "inputs": {
                "agent_findings": [
                    {"agent_type": "tech_comparator", "finding": {"key": "value"}},
                ],
                "content_summary": "Test summary",
                "coverage_score": 0.75,
            },
            "outputs": {
                "executive_summary": "Test executive summary",
                "key_findings": ["Finding 1", "Finding 2"],
            },
            "evaluation_criteria": {"rubric": "test"},
            "metadata": {"source": "test"},
        }

        input_data, expected_output, metadata = format_synthesis_item(example)

        assert len(input_data["agent_findings"]) == 1
        assert input_data["content_summary"] == "Test summary"
        assert input_data["coverage_score"] == 0.75
        assert expected_output["executive_summary"] == "Test executive summary"
        assert metadata["id"] == "synth-001"


class TestUploadDataset:
    """Tests for upload_dataset function."""

    def test_upload_dataset_unknown_dataset(self):
        """Test upload_dataset with unknown dataset name."""
        result = upload_dataset("unknown_dataset")
        assert result is False

    def test_upload_dataset_dry_run(self):
        """Test upload_dataset in dry-run mode."""
        result = upload_dataset("supervisor", dry_run=True)
        assert result is True

    def test_upload_dataset_file_not_found(self):
        """Test upload_dataset with missing dataset file."""
        with patch("upload_datasets_to_langfuse.load_dataset") as mock_load:
            mock_load.side_effect = FileNotFoundError("Dataset not found")
            result = upload_dataset("supervisor")
            assert result is False

    @patch("upload_datasets_to_langfuse.get_langfuse_client")
    @patch("upload_datasets_to_langfuse.load_dataset")
    def test_upload_dataset_success(self, mock_load, mock_client):
        """Test successful dataset upload."""
        # Mock dataset loading
        mock_load.return_value = [
            {
                "id": "sup-001",
                "inputs": {
                    "content": "Test",
                    "content_type": "article",
                    "url": "https://example.com",
                    "extraction_metadata": {},
                },
                "outputs": {
                    "expected_agents": ["tech_comparator"],
                    "optional_agents": [],
                    "reasoning": "Test",
                },
                "metadata": {
                    "complexity": "medium",
                    "primary_agent": "tech_comparator",
                    "source": "test",
                },
            }
        ]

        # Mock Langfuse client
        mock_langfuse = MagicMock()
        mock_langfuse.get_dataset.side_effect = Exception("Dataset not found")
        mock_client.return_value = mock_langfuse

        result = upload_dataset("supervisor")
        assert result is True

        # Verify dataset creation
        assert mock_langfuse.create_dataset.called
        dataset_call = mock_langfuse.create_dataset.call_args
        assert dataset_call.kwargs["name"] == "supervisor_routing_golden"
        assert "description" in dataset_call.kwargs

        # Verify item creation
        assert mock_langfuse.create_dataset_item.called
        item_call = mock_langfuse.create_dataset_item.call_args
        assert item_call.kwargs["dataset_name"] == "supervisor_routing_golden"
        assert "input" in item_call.kwargs
        assert "expected_output" in item_call.kwargs

    @patch("upload_datasets_to_langfuse.get_langfuse_client")
    @patch("upload_datasets_to_langfuse.load_dataset")
    def test_upload_dataset_existing_dataset(self, mock_load, mock_client):
        """Test upload to existing dataset."""
        mock_load.return_value = [
            {
                "id": "sup-001",
                "inputs": {
                    "content": "Test",
                    "content_type": "article",
                    "url": "https://example.com",
                    "extraction_metadata": {},
                },
                "outputs": {
                    "expected_agents": ["tech_comparator"],
                    "optional_agents": [],
                    "reasoning": "Test",
                },
                "metadata": {
                    "complexity": "medium",
                    "primary_agent": "tech_comparator",
                    "source": "test",
                },
            }
        ]

        # Mock Langfuse client - dataset exists
        mock_langfuse = MagicMock()
        mock_dataset = MagicMock()
        mock_langfuse.get_dataset.return_value = mock_dataset
        mock_client.return_value = mock_langfuse

        result = upload_dataset("supervisor")
        assert result is True

        # Verify dataset creation NOT called (dataset exists)
        assert not mock_langfuse.create_dataset.called

        # Verify item creation still called
        assert mock_langfuse.create_dataset_item.called


class TestDatasetMapping:
    """Tests for DATASET_MAPPING configuration."""

    def test_all_datasets_have_required_keys(self):
        """Test that all datasets have required configuration keys."""
        required_keys = {"file_path", "langfuse_name", "description"}

        for dataset_name, config in DATASET_MAPPING.items():
            assert required_keys.issubset(config.keys()), (
                f"Dataset {dataset_name} missing required keys"
            )
            assert isinstance(config["file_path"], str)
            assert isinstance(config["langfuse_name"], str)
            assert isinstance(config["description"], str)

    def test_langfuse_names_are_unique(self):
        """Test that Langfuse dataset names are unique."""
        langfuse_names = [config["langfuse_name"] for config in DATASET_MAPPING.values()]
        assert len(langfuse_names) == len(set(langfuse_names)), (
            "Duplicate Langfuse dataset names found"
        )

    def test_expected_datasets_present(self):
        """Test that expected datasets are present."""
        expected_datasets = {"supervisor", "agent_analysis", "synthesis"}
        assert expected_datasets.issubset(DATASET_MAPPING.keys())

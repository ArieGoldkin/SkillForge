"""Unit tests for LangSmith trace extractor.

Tests cover:
- ExtractionConfig dataclass
- LangSmithExtractor helper methods (without API calls)
- Dataset saving functionality
- Optional import handling
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.evaluation.ingestion.langsmith_extractor import (
    LANGSMITH_AVAILABLE,
    ExtractionConfig,
)


class TestExtractionConfig:
    """Tests for ExtractionConfig dataclass."""

    def test_extraction_config_defaults(self):
        """Test ExtractionConfig has correct defaults."""
        config = ExtractionConfig(project_name="test-project", task_type="agent")

        assert config.project_name == "test-project"
        assert config.task_type == "agent"
        assert config.agent_type is None
        assert config.min_confidence == 0.85
        assert config.max_latency_ms == 5000
        assert config.date_start is None
        assert config.date_end is None
        assert config.limit == 100

    def test_extraction_config_custom_values(self):
        """Test ExtractionConfig with custom values."""
        start_date = datetime(2025, 12, 1)
        end_date = datetime(2025, 12, 10)

        config = ExtractionConfig(
            project_name="skillforge-prod",
            task_type="supervisor",
            agent_type="security_auditor",
            min_confidence=0.90,
            max_latency_ms=3000,
            date_start=start_date,
            date_end=end_date,
            limit=50,
        )

        assert config.project_name == "skillforge-prod"
        assert config.task_type == "supervisor"
        assert config.agent_type == "security_auditor"
        assert config.min_confidence == 0.90
        assert config.max_latency_ms == 3000
        assert config.date_start == start_date
        assert config.date_end == end_date
        assert config.limit == 50

    def test_extraction_config_task_types(self):
        """Test valid task types."""
        for task_type in ["supervisor", "agent", "synthesis"]:
            config = ExtractionConfig(project_name="test", task_type=task_type)
            assert config.task_type == task_type


class TestLangSmithAvailability:
    """Tests for optional LangSmith import handling."""

    def test_langsmith_available_flag(self):
        """Test LANGSMITH_AVAILABLE is a boolean."""
        assert isinstance(LANGSMITH_AVAILABLE, bool)

    @pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
    def test_langsmith_extractor_import(self):
        """Test LangSmithExtractor can be imported when available."""
        from app.evaluation.ingestion import LangSmithExtractor

        assert LangSmithExtractor is not None


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorMethods:
    """Tests for LangSmithExtractor helper methods (mocked)."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mocked client."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()
            return extractor

    def test_extract_confidence_from_outputs(self, extractor):
        """Test confidence extraction from various output structures."""
        # Direct confidence field
        outputs = {"confidence": 0.92}
        assert extractor._extract_confidence(outputs) == 0.92

        # confidence_score field
        outputs = {"confidence_score": 0.88}
        assert extractor._extract_confidence(outputs) == 0.88

        # Nested in supervisor_decision
        outputs = {"supervisor_decision": {"confidence": 0.85}}
        assert extractor._extract_confidence(outputs) == 0.85

        # Nested in agent_findings
        outputs = {"agent_findings": [{"confidence": 0.78}]}
        assert extractor._extract_confidence(outputs) == 0.78

        # No confidence found
        outputs = {"result": "something"}
        assert extractor._extract_confidence(outputs) is None

    def test_extract_agent_type_from_inputs(self, extractor):
        """Test agent type extraction from inputs."""
        # Direct agent_type
        inputs = {"agent_type": "security_auditor"}
        assert extractor._extract_agent_type(inputs) == "security_auditor"

        # From supervisor_decision
        inputs = {"supervisor_decision": {"agents": ["tech_comparator", "security_auditor"]}}
        assert extractor._extract_agent_type(inputs) == "tech_comparator"

        # Empty inputs
        inputs = {}
        assert extractor._extract_agent_type(inputs) is None

    def test_extract_primary_outputs_supervisor(self, extractor):
        """Test primary output extraction for supervisor task."""
        outputs = {
            "supervisor_decision": {
                "agents": ["security_auditor"],
                "confidence": 0.9,
                "reasoning": "Security content detected",
            }
        }
        result = extractor._extract_primary_outputs(outputs, "supervisor")
        assert result["selected_agents"] == ["security_auditor"]
        assert result["confidence"] == 0.9
        assert result["reasoning"] == "Security content detected"

    def test_extract_primary_outputs_agent(self, extractor):
        """Test primary output extraction for agent task."""
        outputs = {"agent_findings": [{"risk_type": "xss", "severity": "high"}]}
        result = extractor._extract_primary_outputs(outputs, "agent")
        assert result["risk_type"] == "xss"
        assert result["severity"] == "high"

    def test_extract_primary_outputs_synthesis(self, extractor):
        """Test primary output extraction for synthesis task."""
        outputs = {"aggregated_insights": {"summary": "Key findings"}}
        result = extractor._extract_primary_outputs(outputs, "synthesis")
        assert result["summary"] == "Key findings"

    def test_estimate_difficulty(self, extractor):
        """Test difficulty estimation based on content length."""
        assert extractor._estimate_difficulty("x" * 100) == "easy"
        assert extractor._estimate_difficulty("x" * 500) == "medium"
        assert extractor._estimate_difficulty("x" * 1000) == "medium"
        assert extractor._estimate_difficulty("x" * 2500) == "hard"
        assert extractor._estimate_difficulty("x" * 6000) == "expert"

    def test_extract_tags(self, extractor):
        """Test tag extraction from inputs/outputs."""
        inputs = {"content_type": "tutorial", "agent_type": "security_auditor"}
        outputs = {}
        tags = extractor._extract_tags(inputs, outputs)

        assert "tutorial" in tags
        assert "security_auditor" in tags
        assert "langsmith" in tags
        assert "production" in tags

    def test_generate_default_criteria(self, extractor):
        """Test default evaluation criteria generation."""
        criteria = extractor._generate_default_criteria("agent")

        assert "scoring_rubric" in criteria
        assert "correctness" in criteria["scoring_rubric"]
        assert criteria["scoring_rubric"]["correctness"]["weight"] == 0.5
        assert criteria["scoring_rubric"]["completeness"]["weight"] == 0.3
        assert criteria["scoring_rubric"]["quality"]["weight"] == 0.2

    def test_save_dataset(self, extractor, tmp_path):
        """Test saving extracted examples to dataset file."""
        examples = [
            {
                "id": "test-001",
                "inputs": {"content": "Test", "agent_type": "security_auditor"},
                "expected_outputs": {"primary": {}},
                "evaluation_criteria": {},
                "provenance": {"source": "langsmith"},
                "validation": {"status": "draft"},
                "metadata": {"difficulty": "medium"},
            }
        ]

        output_path = tmp_path / "output.json"
        extractor.save_dataset(examples, str(output_path), dataset_name="test_dataset")

        assert output_path.exists()

        with open(output_path) as f:
            dataset = json.load(f)

        assert dataset["version"] == "2.0.0"
        assert dataset["metadata"]["dataset_name"] == "test_dataset"
        assert len(dataset["examples"]) == 1
        assert dataset["examples"][0]["id"] == "test-001"


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorIntegration:
    """Integration tests with mocked LangSmith client."""

    @pytest.fixture
    def mock_trace(self):
        """Create a mock LangSmith trace/run."""
        trace = MagicMock()
        trace.id = "abc123-def456"
        trace.error = None
        trace.start_time = datetime.utcnow() - timedelta(seconds=2)
        trace.end_time = datetime.utcnow()
        trace.inputs = {
            "content": "Test content about React and Vue frameworks",
            "content_type": "article",
        }
        trace.outputs = {
            "confidence": 0.92,
            "agent_findings": [{"primary_tech": "React", "confidence": 0.9}],
        }
        return trace

    def test_extract_with_mocked_client(self, mock_trace):
        """Test full extraction flow with mocked client."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_client.list_runs.return_value = [mock_trace]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            config = ExtractionConfig(
                project_name="test-project",
                task_type="agent",
                min_confidence=0.85,
                limit=10,
            )

            examples = extractor.extract(config)

            assert len(examples) == 1
            assert examples[0]["inputs"]["content"] == "Test content about React and Vue frameworks"
            assert examples[0]["validation"]["status"] == "draft"
            assert examples[0]["provenance"]["source"] == "langsmith"

    def test_extract_filters_by_confidence(self, mock_trace):
        """Test that low confidence traces are filtered out."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        # Set low confidence
        mock_trace.outputs = {"confidence": 0.5}

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_runs.return_value = [mock_trace]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            config = ExtractionConfig(
                project_name="test-project",
                task_type="agent",
                min_confidence=0.85,  # Higher than trace confidence
            )

            examples = extractor.extract(config)

            # Should be filtered out due to low confidence
            assert len(examples) == 0

    def test_extract_filters_by_latency(self, mock_trace):
        """Test that slow traces are filtered out."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        # Set high latency (10 seconds)
        mock_trace.start_time = datetime.utcnow() - timedelta(seconds=10)
        mock_trace.end_time = datetime.utcnow()

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_runs.return_value = [mock_trace]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            config = ExtractionConfig(
                project_name="test-project",
                task_type="agent",
                max_latency_ms=5000,  # 5 seconds max
            )

            examples = extractor.extract(config)

            # Should be filtered out due to high latency
            assert len(examples) == 0

    def test_extract_filters_errors(self):
        """Test that traces with errors are filtered out."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        error_trace = MagicMock()
        error_trace.id = "error-trace"
        error_trace.error = "Some error occurred"
        error_trace.inputs = {"content": "Test"}
        error_trace.outputs = {}

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_runs.return_value = [error_trace]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            config = ExtractionConfig(project_name="test-project", task_type="agent")

            examples = extractor.extract(config)

            # Should be filtered out due to error
            assert len(examples) == 0

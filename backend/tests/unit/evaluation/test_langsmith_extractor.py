"""Unit tests for LangSmith trace extractor.

Tests cover:
- ExtractionConfig dataclass
- LangSmithExtractor helper methods (without API calls)
- Domain inference
- PII anonymization integration
- Batch extraction methods
- Dataset saving functionality
- Optional import handling
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.evaluation.ingestion.langsmith_extractor import (
    AGENT_TO_DOMAIN,
    ALL_AGENT_TYPES,
    KEYWORD_DOMAIN_MAP,
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

        with output_path.open() as f:
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
        trace.start_time = datetime.now(UTC) - timedelta(seconds=2)
        trace.end_time = datetime.now(UTC)
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
        mock_trace.start_time = datetime.now(UTC) - timedelta(seconds=10)
        mock_trace.end_time = datetime.now(UTC)

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


class TestDomainInferenceConstants:
    """Tests for domain inference constants and mappings."""

    def test_all_agent_types_has_8_agents(self):
        """Test that ALL_AGENT_TYPES contains exactly 8 agent types."""
        assert len(ALL_AGENT_TYPES) == 8
        expected_agents = {
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "dependency_mapper",
            "trend_validator",
            "integration_feasibility",
        }
        assert set(ALL_AGENT_TYPES) == expected_agents

    def test_agent_to_domain_coverage(self):
        """Test that all agents have domain mappings."""
        for agent in ALL_AGENT_TYPES:
            assert agent in AGENT_TO_DOMAIN, f"Agent {agent} missing from AGENT_TO_DOMAIN"
            assert len(AGENT_TO_DOMAIN[agent]) >= 1

    def test_keyword_domain_map_not_empty(self):
        """Test that keyword domain map is populated."""
        assert len(KEYWORD_DOMAIN_MAP) > 10
        # Check some expected keywords
        assert "api" in KEYWORD_DOMAIN_MAP
        assert "database" in KEYWORD_DOMAIN_MAP
        assert "security" in KEYWORD_DOMAIN_MAP
        assert "docker" in KEYWORD_DOMAIN_MAP


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorDomainInference:
    """Tests for domain inference functionality."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mocked client."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()
            return extractor

    def test_infer_domain_from_keyword_api(self, extractor):
        """Test domain inference from API keywords."""
        content = "How to build a REST API with FastAPI"
        domain = extractor._infer_domain(content)
        assert domain == "backend"

    def test_infer_domain_from_keyword_database(self, extractor):
        """Test domain inference from database keywords."""
        content = "Optimizing SQL queries for PostgreSQL"
        domain = extractor._infer_domain(content)
        assert domain == "data-layer"

    def test_infer_domain_from_keyword_security(self, extractor):
        """Test domain inference from security keywords."""
        content = "Implementing OAuth2 authentication flow"
        domain = extractor._infer_domain(content)
        assert domain == "security"

    def test_infer_domain_from_keyword_frontend(self, extractor):
        """Test domain inference from frontend keywords."""
        content = "Building React components with hooks"
        domain = extractor._infer_domain(content)
        assert domain == "frontend"

    def test_infer_domain_from_keyword_devops(self, extractor):
        """Test domain inference from devops keywords."""
        content = "Setting up Kubernetes deployment pipelines"
        domain = extractor._infer_domain(content)
        assert domain == "devops"

    def test_infer_domain_from_agent_type(self, extractor):
        """Test domain inference from agent type fallback."""
        content = "Some generic content without domain keywords"
        domain = extractor._infer_domain(content, agent_type="security_auditor")
        assert domain == "security"

    def test_infer_domain_from_agent_type_performance(self, extractor):
        """Test domain inference for performance analyst."""
        content = "General performance discussion"
        domain = extractor._infer_domain(content, agent_type="performance_analyst")
        assert domain == "data-layer"  # First in list for performance_analyst

    def test_infer_domain_default_general(self, extractor):
        """Test domain defaults to general when no match."""
        content = "Random content with no technical keywords"
        domain = extractor._infer_domain(content)
        assert domain == "general"

    def test_infer_domain_from_inputs_content_type(self, extractor):
        """Test domain inference from inputs content_type."""
        content = "Random content"
        inputs = {"content_type": "database-tutorial"}
        domain = extractor._infer_domain(content, inputs=inputs)
        assert domain == "data-layer"


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorPIIAnonymization:
    """Tests for PII anonymization integration."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mocked client."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()
            return extractor

    def test_anonymize_content_with_email(self, extractor):
        """Test PII anonymization of content with email."""
        content = "Contact john.doe@company.com for more info"
        anonymized, has_pii, pii_count = extractor._anonymize_content(content)

        assert has_pii is True
        assert pii_count >= 1
        assert "john.doe@company.com" not in anonymized
        assert "[EMAIL_1]" in anonymized

    def test_anonymize_content_with_phone(self, extractor):
        """Test PII anonymization of content with phone."""
        content = "Call us at 555-123-4567"
        anonymized, has_pii, _pii_count = extractor._anonymize_content(content)

        assert has_pii is True
        assert "555-123-4567" not in anonymized

    def test_anonymize_content_no_pii(self, extractor):
        """Test content without PII."""
        content = "This is just a normal sentence about coding."
        anonymized, has_pii, pii_count = extractor._anonymize_content(content)

        assert has_pii is False
        assert pii_count == 0
        assert anonymized == content

    def test_anonymize_content_preserves_safe_emails(self, extractor):
        """Test that allowlisted emails are preserved."""
        content = "Test with example@example.com"
        anonymized, _has_pii, _pii_count = extractor._anonymize_content(content)

        # example.com is allowlisted
        assert "example@example.com" in anonymized


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorConversionWithEnhancements:
    """Tests for trace conversion with domain/PII enhancements."""

    @pytest.fixture
    def mock_trace(self):
        """Create a mock trace with PII content."""
        trace = MagicMock()
        trace.id = "trace-123-456"
        trace.error = None
        trace.start_time = datetime.now(UTC) - timedelta(seconds=2)
        trace.end_time = datetime.now(UTC)
        trace.inputs = {
            "content": "Contact john@corp.com for the API documentation",
            "content_type": "article",
        }
        trace.outputs = {"confidence": 0.92}
        return trace

    def test_convert_trace_includes_domain(self, mock_trace):
        """Test that converted examples include inferred domain."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()

            config = ExtractionConfig(project_name="test", task_type="agent")
            example = extractor._convert_trace_to_example(mock_trace, config)

            assert "domain" in example["metadata"]
            assert example["metadata"]["domain"] == "backend"  # API keyword

    def test_convert_trace_includes_pii_metadata(self, mock_trace):
        """Test that converted examples include PII anonymization metadata."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()

            config = ExtractionConfig(project_name="test", task_type="agent")
            example = extractor._convert_trace_to_example(mock_trace, config)

            assert "pii_anonymized" in example["metadata"]
            assert "pii_count" in example["metadata"]
            # john@corp.com should be anonymized
            assert example["metadata"]["pii_anonymized"] is True
            assert example["metadata"]["pii_count"] >= 1

    def test_convert_trace_content_anonymized(self, mock_trace):
        """Test that PII in content is anonymized."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()

            config = ExtractionConfig(project_name="test", task_type="agent")
            example = extractor._convert_trace_to_example(mock_trace, config)

            assert "john@corp.com" not in example["inputs"]["content"]
            assert "[EMAIL_1]" in example["inputs"]["content"]


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorBatchMethods:
    """Tests for batch extraction methods."""

    @pytest.fixture
    def mock_trace_factory(self):
        """Create mock traces with configurable agent types."""

        def create_trace(agent_type: str, content: str = "Test content"):
            trace = MagicMock()
            trace.id = f"trace-{agent_type}-123"
            trace.error = None
            trace.start_time = datetime.now(UTC) - timedelta(seconds=2)
            trace.end_time = datetime.now(UTC)
            trace.inputs = {
                "content": content,
                "content_type": "article",
                "agent_type": agent_type,
            }
            trace.outputs = {"confidence": 0.90}
            return trace

        return create_trace

    def test_extract_all_agents_calls_each_agent(self, mock_trace_factory):
        """Test that extract_all_agents queries for each agent type."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            mock_client = MagicMock()
            # Return one trace per call
            mock_client.list_runs.return_value = [
                mock_trace_factory("security_auditor", "Security test")
            ]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            examples = extractor.extract_all_agents(project_name="test", examples_per_agent=1)

            # Should have called list_runs 8 times (once per agent)
            assert mock_client.list_runs.call_count == 8

    def test_extract_by_confidence_bands_structure(self, mock_trace_factory):
        """Test extract_by_confidence_bands returns correct structure."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.list_runs.return_value = [
                mock_trace_factory("tech_comparator", "Test content")
            ]
            mock_client_class.return_value = mock_client

            extractor = LangSmithExtractor()
            bands = extractor.extract_by_confidence_bands(project_name="test", examples_per_band=5)

            assert "high" in bands
            assert "medium" in bands
            assert "low" in bands
            assert isinstance(bands["high"], list)
            assert isinstance(bands["medium"], list)
            assert isinstance(bands["low"], list)


@pytest.mark.skipif(not LANGSMITH_AVAILABLE, reason="LangSmith not installed")
class TestLangSmithExtractorSaveDatasetWithDomains:
    """Tests for save_dataset with domain collection."""

    @pytest.fixture
    def extractor(self):
        """Create extractor with mocked client."""
        from app.evaluation.ingestion.langsmith_extractor import LangSmithExtractor

        with patch("app.evaluation.ingestion.langsmith_extractor.Client") as mock_client:
            mock_client.return_value = MagicMock()
            extractor = LangSmithExtractor()
            return extractor

    def test_save_dataset_collects_domains(self, extractor, tmp_path):
        """Test that save_dataset collects domains from examples."""
        examples = [
            {
                "id": "test-001",
                "inputs": {"content": "Test", "agent_type": "security_auditor"},
                "expected_outputs": {"primary": {}},
                "evaluation_criteria": {},
                "provenance": {"source": "langsmith"},
                "validation": {"status": "draft"},
                "metadata": {"difficulty": "medium", "domain": "security"},
            },
            {
                "id": "test-002",
                "inputs": {"content": "Test 2", "agent_type": "tech_comparator"},
                "expected_outputs": {"primary": {}},
                "evaluation_criteria": {},
                "provenance": {"source": "langsmith"},
                "validation": {"status": "draft"},
                "metadata": {"difficulty": "medium", "domain": "backend"},
            },
        ]

        output_path = tmp_path / "output.json"
        extractor.save_dataset(examples, str(output_path), dataset_name="test_domains")

        with output_path.open() as f:
            dataset = json.load(f)

        assert "domains" in dataset["metadata"]
        assert "security" in dataset["metadata"]["domains"]
        assert "backend" in dataset["metadata"]["domains"]
        assert len(dataset["metadata"]["domains"]) == 2

    def test_save_dataset_empty_domains_when_missing(self, extractor, tmp_path):
        """Test save_dataset handles examples without domains."""
        examples = [
            {
                "id": "test-001",
                "inputs": {"content": "Test", "agent_type": "security_auditor"},
                "expected_outputs": {"primary": {}},
                "evaluation_criteria": {},
                "provenance": {"source": "langsmith"},
                "validation": {"status": "draft"},
                "metadata": {"difficulty": "medium"},  # No domain
            },
        ]

        output_path = tmp_path / "output.json"
        extractor.save_dataset(examples, str(output_path))

        with output_path.open() as f:
            dataset = json.load(f)

        assert "domains" in dataset["metadata"]
        assert dataset["metadata"]["domains"] == []

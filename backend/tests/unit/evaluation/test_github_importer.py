"""Unit tests for GitHub Issue Importer.

Tests cover:
- GitHubImportConfig dataclass
- GitHubIssue dataclass
- Agent type inference
- Domain inference
- Difficulty estimation
- Issue to example conversion
- Dataset saving
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.evaluation.ingestion.github_importer import (
    AGENT_KEYWORDS,
    LABEL_TO_AGENT,
    REPO_DOMAIN_MAP,
    GitHubImportConfig,
    GitHubImporter,
    GitHubIssue,
)


class TestGitHubImportConfig:
    """Tests for GitHubImportConfig dataclass."""

    def test_config_defaults(self):
        """Test GitHubImportConfig has correct defaults."""
        config = GitHubImportConfig(owner="test-owner", repo="test-repo")

        assert config.owner == "test-owner"
        assert config.repo == "test-repo"
        assert config.min_reactions == 5
        assert config.state == "closed"
        assert config.labels is None
        assert config.since is None
        assert config.limit == 50

    def test_config_custom_values(self):
        """Test GitHubImportConfig with custom values."""
        since_date = datetime(2025, 12, 1, tzinfo=UTC)
        config = GitHubImportConfig(
            owner="langchain-ai",
            repo="langchain",
            min_reactions=10,
            state="all",
            labels=["bug", "documentation"],
            since=since_date,
            limit=100,
        )

        assert config.owner == "langchain-ai"
        assert config.repo == "langchain"
        assert config.min_reactions == 10
        assert config.state == "all"
        assert config.labels == ["bug", "documentation"]
        assert config.since == since_date
        assert config.limit == 100


class TestGitHubIssue:
    """Tests for GitHubIssue dataclass."""

    def test_issue_creation(self):
        """Test GitHubIssue creation with all fields."""
        created = datetime(2025, 12, 1, tzinfo=UTC)
        closed = datetime(2025, 12, 5, tzinfo=UTC)

        issue = GitHubIssue(
            number=123,
            title="Test Issue",
            body="This is a test issue body",
            labels=["bug", "high-priority"],
            state="closed",
            reactions_count=15,
            comments_count=8,
            created_at=created,
            closed_at=closed,
            html_url="https://github.com/owner/repo/issues/123",
        )

        assert issue.number == 123
        assert issue.title == "Test Issue"
        assert issue.body == "This is a test issue body"
        assert issue.labels == ["bug", "high-priority"]
        assert issue.state == "closed"
        assert issue.reactions_count == 15
        assert issue.comments_count == 8
        assert issue.created_at == created
        assert issue.closed_at == closed
        assert issue.html_url == "https://github.com/owner/repo/issues/123"

    def test_issue_open_no_closed_at(self):
        """Test open issue with no closed_at date."""
        issue = GitHubIssue(
            number=456,
            title="Open Issue",
            body="Still open",
            labels=[],
            state="open",
            reactions_count=5,
            comments_count=2,
            created_at=datetime.now(UTC),
            closed_at=None,
            html_url="https://github.com/owner/repo/issues/456",
        )

        assert issue.state == "open"
        assert issue.closed_at is None


class TestGitHubImporterAgentInference:
    """Tests for agent type inference."""

    @pytest.fixture
    def importer(self):
        """Create importer with mocked dependencies."""
        with patch.object(GitHubImporter, "__init__", lambda x, **kwargs: None):
            importer = GitHubImporter.__new__(GitHubImporter)
            importer.anonymizer = MagicMock()
            importer.anonymizer.anonymize.return_value = MagicMock(text="anonymized", has_pii=False)
            return importer

    @pytest.fixture
    def base_issue(self):
        """Create base issue for testing."""
        return GitHubIssue(
            number=1,
            title="",
            body="",
            labels=[],
            state="closed",
            reactions_count=10,
            comments_count=5,
            created_at=datetime.now(UTC),
            closed_at=None,
            html_url="https://github.com/owner/repo/issues/1",
        )

    def test_infer_agents_from_security_keywords(self, importer, base_issue):
        """Test security agent inference from keywords."""
        base_issue.title = "Security vulnerability in authentication"
        base_issue.body = "Found XSS injection in login form"

        agents = importer._infer_agents(base_issue)

        assert "security_auditor" in agents

    def test_infer_agents_from_performance_keywords(self, importer, base_issue):
        """Test performance agent inference from keywords."""
        base_issue.title = "Slow response times"
        base_issue.body = "Memory usage is high and latency is bad"

        agents = importer._infer_agents(base_issue)

        assert "performance_analyst" in agents

    def test_infer_agents_from_comparison_keywords(self, importer, base_issue):
        """Test tech_comparator inference from comparison keywords."""
        base_issue.title = "React vs Vue comparison"
        base_issue.body = "Looking to migrate from Vue to React"

        agents = importer._infer_agents(base_issue)

        assert "tech_comparator" in agents

    def test_infer_agents_from_labels(self, importer, base_issue):
        """Test agent inference from labels."""
        base_issue.labels = ["security", "bug"]

        agents = importer._infer_agents(base_issue)

        assert "security_auditor" in agents
        assert "code_quality_critic" in agents

    def test_infer_agents_default(self, importer, base_issue):
        """Test default agent when no keywords match."""
        base_issue.title = "Random issue"
        base_issue.body = "Nothing specific here"
        base_issue.labels = []

        agents = importer._infer_agents(base_issue)

        assert "implementation_planner" in agents

    def test_infer_multiple_agents(self, importer, base_issue):
        """Test inference of multiple agents."""
        base_issue.title = "Security and performance optimization"
        base_issue.body = "Need to fix vulnerability and improve speed"

        agents = importer._infer_agents(base_issue)

        assert "security_auditor" in agents
        assert "performance_analyst" in agents


class TestGitHubImporterDomainInference:
    """Tests for domain inference."""

    @pytest.fixture
    def importer(self):
        """Create importer for testing."""
        with patch.object(GitHubImporter, "__init__", lambda x, **kwargs: None):
            return GitHubImporter.__new__(GitHubImporter)

    @pytest.fixture
    def base_issue(self):
        """Create base issue for testing."""
        return GitHubIssue(
            number=1,
            title="Test",
            body="Test body",
            labels=[],
            state="closed",
            reactions_count=10,
            comments_count=5,
            created_at=datetime.now(UTC),
            closed_at=None,
            html_url="https://github.com/owner/repo/issues/1",
        )

    def test_infer_domain_from_repo(self, importer, base_issue):
        """Test domain inference from repository name."""
        domain = importer._infer_domain(base_issue, "langchain")
        assert domain == "llm-orchestration"

        domain = importer._infer_domain(base_issue, "fastapi")
        assert domain == "backend"

        domain = importer._infer_domain(base_issue, "react")
        assert domain == "frontend"

    def test_infer_domain_from_labels(self, importer, base_issue):
        """Test domain inference from labels."""
        base_issue.labels = ["database", "sql"]
        domain = importer._infer_domain(base_issue, "unknown-repo")
        assert domain == "data-layer"

    def test_infer_domain_from_content(self, importer, base_issue):
        """Test domain inference from content."""
        base_issue.title = "Kubernetes deployment issue"
        base_issue.body = "Docker container not starting"
        domain = importer._infer_domain(base_issue, "unknown-repo")
        assert domain == "devops"

    def test_infer_domain_default(self, importer, base_issue):
        """Test default domain when nothing matches."""
        base_issue.title = "Random issue"
        base_issue.body = "Nothing specific"
        domain = importer._infer_domain(base_issue, "unknown-repo")
        assert domain == "general"


class TestGitHubImporterDifficultyEstimation:
    """Tests for difficulty estimation."""

    @pytest.fixture
    def importer(self):
        """Create importer for testing."""
        with patch.object(GitHubImporter, "__init__", lambda x, **kwargs: None):
            return GitHubImporter.__new__(GitHubImporter)

    @pytest.fixture
    def base_issue(self):
        """Create base issue for testing."""
        return GitHubIssue(
            number=1,
            title="Test",
            body="",
            labels=[],
            state="closed",
            reactions_count=10,
            comments_count=0,
            created_at=datetime.now(UTC),
            closed_at=None,
            html_url="https://github.com/owner/repo/issues/1",
        )

    def test_easy_difficulty(self, importer, base_issue):
        """Test easy difficulty for simple issues."""
        base_issue.body = "Short issue"
        base_issue.comments_count = 0

        difficulty = importer._estimate_difficulty(base_issue)

        assert difficulty == "easy"

    def test_medium_difficulty(self, importer, base_issue):
        """Test medium difficulty for moderately complex issues."""
        base_issue.body = "x" * 600  # Medium length
        base_issue.comments_count = 3

        difficulty = importer._estimate_difficulty(base_issue)

        assert difficulty == "medium"

    def test_hard_difficulty(self, importer, base_issue):
        """Test hard difficulty for complex issues."""
        base_issue.body = "x" * 2500 + "```python\ncode here\n```"
        base_issue.comments_count = 8

        difficulty = importer._estimate_difficulty(base_issue)

        assert difficulty in ["hard", "expert"]

    def test_expert_difficulty(self, importer, base_issue):
        """Test expert difficulty for very complex issues."""
        base_issue.body = "x" * 3000 + "```\ncode\n```"
        base_issue.comments_count = 15

        difficulty = importer._estimate_difficulty(base_issue)

        assert difficulty == "expert"


class TestGitHubImporterConversion:
    """Tests for issue to example conversion."""

    @pytest.fixture
    def importer(self):
        """Create importer with mocked anonymizer."""
        with patch.object(GitHubImporter, "__init__", lambda x, **kwargs: None):
            importer = GitHubImporter.__new__(GitHubImporter)
            importer.anonymizer = MagicMock()
            importer.anonymizer.anonymize.return_value = MagicMock(
                text="anonymized_content", has_pii=True
            )
            return importer

    @pytest.fixture
    def sample_issue(self):
        """Create sample issue for conversion testing."""
        return GitHubIssue(
            number=789,
            title="Performance optimization needed",
            body="The API is slow when handling large requests. Need to optimize.",
            labels=["performance", "enhancement"],
            state="closed",
            reactions_count=20,
            comments_count=10,
            created_at=datetime(2025, 12, 1, tzinfo=UTC),
            closed_at=datetime(2025, 12, 5, tzinfo=UTC),
            html_url="https://github.com/langchain-ai/langchain/issues/789",
        )

    def test_convert_to_example(self, importer, sample_issue):
        """Test converting issue to v2.0 example format."""
        config = GitHubImportConfig(owner="langchain-ai", repo="langchain")
        example = importer._convert_to_example(sample_issue, config)

        # Check ID format
        assert example["id"] == "gh-langchain-ai-langchain-789"

        # Check inputs
        assert "content" in example["inputs"]
        assert example["inputs"]["content_type"] == "github_issue"
        assert "agent_type" in example["inputs"]

        # Check expected outputs
        assert "primary" in example["expected_outputs"]
        assert "acceptable_alternatives" in example["expected_outputs"]

        # Check evaluation criteria
        assert "scoring_rubric" in example["evaluation_criteria"]
        rubric = example["evaluation_criteria"]["scoring_rubric"]
        assert rubric["correctness"]["weight"] == 0.5
        assert rubric["completeness"]["weight"] == 0.3
        assert rubric["quality"]["weight"] == 0.2

        # Check provenance
        assert example["provenance"]["source"] == "github"
        assert example["provenance"]["github_issue_url"] == sample_issue.html_url
        assert example["provenance"]["github_owner"] == "langchain-ai"
        assert example["provenance"]["github_repo"] == "langchain"
        assert example["provenance"]["github_issue_number"] == 789

        # Check validation
        assert example["validation"]["status"] == "draft"

        # Check metadata
        assert "difficulty" in example["metadata"]
        assert example["metadata"]["pii_anonymized"] is True
        assert "tags" in example["metadata"]


class TestGitHubImporterSaveDataset:
    """Tests for dataset saving functionality."""

    @pytest.fixture
    def importer(self):
        """Create importer for testing."""
        with patch.object(GitHubImporter, "__init__", lambda x, **kwargs: None):
            return GitHubImporter.__new__(GitHubImporter)

    def test_save_dataset(self, importer, tmp_path):
        """Test saving examples as dataset."""
        examples = [
            {
                "id": "test-001",
                "inputs": {"content": "Test", "agent_type": "security_auditor"},
                "expected_outputs": {"primary": {"domain": "security"}},
            },
            {
                "id": "test-002",
                "inputs": {"content": "Test 2", "agent_type": "tech_comparator"},
                "expected_outputs": {"primary": {"domain": "frontend"}},
            },
        ]

        output_path = tmp_path / "test_dataset.json"
        importer.save_dataset(examples, output_path, dataset_name="test_github")

        assert output_path.exists()

        with output_path.open() as f:
            dataset = json.load(f)

        assert dataset["version"] == "2.0.0"
        assert dataset["metadata"]["dataset_name"] == "test_github"
        assert dataset["metadata"]["task_type"] == "agent"
        assert len(dataset["examples"]) == 2

        # Check that agent types and domains were collected
        assert "security_auditor" in dataset["metadata"]["agent_types"]
        assert "tech_comparator" in dataset["metadata"]["agent_types"]

    def test_save_dataset_creates_directory(self, importer, tmp_path):
        """Test that save_dataset creates parent directories."""
        output_path = tmp_path / "subdir" / "nested" / "dataset.json"
        importer.save_dataset([], output_path)

        assert output_path.exists()


class TestGitHubImporterInit:
    """Tests for GitHubImporter initialization."""

    def test_init_with_token_env(self):
        """Test initialization with GITHUB_TOKEN environment variable."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test_token"}):
            importer = GitHubImporter()

            assert importer.api_token == "ghp_test_token"
            assert "Authorization" in importer.headers
            assert importer.headers["Authorization"] == "Bearer ghp_test_token"

    def test_init_with_explicit_token(self):
        """Test initialization with explicit token parameter."""
        importer = GitHubImporter(api_token="ghp_explicit_token")

        assert importer.api_token == "ghp_explicit_token"
        assert importer.headers["Authorization"] == "Bearer ghp_explicit_token"

    def test_init_without_token(self):
        """Test initialization without token."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove GITHUB_TOKEN if it exists
            import os

            os.environ.pop("GITHUB_TOKEN", None)

            importer = GitHubImporter(api_token=None)

            assert importer.api_token is None
            assert "Authorization" not in importer.headers


class TestAgentKeywordsConsistency:
    """Tests for agent keyword and label mapping consistency."""

    def test_all_agents_have_keywords(self):
        """Test that all expected agents have keyword mappings."""
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

        assert set(AGENT_KEYWORDS.keys()) == expected_agents

    def test_label_agents_are_valid(self):
        """Test that label-mapped agents are in the keywords dict."""
        for label, agent in LABEL_TO_AGENT.items():
            assert agent in AGENT_KEYWORDS, (
                f"Agent '{agent}' for label '{label}' not in AGENT_KEYWORDS"
            )

    def test_repo_domains_are_strings(self):
        """Test that all repo domain mappings are strings."""
        for repo, domain in REPO_DOMAIN_MAP.items():
            assert isinstance(repo, str)
            assert isinstance(domain, str)
            assert len(domain) > 0

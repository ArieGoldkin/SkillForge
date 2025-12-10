"""GitHub Issue Importer for evaluation dataset ingestion.

This module provides functionality to import high-quality issues from
GitHub repositories and convert them to v2.0 evaluation dataset format.

Features:
- Rate-limited API access (respects GitHub's 5000 req/hour limit)
- Agent type inference from issue content and labels
- Domain inference from repository and labels
- Difficulty estimation based on content complexity
- PII anonymization integration

Example:
    >>> from app.evaluation.ingestion import GitHubImporter, GitHubImportConfig
    >>> config = GitHubImportConfig(owner="langchain-ai", repo="langchain")
    >>> importer = GitHubImporter()
    >>> examples = importer.import_issues(config)

"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.evaluation.ingestion.pii_anonymizer import PIIAnonymizer, get_anonymizer
from app.services.backpressure.rate_limiter import RateLimiter

logger = get_logger(__name__)

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

# Rate limiting: GitHub allows 5000 requests/hour with token, 60/hour without
# Use conservative rate of 4000/hour = ~67/minute
GITHUB_RATE_LIMITER = RateLimiter(
    tokens_per_minute=67,
    burst_capacity=20,
    name="github_api",
)

# Agent inference keywords
AGENT_KEYWORDS: dict[str, list[str]] = {
    "tech_comparator": [
        "alternative",
        "vs",
        "versus",
        "compare",
        "comparison",
        "migrate",
        "migration",
        "upgrade",
        "switch",
        "replace",
    ],
    "security_auditor": [
        "security",
        "vulnerability",
        "vuln",
        "cve",
        "auth",
        "authentication",
        "authorization",
        "injection",
        "xss",
        "csrf",
        "exploit",
    ],
    "implementation_planner": [
        "how to",
        "tutorial",
        "guide",
        "example",
        "setup",
        "getting started",
        "documentation",
        "docs",
        "walkthrough",
    ],
    "performance_analyst": [
        "performance",
        "slow",
        "fast",
        "memory",
        "latency",
        "benchmark",
        "optimization",
        "optimize",
        "speed",
        "bottleneck",
    ],
    "code_quality_critic": [
        "best practice",
        "antipattern",
        "refactor",
        "clean",
        "code smell",
        "maintainability",
        "readability",
        "technical debt",
    ],
    "dependency_mapper": [
        "dependency",
        "dependencies",
        "import",
        "package",
        "version",
        "conflict",
        "incompatible",
        "requirements",
    ],
    "trend_validator": [
        "deprecated",
        "legacy",
        "modern",
        "2025",
        "2024",
        "latest",
        "adoption",
        "trend",
        "outdated",
    ],
    "integration_feasibility": [
        "integration",
        "integrate",
        "connect",
        "api",
        "service",
        "third-party",
        "external",
        "webhook",
    ],
}

# Label to agent mapping
LABEL_TO_AGENT: dict[str, str] = {
    "security": "security_auditor",
    "performance": "performance_analyst",
    "documentation": "implementation_planner",
    "docs": "implementation_planner",
    "bug": "code_quality_critic",
    "enhancement": "tech_comparator",
    "feature": "tech_comparator",
    "dependencies": "dependency_mapper",
    "breaking-change": "trend_validator",
}

# Repository to domain mapping
REPO_DOMAIN_MAP: dict[str, str] = {
    "langchain": "llm-orchestration",
    "langgraph": "agent-systems",
    "fastapi": "backend",
    "react": "frontend",
    "nextjs": "frontend",
    "next.js": "frontend",
    "pytorch": "machine-learning",
    "tensorflow": "machine-learning",
    "kubernetes": "devops",
    "docker": "devops",
}

# Keyword to domain mapping
KEYWORD_DOMAIN_MAP: dict[str, str] = {
    "api": "backend",
    "rest": "backend",
    "graphql": "backend",
    "database": "data-layer",
    "sql": "data-layer",
    "postgresql": "data-layer",
    "mongodb": "data-layer",
    "frontend": "frontend",
    "react": "frontend",
    "vue": "frontend",
    "css": "frontend",
    "ml": "machine-learning",
    "model": "machine-learning",
    "training": "machine-learning",
    "deploy": "devops",
    "ci/cd": "devops",
    "docker": "devops",
    "kubernetes": "devops",
    "security": "security",
    "auth": "security",
    "llm": "llm-orchestration",
    "langchain": "llm-orchestration",
    "agent": "agent-systems",
    "workflow": "agent-systems",
}


@dataclass
class GitHubImportConfig:
    """Configuration for GitHub issue import.

    Attributes:
        owner: GitHub repository owner (user or org)
        repo: Repository name
        min_reactions: Minimum total reactions for quality filtering
        state: Issue state filter (open, closed, all)
        labels: Optional label filter
        since: Only import issues updated after this date
        limit: Maximum number of issues to import

    """

    owner: str
    repo: str
    min_reactions: int = 5
    state: Literal["open", "closed", "all"] = "closed"
    labels: list[str] | None = None
    since: datetime | None = None
    limit: int = 50


@dataclass
class GitHubIssue:
    """Parsed GitHub issue data.

    Attributes:
        number: Issue number
        title: Issue title
        body: Issue body (markdown)
        labels: List of label names
        state: Issue state
        reactions_count: Total reaction count
        comments_count: Number of comments
        created_at: Creation timestamp
        closed_at: Close timestamp (if closed)
        html_url: URL to issue on GitHub

    """

    number: int
    title: str
    body: str
    labels: list[str]
    state: str
    reactions_count: int
    comments_count: int
    created_at: datetime
    closed_at: datetime | None
    html_url: str


class GitHubImporter:
    """Imports GitHub issues and converts to evaluation dataset format.

    Uses the GitHub REST API with rate limiting and retry logic.
    Infers agent types and domains from issue content.

    Example:
        >>> importer = GitHubImporter()
        >>> config = GitHubImportConfig(owner="langchain-ai", repo="langchain")
        >>> examples = importer.import_issues(config)
        >>> importer.save_dataset(examples, "langchain_issues.json")

    """

    def __init__(
        self,
        api_token: str | None = None,
        anonymizer: PIIAnonymizer | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize the GitHub importer.

        Args:
            api_token: GitHub API token (or GITHUB_TOKEN env var)
            anonymizer: PII anonymizer instance (default: auto-create)
            rate_limiter: Rate limiter instance (default: module-level)

        """
        self.api_token = api_token or os.environ.get("GITHUB_TOKEN")
        self.anonymizer = anonymizer or get_anonymizer()
        self.rate_limiter = rate_limiter or GITHUB_RATE_LIMITER

        # Build headers
        self.headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"

        logger.info(
            "github_importer_initialized",
            has_token=bool(self.api_token),
            rate_limit=self.rate_limiter.tokens_per_minute,
        )

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
    )
    async def _fetch_issues(
        self,
        config: GitHubImportConfig,
    ) -> list[GitHubIssue]:
        """Fetch issues from GitHub API.

        Args:
            config: Import configuration

        Returns:
            List of parsed GitHub issues

        """
        issues: list[GitHubIssue] = []
        page = 1
        per_page = min(100, config.limit)

        async with httpx.AsyncClient(timeout=30.0) as client:
            while len(issues) < config.limit:
                # Rate limit
                await self.rate_limiter.acquire_async(tokens=1)

                # Build URL and params
                url = f"{GITHUB_API_BASE}/repos/{config.owner}/{config.repo}/issues"
                params: dict[str, Any] = {
                    "state": config.state,
                    "sort": "reactions",
                    "direction": "desc",
                    "per_page": per_page,
                    "page": page,
                }

                if config.labels:
                    params["labels"] = ",".join(config.labels)
                if config.since:
                    params["since"] = config.since.isoformat()

                logger.debug(
                    "github_api_request",
                    url=url,
                    page=page,
                    params=params,
                )

                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()
                if not data:
                    break  # No more issues

                for item in data:
                    # Skip pull requests (they appear in issues endpoint)
                    if "pull_request" in item:
                        continue

                    # Parse reactions
                    reactions = item.get("reactions", {})
                    total_reactions = reactions.get("total_count", 0)

                    # Filter by reactions threshold
                    if total_reactions < config.min_reactions:
                        continue

                    # Parse issue
                    issue = GitHubIssue(
                        number=item["number"],
                        title=item["title"],
                        body=item.get("body") or "",
                        labels=[label["name"] for label in item.get("labels", [])],
                        state=item["state"],
                        reactions_count=total_reactions,
                        comments_count=item.get("comments", 0),
                        created_at=datetime.fromisoformat(
                            item["created_at"].replace("Z", "+00:00")
                        ),
                        closed_at=(
                            datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00"))
                            if item.get("closed_at")
                            else None
                        ),
                        html_url=item["html_url"],
                    )
                    issues.append(issue)

                    if len(issues) >= config.limit:
                        break

                page += 1

                # Check for pagination
                link_header = response.headers.get("Link", "")
                if 'rel="next"' not in link_header:
                    break

        logger.info(
            "github_issues_fetched",
            owner=config.owner,
            repo=config.repo,
            count=len(issues),
        )

        return issues

    def _infer_agents(self, issue: GitHubIssue) -> list[str]:
        """Infer relevant agent types from issue content.

        Args:
            issue: GitHub issue to analyze

        Returns:
            List of inferred agent type names

        """
        agents: set[str] = set()
        content = f"{issue.title} {issue.body}".lower()

        # Check labels first (higher confidence)
        for label in issue.labels:
            label_lower = label.lower()
            if label_lower in LABEL_TO_AGENT:
                agents.add(LABEL_TO_AGENT[label_lower])

        # Check keyword patterns
        for agent, keywords in AGENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    agents.add(agent)
                    break  # One match per agent is enough

        # Default to implementation_planner if no agents found
        if not agents:
            agents.add("implementation_planner")

        return list(agents)

    def _infer_domain(self, issue: GitHubIssue, repo: str) -> str:
        """Infer technical domain from issue and repository.

        Args:
            issue: GitHub issue to analyze
            repo: Repository name

        Returns:
            Inferred domain name

        """
        # First check repository
        repo_lower = repo.lower()
        if repo_lower in REPO_DOMAIN_MAP:
            return REPO_DOMAIN_MAP[repo_lower]

        # Check labels
        for label in issue.labels:
            label_lower = label.lower()
            for keyword, domain in KEYWORD_DOMAIN_MAP.items():
                if keyword in label_lower:
                    return domain

        # Check content
        content = f"{issue.title} {issue.body}".lower()
        for keyword, domain in KEYWORD_DOMAIN_MAP.items():
            if keyword in content:
                return domain

        # Default domain
        return "general"

    def _estimate_difficulty(self, issue: GitHubIssue) -> str:
        """Estimate issue difficulty based on content complexity.

        Args:
            issue: GitHub issue to analyze

        Returns:
            Difficulty level: easy, medium, hard, expert

        """
        content_length = len(issue.body)
        has_code = "```" in issue.body
        comments = issue.comments_count

        # Score based on multiple factors
        score = 0

        # Content length
        if content_length > 2000:
            score += 2
        elif content_length > 500:
            score += 1

        # Code blocks indicate technical depth
        if has_code:
            score += 1

        # Many comments indicate complexity
        if comments > 10:
            score += 2
        elif comments > 5:
            score += 1

        # Map score to difficulty
        if score >= 4:
            return "expert"
        elif score >= 3:
            return "hard"
        elif score >= 1:
            return "medium"
        else:
            return "easy"

    def _convert_to_example(
        self,
        issue: GitHubIssue,
        config: GitHubImportConfig,
    ) -> dict[str, Any]:
        """Convert GitHub issue to v2.0 evaluation example.

        Args:
            issue: Parsed GitHub issue
            config: Import configuration

        Returns:
            Evaluation example in v2.0 schema format

        """
        # Infer metadata
        agents = self._infer_agents(issue)
        domain = self._infer_domain(issue, config.repo)
        difficulty = self._estimate_difficulty(issue)

        # Anonymize content
        title_result = self.anonymizer.anonymize(issue.title)
        body_result = self.anonymizer.anonymize(issue.body)

        # Build example
        example: dict[str, Any] = {
            "id": f"gh-{config.owner}-{config.repo}-{issue.number}",
            "inputs": {
                "content": f"# {title_result.text}\n\n{body_result.text}",
                "content_type": "github_issue",
                "agent_type": agents[0] if agents else "implementation_planner",
            },
            "expected_outputs": {
                "primary": {
                    # Expected output depends on agent type
                    "agent_type": agents[0] if agents else "implementation_planner",
                    "domain": domain,
                    # Actual expected outputs would come from manual review
                },
                "acceptable_alternatives": [],
                "forbidden_outputs": [],
            },
            "evaluation_criteria": {
                "scoring_rubric": {
                    "correctness": {
                        "weight": 0.5,
                        "thresholds": {
                            "perfect": 1.0,
                            "acceptable": 0.7,
                            "failing": 0.5,
                        },
                        "description": "Agent correctly identifies key issues and solutions",
                    },
                    "completeness": {
                        "weight": 0.3,
                        "required_fields": ["summary", "recommendations"],
                    },
                    "quality": {
                        "weight": 0.2,
                        "min_length": 100,
                        "max_length": 2000,
                    },
                },
                "custom_evaluators": [],
            },
            "provenance": {
                "source": "github",
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": "github_importer",
                "github_issue_url": issue.html_url,
                "github_owner": config.owner,
                "github_repo": config.repo,
                "github_issue_number": issue.number,
                "original_created_at": issue.created_at.isoformat(),
            },
            "validation": {
                "status": "draft",
                "validated_by": [],
            },
            "metadata": {
                "difficulty": difficulty,
                "edge_case": False,
                "adversarial": False,
                "tags": [
                    f"repo:{config.repo}",
                    f"domain:{domain}",
                    *[f"agent:{a}" for a in agents],
                    *[f"label:{label}" for label in issue.labels[:5]],
                ],
                "github_reactions": issue.reactions_count,
                "github_comments": issue.comments_count,
                "pii_anonymized": title_result.has_pii or body_result.has_pii,
            },
        }

        return example

    async def import_issues(
        self,
        config: GitHubImportConfig,
    ) -> list[dict[str, Any]]:
        """Import issues from GitHub and convert to evaluation examples.

        Args:
            config: Import configuration

        Returns:
            List of evaluation examples in v2.0 schema format

        """
        issues = await self._fetch_issues(config)
        examples = [self._convert_to_example(issue, config) for issue in issues]

        logger.info(
            "github_import_complete",
            owner=config.owner,
            repo=config.repo,
            issues_fetched=len(issues),
            examples_created=len(examples),
        )

        return examples

    def save_dataset(
        self,
        examples: list[dict[str, Any]],
        output_path: str | Path,
        dataset_name: str | None = None,
    ) -> None:
        """Save extracted examples as v2.0 dataset.

        Args:
            examples: List of evaluation examples
            output_path: Path to output JSON file
            dataset_name: Dataset name for metadata

        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Collect unique values for metadata
        agent_types = set()
        domains = set()
        for ex in examples:
            if "agent_type" in ex.get("inputs", {}):
                agent_types.add(ex["inputs"]["agent_type"])
            if "domain" in ex.get("expected_outputs", {}).get("primary", {}):
                domains.add(ex["expected_outputs"]["primary"]["domain"])

        dataset = {
            "version": "2.0.0",
            "metadata": {
                "dataset_name": dataset_name or output_path.stem,
                "task_type": "agent",
                "agent_types": list(agent_types),
                "domains": list(domains),
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "release_tag": "v2.0.0-draft",
                "description": "GitHub issues imported from repositories",
                "maintainers": ["github_importer"],
            },
            "examples": examples,
        }

        with open(output_path, "w") as f:
            json.dump(dataset, f, indent=2, default=str)

        logger.info(
            "github_dataset_saved",
            path=str(output_path),
            example_count=len(examples),
        )

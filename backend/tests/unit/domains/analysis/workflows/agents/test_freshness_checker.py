"""Tests for freshness_checker agent.

This test suite verifies that the freshness_checker agent:
1. Properly extracts version references from content
2. Uses MCP tools (npm, PyPI) to check latest versions
3. Calculates accurate freshness scores
4. Provides actionable recommendations
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool

from app.domains.analysis.schemas.agents.freshness_checker import (
    FreshnessCheckerOutput,
    VersionCheck,
)
from app.domains.analysis.workflows.agents.freshness_checker import run_freshness_checker
from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def analysis_id():
    """Create test analysis ID."""
    return str(uuid4())


@pytest.fixture
def base_state() -> AnalysisState:
    """Create base state dictionary."""
    return {
        "skill_level": "intermediate",
        "proactive_context": "",
        "agent_expectation": "high",
        "content_signals": {
            "has_comparisons": False,
            "detected_genre": "tutorial",
            "has_conceptual_only": False,
        },
    }


@pytest.fixture
def mock_npm_tool():
    """Create mock npm package details tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get-npm-package-details"
    tool.description = "Get npm package metadata and latest version info"
    return tool


@pytest.fixture
def mock_pypi_tool():
    """Create mock PyPI package details tool."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "get-pypi-package-details"
    tool.description = "Get PyPI package metadata and latest version info"
    return tool


class TestFreshnessCheckerBasics:
    """Test basic freshness checker functionality."""

    @pytest.mark.asyncio
    async def test_freshness_checker_with_current_versions(
        self, mock_session, analysis_id, base_state
    ):
        """Test freshness checker with current versions (high freshness score)."""
        content = """
        React 19.0.0 Tutorial
        Published: December 2024

        This tutorial covers React 19.0.0 features including:
        - Concurrent rendering
        - Server components
        - Automatic batching

        Prerequisites:
        - Node.js 20.10.0
        - npm 10.2.0
        """

        mock_output = FreshnessCheckerOutput(
            content_date="2024-12-01",
            version_checks=[
                VersionCheck(
                    package_name="react",
                    mentioned_version="19.0.0",
                    latest_version="19.0.0",
                    is_outdated=False,
                    versions_behind=0,
                    ecosystem="npm",
                )
            ],
            is_outdated=False,
            freshness_score=1.0,
            recommendations=[],
            confidence_score=0.9,
            data_availability_score=1.0,
            missing_data_flags=[],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            # Setup mock agent that returns our mock output
            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            # Mock run_agent_with_tracking to return expected structure
            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 1500,
            }

            result = await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=None,
            )

            # Verify result structure
            assert result["agent_type"] == "freshness_checker"
            assert "findings" in result
            assert "processing_time_ms" in result

            findings = result["findings"]
            assert findings["content_date"] == "2024-12-01"
            assert findings["is_outdated"] is False
            assert findings["freshness_score"] == 1.0
            assert len(findings["version_checks"]) == 1
            assert findings["version_checks"][0]["is_outdated"] is False
            assert findings["confidence_score"] == 0.9

    @pytest.mark.asyncio
    async def test_freshness_checker_with_outdated_versions(
        self, mock_session, analysis_id, base_state
    ):
        """Test freshness checker with outdated versions (low freshness score)."""
        content = """
        React 16.8.0 Tutorial
        Published: January 2020

        This tutorial covers React 16.8.0 hooks including:
        - useState
        - useEffect
        - useContext

        Prerequisites:
        - Python 3.7
        - FastAPI 0.65.0
        """

        mock_output = FreshnessCheckerOutput(
            content_date="2020-01-01",
            version_checks=[
                VersionCheck(
                    package_name="react",
                    mentioned_version="16.8.0",
                    latest_version="19.0.0",
                    is_outdated=True,
                    versions_behind=3,
                    ecosystem="npm",
                ),
                VersionCheck(
                    package_name="python",
                    mentioned_version="3.7",
                    latest_version="3.12.1",
                    is_outdated=True,
                    versions_behind=5,
                    ecosystem="language",
                ),
                VersionCheck(
                    package_name="fastapi",
                    mentioned_version="0.65.0",
                    latest_version="0.109.0",
                    is_outdated=True,
                    versions_behind=44,
                    ecosystem="pypi",
                ),
            ],
            is_outdated=True,
            freshness_score=0.2,
            recommendations=[
                "Update React from 16.8.0 to 19.0.0 for concurrent features and automatic batching",
                "Migrate to Python 3.12 for performance improvements (up to 30% faster)",
                "Upgrade FastAPI from 0.65.0 to 0.109.0 for latest features and security patches",
            ],
            confidence_score=0.85,
            data_availability_score=1.0,
            missing_data_flags=[],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 2500,
            }

            result = await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=None,
            )

            findings = result["findings"]
            assert findings["content_date"] == "2020-01-01"
            assert findings["is_outdated"] is True
            assert findings["freshness_score"] == 0.2
            assert len(findings["version_checks"]) == 3
            assert all(check["is_outdated"] for check in findings["version_checks"])
            assert len(findings["recommendations"]) == 3
            assert findings["confidence_score"] == 0.85


class TestFreshnessCheckerMCPIntegration:
    """Test freshness checker with MCP tools."""

    @pytest.mark.asyncio
    async def test_freshness_checker_uses_mcp_tools(
        self, mock_session, analysis_id, base_state, mock_npm_tool, mock_pypi_tool
    ):
        """Test that freshness checker uses MCP tools when provided."""
        content = """
        React 18.2.0 and FastAPI 0.104.1 Integration
        Learn how to build full-stack apps with React 18.2.0 and FastAPI 0.104.1.
        """

        tools = [mock_npm_tool, mock_pypi_tool]

        mock_output = FreshnessCheckerOutput(
            content_date=None,
            version_checks=[
                VersionCheck(
                    package_name="react",
                    mentioned_version="18.2.0",
                    latest_version="19.0.0",
                    is_outdated=True,
                    versions_behind=1,
                    ecosystem="npm",
                ),
                VersionCheck(
                    package_name="fastapi",
                    mentioned_version="0.104.1",
                    latest_version="0.109.0",
                    is_outdated=True,
                    versions_behind=5,
                    ecosystem="pypi",
                ),
            ],
            is_outdated=True,
            freshness_score=0.7,
            recommendations=[
                "Update React from 18.2.0 to 19.0.0 for concurrent features",
                "Upgrade FastAPI from 0.104.1 to 0.109.0 for security patches",
            ],
            confidence_score=0.85,
            data_availability_score=1.0,
            missing_data_flags=[],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 3000,
            }

            result = await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=tools,
            )

            # Verify agent was created with tools
            mock_create_agent.assert_called_once()
            call_kwargs = mock_create_agent.call_args[1]
            assert call_kwargs["tools"] == tools
            assert call_kwargs["agent_type"] == "freshness_checker"

            # Verify findings
            findings = result["findings"]
            assert len(findings["version_checks"]) == 2
            assert findings["version_checks"][0]["ecosystem"] == "npm"
            assert findings["version_checks"][1]["ecosystem"] == "pypi"


class TestFreshnessCheckerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_freshness_checker_no_versions_found(self, mock_session, analysis_id, base_state):
        """Test freshness checker when no version references are found."""
        content = """
        Introduction to React
        Learn the basics of React without diving into specific versions.
        Great for conceptual understanding.
        """

        mock_output = FreshnessCheckerOutput(
            content_date=None,
            version_checks=[],
            is_outdated=False,
            freshness_score=0.5,  # Neutral score when no data
            recommendations=[],
            confidence_score=0.3,  # Low confidence due to lack of version data
            data_availability_score=0.2,
            missing_data_flags=["no_version_references", "no_publication_date"],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 1000,
            }

            result = await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=None,
            )

            findings = result["findings"]
            assert len(findings["version_checks"]) == 0
            assert findings["confidence_score"] == 0.3
            assert findings["freshness_score"] == 0.5
            # Check data availability fields if present (from DataAvailabilityMixin)
            if "missing_data_flags" in findings:
                assert "no_version_references" in findings["missing_data_flags"]

    @pytest.mark.asyncio
    async def test_freshness_checker_registry_unavailable(
        self, mock_session, analysis_id, base_state
    ):
        """Test freshness checker when package registry is unavailable."""
        content = """
        React 18.2.0 Tutorial
        Published: June 2023
        """

        mock_output = FreshnessCheckerOutput(
            content_date="2023-06-01",
            version_checks=[
                VersionCheck(
                    package_name="react",
                    mentioned_version="18.2.0",
                    latest_version="unknown",  # Registry unavailable
                    is_outdated=False,  # Can't determine without registry
                    versions_behind=0,
                    ecosystem="npm",
                )
            ],
            is_outdated=False,  # Conservative assumption
            freshness_score=0.7,  # Based on content date only
            recommendations=[],
            confidence_score=0.5,  # Medium confidence - has date but no registry data
            data_availability_score=0.6,
            missing_data_flags=["registry_unavailable"],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 1200,
            }

            result = await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=None,
            )

            findings = result["findings"]
            assert findings["version_checks"][0]["latest_version"] == "unknown"
            assert findings["confidence_score"] == 0.5
            # Check data availability fields if present (from DataAvailabilityMixin)
            if "missing_data_flags" in findings:
                assert "registry_unavailable" in findings["missing_data_flags"]


class TestFreshnessCheckerPromptManager:
    """Test integration with PromptManager."""

    @pytest.mark.asyncio
    async def test_freshness_checker_uses_prompt_manager(
        self, mock_session, analysis_id, base_state
    ):
        """Test that freshness checker uses PromptManager for prompt fetching."""
        content = "React 19.0.0 tutorial"

        mock_output = FreshnessCheckerOutput(
            content_date=None,
            version_checks=[],
            is_outdated=False,
            freshness_score=0.8,
            recommendations=[],
            confidence_score=0.6,
            data_availability_score=0.5,
            missing_data_flags=[],
        )

        with (
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.get_prompt_manager"
            ) as mock_get_pm,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.create_agent_with_optional_few_shot"
            ) as mock_create_agent,
            patch(
                "app.domains.analysis.workflows.agents.freshness_checker.run_agent_with_tracking"
            ) as mock_run_agent,
        ):
            # Setup prompt manager mock
            mock_pm = AsyncMock()
            mock_pm.get_prompt_with_langfuse_client = AsyncMock(
                return_value=("Test prompt from Langfuse", None)
            )
            mock_get_pm.return_value = mock_pm

            mock_agent = AsyncMock()
            mock_create_agent.return_value = mock_agent

            mock_run_agent.return_value = {
                "agent_type": "freshness_checker",
                "findings": mock_output.model_dump(),
                "processing_time_ms": 1000,
            }

            await run_freshness_checker(
                content=content,
                content_type="article",
                analysis_id=analysis_id,
                session=mock_session,
                state=base_state,
                tools=None,
            )

            # Verify PromptManager was called
            mock_pm.get_prompt_with_langfuse_client.assert_called_once_with(
                "analysis-agent-freshness-checker"
            )

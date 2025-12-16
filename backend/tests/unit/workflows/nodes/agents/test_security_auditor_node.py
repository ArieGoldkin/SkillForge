"""Unit tests for security_auditor_node."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.nodes.agents.security_auditor_node import security_auditor_node
from app.domains.analysis.workflows.state import AnalysisState



@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample state for testing."""
    return {
        "analysis_id": str(uuid4()),
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Security best practices for API development.",
    }


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.nodes.agents.security_auditor_node.run_security_auditor_with_session")
async def test_security_auditor_node_success(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test security_auditor_node returns findings on success."""
    mock_runner.return_value = {
        "agent_type": "security_auditor",
        "findings": {"vulnerabilities": []},
        "processing_time_ms": 1000,
    }

    result = await security_auditor_node(sample_state)

    assert "agent_findings" in result
    assert len(result["agent_findings"]) == 1
    assert result["agent_findings"][0]["agent_type"] == "security_auditor"


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.nodes.agents.security_auditor_node.run_security_auditor_with_session")
async def test_security_auditor_node_handles_error(
    mock_runner: AsyncMock, sample_state: AnalysisState
) -> None:
    """Test security_auditor_node handles errors gracefully."""
    mock_runner.side_effect = Exception("Agent failed")

    result = await security_auditor_node(sample_state)

    assert "agent_findings" in result
    assert result["agent_findings"] == []

"""Unit tests for agent quality evaluator."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.workflows.evaluation.evaluator import evaluate_agent_quality
from app.domains.analysis.workflows.state import AnalysisState

# Expected embedding dimensions for OpenAI text-embedding-3-small
EXPECTED_EMBEDDING_DIMENSIONS = 1536


@pytest.fixture
def sample_state_with_findings() -> AnalysisState:
    """Sample state with agent findings."""
    return {
        "analysis_id": "test-analysis-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test content",
        "extraction_metadata": {},
        "content_embedding": [0.1] * EXPECTED_EMBEDDING_DIMENSIONS,
        "supervisor_decision": {"agents": ["tech_comparator"]},
        "agent_findings": [
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "primary_tech": "LangGraph",
                    "alternatives": ["LangChain"],
                },
                "confidence_score": 0.85,
            }
        ],
    }


@pytest.fixture
def sample_state_no_findings() -> AnalysisState:
    """Sample state without agent findings."""
    return {
        "analysis_id": "test-analysis-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test content",
        "extraction_metadata": {},
        "content_embedding": [0.1] * EXPECTED_EMBEDDING_DIMENSIONS,
        "supervisor_decision": {"agents": []},
        "agent_findings": [],
    }


@pytest.mark.asyncio
async def test_evaluate_agent_quality_with_findings(
    sample_state_with_findings: AnalysisState,
) -> None:
    """Test evaluator processes findings and calculates quality scores."""
    with patch(
        "app.domains.analysis.workflows.evaluation.evaluator.emit_streaming_event",
        new_callable=AsyncMock,
    ) as mock_emit:
        result = await evaluate_agent_quality(sample_state_with_findings)

        # Verify evaluation results added to state
        assert "evaluation_results" in result
        assert "tech_comparator" in result["evaluation_results"]

        # Verify quality score calculated
        eval_result = result["evaluation_results"]["tech_comparator"]
        assert "quality_score" in eval_result
        assert 0.0 <= eval_result["quality_score"] <= 1.0

        # Verify SSE event emitted
        assert mock_emit.called


@pytest.mark.asyncio
async def test_evaluate_agent_quality_no_findings(
    sample_state_no_findings: AnalysisState,
) -> None:
    """Test evaluator handles empty findings gracefully."""
    result = await evaluate_agent_quality(sample_state_no_findings)

    # Verify evaluation results is empty dict
    assert "evaluation_results" in result
    assert result["evaluation_results"] == {}


@pytest.mark.asyncio
async def test_evaluate_agent_quality_multiple_agents() -> None:
    """Test evaluator handles multiple agent findings."""
    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test",
        "extraction_metadata": {},
        "content_embedding": [0.1] * EXPECTED_EMBEDDING_DIMENSIONS,
        "supervisor_decision": {"agents": ["tech_comparator", "security_auditor"]},
        "agent_findings": [
            {
                "agent_type": "tech_comparator",
                "findings": {"primary_tech": "LangGraph"},
            },
            {
                "agent_type": "security_auditor",
                "findings": {"risks": []},
            },
        ],
    }

    with patch(
        "app.domains.analysis.workflows.evaluation.evaluator.emit_streaming_event",
        new_callable=AsyncMock,
    ):
        result = await evaluate_agent_quality(state)

        # Verify both agents evaluated
        assert "evaluation_results" in result
        assert "tech_comparator" in result["evaluation_results"]
        assert "security_auditor" in result["evaluation_results"]


@pytest.mark.asyncio
async def test_evaluate_agent_quality_error_handling() -> None:
    """Test evaluator handles errors gracefully."""
    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test",
        "extraction_metadata": {},
        "content_embedding": [0.1] * EXPECTED_EMBEDDING_DIMENSIONS,
        "supervisor_decision": {"agents": []},
        "agent_findings": [
            {
                "agent_type": "tech_comparator",
                "findings": None,  # Invalid findings
            }
        ],
    }

    # Should not raise, but return empty evaluation results
    result = await evaluate_agent_quality(state)
    assert "evaluation_results" in result

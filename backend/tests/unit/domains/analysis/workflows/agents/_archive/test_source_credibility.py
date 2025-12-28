"""Tests for source_credibility agent."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.schemas.agents.source_credibility import (
    CredibilitySignal,
    SourceCredibilityOutput,
)
from app.domains.analysis.workflows.agents.source_credibility import run_source_credibility

if TYPE_CHECKING:
    from app.core.types import AnalysisID
    from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=MagicMock())
    session.execute = AsyncMock(return_value=mock_result)
    return session


@pytest.fixture
def sample_analysis_id() -> AnalysisID:
    """Sample analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.source_credibility.create_agent_with_optional_few_shot"
)
@patch("app.domains.analysis.workflows.agents.source_credibility.run_agent_with_tracking")
@patch("app.domains.analysis.workflows.agents.source_credibility.get_prompt_manager")
async def test_source_credibility_official_documentation(
    mock_get_pm: MagicMock,
    mock_run_tracking: MagicMock,
    mock_create_agent: MagicMock,
    mock_session: AsyncSession,
    sample_analysis_id: AnalysisID,
) -> None:
    """Test source credibility assessment for official documentation."""
    # Mock PromptManager
    mock_pm = AsyncMock()
    mock_pm.get_prompt_with_langfuse_client = AsyncMock(
        return_value=("You are a source credibility analyst.", None)
    )
    mock_get_pm.return_value = mock_pm

    # Mock agent creation
    mock_create_agent.return_value = AsyncMock()

    # Mock run_agent_with_tracking response
    mock_run_tracking.return_value = {
        "agent_type": "source_credibility",
        "findings": SourceCredibilityOutput(
            source_url="https://react.dev/learn/state-management",
            credibility_score=0.95,
            signals=[
                CredibilitySignal(
                    signal_type="domain_authority",
                    value="Official React documentation",
                    weight=1.0,
                ),
                CredibilitySignal(
                    signal_type="author_credentials",
                    value="React Team (Facebook/Meta)",
                    weight=0.9,
                ),
            ],
            risk_factors=[],
            recommendation="trustworthy",
            confidence_score=0.95,
        ).model_dump(),
        "processing_time_ms": 100,
    }

    content = "React State Management Guide"
    state: AnalysisState = {
        "url": "https://react.dev/learn/state-management",
        "skill_level": "intermediate",
        "content_signals": {},
    }

    result = await run_source_credibility(
        content=content,
        content_type="article",
        analysis_id=sample_analysis_id,
        session=mock_session,
        state=state,
    )

    assert result["agent_type"] == "source_credibility"
    assert "findings" in result

    findings = SourceCredibilityOutput.model_validate(result["findings"])

    # Official docs should have high credibility
    assert findings.credibility_score >= 0.85
    assert findings.source_url == "https://react.dev/learn/state-management"
    assert findings.recommendation == "trustworthy"
    assert len(findings.signals) >= 2
    assert len(findings.risk_factors) == 0
    assert findings.confidence_score >= 0.8

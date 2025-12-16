"""Unit tests for save_agent_finding error handling."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.base import save_agent_finding



@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_save_agent_finding_analysis_not_found(mock_session, analysis_id):
    """Test save_agent_finding raises ValueError when Analysis not found."""
    # Mock session to return None (analysis not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ValueError, match=r"Analysis record with id=.* does not exist"):
        await save_agent_finding(
            session=mock_session,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            findings={"key": "value"},
        )


@pytest.mark.asyncio
async def test_save_agent_finding_success(mock_session, analysis_id):
    """Test save_agent_finding succeeds when Analysis exists."""
    # Mock Analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id

    # Mock session to return analysis
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock AgentFinding creation
    with patch("app.domains.analysis.workflows.agents.base.AgentFinding") as mock_finding_class:
        mock_finding = MagicMock()
        mock_finding_class.return_value = mock_finding

        result = await save_agent_finding(
            session=mock_session,
            analysis_id=analysis_id,
            agent_type="tech_comparator",
            findings={"key": "value"},
        )

        assert result == mock_finding
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

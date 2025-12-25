"""Unit tests for status transition validation (retry and rerun paths).

Tests the transition rules that allow:
- Failed states → pending (for retry)
- Complete → analyzing (for rerun, skipping extraction)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.schemas.api import AnalysisStatus
from app.domains.analysis.services.persistence.status_updater import (
    VALID_TRANSITIONS,
    StatusUpdater,
    _is_valid_transition,
)


class TestValidTransitionsDict:
    """Test VALID_TRANSITIONS dictionary structure."""

    def test_failed_states_allow_retry(self):
        """All failed states should allow transition to pending for retry."""
        failed_states = [
            "extraction_failed",
            "analysis_failed",
            "artifact_failed",
            "quality_gate_failed",
            "failed",
        ]
        for status in failed_states:
            assert "pending" in VALID_TRANSITIONS[status], (
                f"{status} should allow transition to pending"
            )

    def test_complete_allows_rerun(self):
        """Complete state should allow transition to analyzing for rerun."""
        assert "analyzing" in VALID_TRANSITIONS["complete"], (
            "complete should allow transition to analyzing"
        )

    def test_cancelled_is_terminal(self):
        """Cancelled state should not allow any transitions."""
        assert VALID_TRANSITIONS["cancelled"] == set(), "cancelled should be terminal"

    def test_normal_workflow_progression(self):
        """Normal workflow states should allow forward progression."""
        assert "extracting" in VALID_TRANSITIONS["pending"]
        assert "analyzing" in VALID_TRANSITIONS["extracting"]
        assert "generating_artifact" in VALID_TRANSITIONS["analyzing"]
        assert "complete" in VALID_TRANSITIONS["generating_artifact"]


class TestIsValidTransition:
    """Test _is_valid_transition helper function."""

    def test_retry_transitions_valid(self):
        """All failed states should allow transition to pending."""
        failed_states = [
            "extraction_failed",
            "analysis_failed",
            "artifact_failed",
            "quality_gate_failed",
            "failed",
        ]
        for status in failed_states:
            assert _is_valid_transition(status, "pending"), f"{status} -> pending should be valid"

    def test_rerun_transition_valid(self):
        """Complete should allow transition to analyzing."""
        assert _is_valid_transition("complete", "analyzing"), (
            "complete -> analyzing should be valid"
        )

    def test_invalid_transitions_blocked(self):
        """Invalid transitions should be blocked."""
        invalid_transitions = [
            ("complete", "pending"),  # complete can't retry
            ("pending", "pending"),  # no self-transitions
            ("cancelled", "pending"),  # cancelled is terminal
            ("cancelled", "analyzing"),  # cancelled is terminal
            ("complete", "extracting"),  # complete can't go to extracting
        ]
        for from_status, to_status in invalid_transitions:
            assert not _is_valid_transition(from_status, to_status), (
                f"{from_status} -> {to_status} should be blocked"
            )


class TestAnalysisStatusHelpers:
    """Test AnalysisStatus enum helper methods."""

    def test_is_retryable_for_failed_states(self):
        """All failed states should be retryable."""
        assert AnalysisStatus.is_retryable("extraction_failed")
        assert AnalysisStatus.is_retryable("analysis_failed")
        assert AnalysisStatus.is_retryable("artifact_failed")
        assert AnalysisStatus.is_retryable("quality_gate_failed")
        assert AnalysisStatus.is_retryable("failed")

    def test_is_retryable_for_non_failed_states(self):
        """Non-failed states should not be retryable."""
        non_failed_states = ["pending", "extracting", "analyzing", "complete", "cancelled"]
        for status in non_failed_states:
            assert not AnalysisStatus.is_retryable(status), f"{status} should not be retryable"

    def test_is_rerunnable_only_for_complete(self):
        """Only complete status should be rerunnable."""
        assert AnalysisStatus.is_rerunnable("complete")

        non_complete_states = [
            "pending",
            "failed",
            "extraction_failed",
            "cancelled",
            "analyzing",
        ]
        for status in non_complete_states:
            assert not AnalysisStatus.is_rerunnable(status), f"{status} should not be rerunnable"

    def test_retryable_matches_transition_validation(self):
        """is_retryable() should match _is_valid_transition() for failed states."""
        failed_states = [
            "extraction_failed",
            "analysis_failed",
            "artifact_failed",
            "quality_gate_failed",
            "failed",
        ]
        for status in failed_states:
            can_transition = _is_valid_transition(status, "pending")
            is_retryable = AnalysisStatus.is_retryable(status)
            assert can_transition == is_retryable, (
                f"Mismatch for {status}: transition={can_transition}, retryable={is_retryable}"
            )

    def test_rerunnable_matches_transition_validation(self):
        """is_rerunnable() should match _is_valid_transition() for complete."""
        can_transition = _is_valid_transition("complete", "analyzing")
        is_rerunnable = AnalysisStatus.is_rerunnable("complete")
        assert can_transition == is_rerunnable, (
            f"Mismatch for complete: transition={can_transition}, rerunnable={is_rerunnable}"
        )


class TestStatusUpdaterRetryPath:
    """Test StatusUpdater with retry transitions."""

    @pytest.mark.asyncio
    async def test_retry_from_extraction_failed(self):
        """Test retry transition: extraction_failed -> pending."""
        analysis_id = uuid.uuid4()
        mock_analysis = MagicMock()
        mock_analysis.id = analysis_id
        mock_analysis.status = "extraction_failed"

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db_session.execute.return_value = mock_result
        mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_db_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ):
            updater = StatusUpdater()
            await updater.update(analysis_id, "pending")

        assert mock_analysis.status == "pending"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_from_quality_gate_failed(self):
        """Test retry transition: quality_gate_failed -> pending."""
        analysis_id = uuid.uuid4()
        mock_analysis = MagicMock()
        mock_analysis.id = analysis_id
        mock_analysis.status = "quality_gate_failed"

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db_session.execute.return_value = mock_result
        mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_db_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ):
            updater = StatusUpdater()
            await updater.update(analysis_id, "pending")

        assert mock_analysis.status == "pending"
        mock_db_session.commit.assert_called_once()


class TestStatusUpdaterRerunPath:
    """Test StatusUpdater with rerun transitions."""

    @pytest.mark.asyncio
    async def test_rerun_from_complete(self):
        """Test rerun transition: complete -> analyzing."""
        analysis_id = uuid.uuid4()
        mock_analysis = MagicMock()
        mock_analysis.id = analysis_id
        mock_analysis.status = "complete"

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db_session.execute.return_value = mock_result
        mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_db_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ):
            updater = StatusUpdater()
            await updater.update(analysis_id, "analyzing")

        assert mock_analysis.status == "analyzing"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_rerun_blocked(self):
        """Test that complete -> pending is blocked (use retry, not rerun)."""
        analysis_id = uuid.uuid4()
        mock_analysis = MagicMock()
        mock_analysis.id = analysis_id
        mock_analysis.status = "complete"

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db_session.execute.return_value = mock_result
        mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_db_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ):
            updater = StatusUpdater()
            with pytest.raises(ValueError, match="Invalid status transition"):
                await updater.update(analysis_id, "pending")

        # Status should not be changed
        assert mock_analysis.status == "complete"
        mock_db_session.commit.assert_not_called()


class TestStatusUpdaterInvalidRetry:
    """Test StatusUpdater blocks invalid retry attempts."""

    @pytest.mark.asyncio
    async def test_cancelled_cannot_retry(self):
        """Test that cancelled state cannot transition to pending."""
        analysis_id = uuid.uuid4()
        mock_analysis = MagicMock()
        mock_analysis.id = analysis_id
        mock_analysis.status = "cancelled"

        mock_db_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_analysis
        mock_db_session.execute.return_value = mock_result
        mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_db_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ):
            updater = StatusUpdater()
            with pytest.raises(ValueError, match="Invalid status transition"):
                await updater.update(analysis_id, "pending")

        assert mock_analysis.status == "cancelled"
        mock_db_session.commit.assert_not_called()

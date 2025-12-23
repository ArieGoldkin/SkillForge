"""Unit tests for AnalysisStatus enum and helper methods."""

from app.domains.analysis.schemas.api import AnalysisStatus


class TestAnalysisStatus:
    """Test AnalysisStatus enum values and methods."""

    def test_enum_values_exist(self):
        """Test all expected status values exist."""
        assert AnalysisStatus.PENDING == "pending"
        assert AnalysisStatus.EXTRACTING == "extracting"
        assert AnalysisStatus.ANALYZING == "analyzing"
        assert AnalysisStatus.GENERATING_ARTIFACT == "generating_artifact"
        assert AnalysisStatus.COMPLETE == "complete"
        assert AnalysisStatus.EXTRACTION_FAILED == "extraction_failed"
        assert AnalysisStatus.ANALYSIS_FAILED == "analysis_failed"
        assert AnalysisStatus.ARTIFACT_FAILED == "artifact_failed"
        assert AnalysisStatus.QUALITY_GATE_FAILED == "quality_gate_failed"
        assert AnalysisStatus.FAILED == "failed"
        assert AnalysisStatus.CANCELLED == "cancelled"

    def test_is_failure_returns_true_for_failure_statuses(self):
        """Test is_failure returns True for all failure statuses."""
        failure_statuses = [
            AnalysisStatus.EXTRACTION_FAILED,
            AnalysisStatus.ANALYSIS_FAILED,
            AnalysisStatus.ARTIFACT_FAILED,
            AnalysisStatus.QUALITY_GATE_FAILED,
            AnalysisStatus.FAILED,
        ]

        for status in failure_statuses:
            assert AnalysisStatus.is_failure(status.value) is True

    def test_is_failure_returns_false_for_non_failure_statuses(self):
        """Test is_failure returns False for non-failure statuses."""
        non_failure_statuses = [
            AnalysisStatus.PENDING,
            AnalysisStatus.EXTRACTING,
            AnalysisStatus.ANALYZING,
            AnalysisStatus.GENERATING_ARTIFACT,
            AnalysisStatus.COMPLETE,
            AnalysisStatus.CANCELLED,
        ]

        for status in non_failure_statuses:
            assert AnalysisStatus.is_failure(status.value) is False

    def test_is_complete_returns_true_only_for_complete(self):
        """Test is_complete returns True only for COMPLETE status."""
        assert AnalysisStatus.is_complete(AnalysisStatus.COMPLETE.value) is True

    def test_is_complete_returns_false_for_all_other_statuses(self):
        """Test is_complete returns False for all non-complete statuses."""
        non_complete_statuses = [
            AnalysisStatus.PENDING,
            AnalysisStatus.EXTRACTING,
            AnalysisStatus.ANALYZING,
            AnalysisStatus.GENERATING_ARTIFACT,
            AnalysisStatus.EXTRACTION_FAILED,
            AnalysisStatus.ANALYSIS_FAILED,
            AnalysisStatus.ARTIFACT_FAILED,
            AnalysisStatus.QUALITY_GATE_FAILED,
            AnalysisStatus.FAILED,
            AnalysisStatus.CANCELLED,
        ]

        for status in non_complete_statuses:
            assert AnalysisStatus.is_complete(status.value) is False

    def test_is_complete_returns_false_for_invalid_status(self):
        """Test is_complete returns False for invalid status string."""
        assert AnalysisStatus.is_complete("invalid_status") is False
        assert AnalysisStatus.is_complete("") is False

    def test_is_failure_returns_false_for_invalid_status(self):
        """Test is_failure returns False for invalid status string."""
        assert AnalysisStatus.is_failure("invalid_status") is False
        assert AnalysisStatus.is_failure("") is False

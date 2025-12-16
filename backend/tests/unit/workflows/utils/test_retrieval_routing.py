"""Unit tests for retrieval routing utilities."""

from unittest.mock import MagicMock

import pytest

from app.shared.workflows.utils.retrieval_routing import coarse_to_fine

@pytest.mark.unit


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock structured logger."""
    logger = MagicMock()
    logger.info = MagicMock()

    # Patch the logger in the retrieval_routing module
    monkeypatch.setattr("app.workflows.utils.retrieval_routing.logger", logger)
    return logger


def test_coarse_to_fine_basic(mock_logger):
    """Test basic coarse-to-fine retrieval with valid hits."""
    coarse_hits = [
        {"path": "/doc/section1", "score": 0.9},
        {"path": "/doc/section2", "score": 0.8},
        {"path": "/doc/section3", "score": 0.7},
    ]

    fine_results = [
        {"path": "/doc/section1", "snippet": "result 1", "score": 0.95},
        {"path": "/doc/section2", "snippet": "result 2", "score": 0.85},
    ]

    def mock_fine_search(paths, top_k):
        assert paths == ["/doc/section1", "/doc/section2", "/doc/section3"]
        assert top_k == 5
        return fine_results

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == fine_results
    assert len(result) == 2
    mock_logger.info.assert_called_once_with(
        "coarse_to_fine_complete",
        coarse_considered=3,
        fine_returned=2,
    )


def test_coarse_to_fine_empty_coarse_hits(mock_logger):
    """Test coarse-to-fine with empty coarse hits."""
    coarse_hits = []

    def mock_fine_search(paths, top_k):
        pytest.fail("fine_search_fn should not be called with empty coarse hits")

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == []
    mock_logger.info.assert_not_called()


def test_coarse_to_fine_top_k_coarse_limit(mock_logger):
    """Test that only top_k_coarse hits are considered."""
    coarse_hits = [{"path": f"/doc/section{i}", "score": 1.0 - i * 0.1} for i in range(10)]

    fine_results = [{"path": "/doc/section0", "snippet": "result", "score": 0.99}]

    def mock_fine_search(paths, top_k):
        # Should only receive first 3 paths due to top_k_coarse=3
        assert len(paths) == 3
        assert paths == ["/doc/section0", "/doc/section1", "/doc/section2"]
        return fine_results

    result = coarse_to_fine(coarse_hits, mock_fine_search, top_k_coarse=3)

    assert result == fine_results
    mock_logger.info.assert_called_once_with(
        "coarse_to_fine_complete",
        coarse_considered=3,
        fine_returned=1,
    )


def test_coarse_to_fine_top_k_fine_parameter(mock_logger):
    """Test that top_k_fine is passed to fine_search_fn."""
    coarse_hits = [{"path": "/doc/section1", "score": 0.9}]

    fine_results = [
        {"path": "/doc/section1", "snippet": f"result {i}", "score": 0.9 - i * 0.1}
        for i in range(10)
    ]

    def mock_fine_search(paths, top_k):
        assert top_k == 10
        return fine_results

    result = coarse_to_fine(coarse_hits, mock_fine_search, top_k_fine=10)

    assert result == fine_results
    assert len(result) == 10


def test_coarse_to_fine_missing_path_in_hits(mock_logger):
    """Test handling of coarse hits without path metadata."""
    coarse_hits = [
        {"path": "/doc/section1", "score": 0.9},
        {"score": 0.8},  # Missing path
        {"path": None, "score": 0.7},  # Null path
        {"path": "/doc/section2", "score": 0.6},
    ]

    fine_results = [{"path": "/doc/section1", "snippet": "result", "score": 0.95}]

    def mock_fine_search(paths, top_k):
        # Should only include hits with valid paths
        assert paths == ["/doc/section1", "/doc/section2"]
        return fine_results

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == fine_results


def test_coarse_to_fine_with_iterator(mock_logger):
    """Test coarse-to-fine with iterator instead of list."""

    def coarse_generator():
        yield {"path": "/doc/section1", "score": 0.9}
        yield {"path": "/doc/section2", "score": 0.8}

    fine_results = [{"path": "/doc/section1", "snippet": "result", "score": 0.95}]

    def mock_fine_search(paths, top_k):
        assert paths == ["/doc/section1", "/doc/section2"]
        return fine_results

    result = coarse_to_fine(coarse_generator(), mock_fine_search)

    assert result == fine_results


def test_coarse_to_fine_empty_fine_results(mock_logger):
    """Test when fine search returns no results."""
    coarse_hits = [{"path": "/doc/section1", "score": 0.9}]

    def mock_fine_search(paths, top_k):
        return []

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == []
    mock_logger.info.assert_called_once_with(
        "coarse_to_fine_complete",
        coarse_considered=1,
        fine_returned=0,
    )


def test_coarse_to_fine_all_hits_missing_paths(mock_logger):
    """Test when all coarse hits are missing path metadata."""
    coarse_hits = [
        {"score": 0.9},
        {"score": 0.8},
        {"path": None, "score": 0.7},
    ]

    def mock_fine_search(paths, top_k):
        assert paths == []
        return []

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == []


def test_coarse_to_fine_preserves_fine_hit_structure(mock_logger):
    """Test that fine hit structure is preserved in output."""
    coarse_hits = [{"path": "/doc/section1", "score": 0.9}]

    fine_results = [
        {
            "path": "/doc/section1",
            "snippet": "detailed content",
            "score": 0.95,
            "metadata": {"author": "test", "tags": ["python"]},
        }
    ]

    def mock_fine_search(paths, top_k):
        return fine_results

    result = coarse_to_fine(coarse_hits, mock_fine_search)

    assert result == fine_results
    assert result[0]["metadata"] == {"author": "test", "tags": ["python"]}

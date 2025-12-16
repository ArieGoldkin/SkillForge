"""Unit tests for exception hierarchy."""

from app.core.exceptions import (

@pytest.mark.unit
    DatabaseError,
    EmbeddingError,
    JinaReaderError,
    ServiceException,
    SkillForgeException,
    WorkflowError,
)


def test_exception_hierarchy() -> None:
    """Test that exceptions follow the correct hierarchy."""
    # Base exception
    assert issubclass(SkillForgeException, Exception)

    # Service exceptions
    assert issubclass(ServiceException, SkillForgeException)
    assert issubclass(EmbeddingError, ServiceException)
    assert issubclass(JinaReaderError, ServiceException)

    # Other exceptions
    assert issubclass(WorkflowError, SkillForgeException)
    assert issubclass(DatabaseError, SkillForgeException)


def test_exception_instantiation() -> None:
    """Test that exceptions can be instantiated with messages."""
    base_exc = SkillForgeException("Base error")
    assert str(base_exc) == "Base error"

    service_exc = ServiceException("Service error")
    assert str(service_exc) == "Service error"
    assert isinstance(service_exc, SkillForgeException)

    embedding_exc = EmbeddingError("Embedding failed")
    assert str(embedding_exc) == "Embedding failed"
    assert isinstance(embedding_exc, ServiceException)
    assert isinstance(embedding_exc, SkillForgeException)

    jina_exc = JinaReaderError("Jina extraction failed")
    assert str(jina_exc) == "Jina extraction failed"
    assert isinstance(jina_exc, ServiceException)
    assert isinstance(jina_exc, SkillForgeException)

    workflow_exc = WorkflowError("Workflow failed")
    assert str(workflow_exc) == "Workflow failed"
    assert isinstance(workflow_exc, SkillForgeException)

    db_exc = DatabaseError("Database error")
    assert str(db_exc) == "Database error"
    assert isinstance(db_exc, SkillForgeException)


def test_exception_catching() -> None:
    """Test that exceptions can be caught by base class."""
    try:
        msg = "Test error"
        raise EmbeddingError(msg)
    except SkillForgeException as e:
        assert isinstance(e, EmbeddingError)
        assert str(e) == "Test error"

    try:
        msg = "Test error"
        raise JinaReaderError(msg)
    except ServiceException as e:
        assert isinstance(e, JinaReaderError)
        assert str(e) == "Test error"

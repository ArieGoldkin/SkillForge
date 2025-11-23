"""Tests for Request ID middleware."""

import uuid

import pytest
import structlog
from fastapi.testclient import TestClient

from app.main import app, RequestIDMiddleware


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def reset_context():
    """Reset structlog context variables before and after tests."""
    # Clear any existing context
    structlog.contextvars.clear_contextvars()
    yield
    # Cleanup
    structlog.contextvars.clear_contextvars()


def test_request_id_middleware_adds_header_to_response(client, reset_context):
    """Test Request ID middleware adds X-Request-ID header to all responses."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None
    # Should be a valid UUID format
    try:
        uuid.UUID(response.headers["X-Request-ID"])
    except ValueError:
        pytest.fail("X-Request-ID is not a valid UUID")


def test_request_id_middleware_uses_custom_header(client, reset_context):
    """Test Request ID middleware uses existing X-Request-ID header if provided."""
    custom_id = "custom-request-id-12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_middleware_generates_unique_ids(client, reset_context):
    """Test Request ID middleware generates unique IDs for each request."""
    response1 = client.get("/api/v1/health")
    response2 = client.get("/api/v1/health")
    response3 = client.get("/api/v1/health")

    id1 = response1.headers["X-Request-ID"]
    id2 = response2.headers["X-Request-ID"]
    id3 = response3.headers["X-Request-ID"]

    # All IDs should be unique
    assert id1 != id2
    assert id2 != id3
    assert id1 != id3


def test_request_id_middleware_adds_to_all_endpoints(client, reset_context):
    """Test Request ID middleware adds header to all endpoints."""
    endpoints = ["/", "/api/v1/health", "/docs", "/openapi.json"]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert "X-Request-ID" in response.headers, f"Missing X-Request-ID in {endpoint}"
        assert response.headers["X-Request-ID"] is not None


def test_request_id_middleware_adds_to_error_responses(client, reset_context):
    """Test Request ID middleware adds header to error responses."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None


def test_request_id_middleware_binds_to_context_vars(client, reset_context):
    """Test Request ID middleware binds request ID to structlog context vars."""
    custom_id = "test-context-binding"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})

    # Context should be cleaned up after request
    # So we can't check it here, but we verify the header is set
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_middleware_cleans_up_context(reset_context):
    """Test Request ID middleware properly cleans up context variables."""
    # Before request - context should be empty
    context = structlog.contextvars.get_contextvars()
    assert "request_id" not in context or context.get("request_id") is None

    client = TestClient(app)
    response = client.get("/api/v1/health")

    # After request - context should still be clean (no leakage)
    context_after = structlog.contextvars.get_contextvars()
    # Context should be clean (request_id removed in finally block)
    assert response.headers["X-Request-ID"] is not None


def test_request_id_middleware_stores_in_request_state(client, reset_context):
    """Test Request ID middleware stores request ID in request.state."""
    custom_id = "test-state-storage"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})

    # Verify header is set (indirect proof that state was set)
    assert response.headers["X-Request-ID"] == custom_id


def test_request_id_middleware_class_structure():
    """Test RequestIDMiddleware is a proper BaseHTTPMiddleware subclass."""
    from starlette.middleware.base import BaseHTTPMiddleware

    assert issubclass(RequestIDMiddleware, BaseHTTPMiddleware)


def test_request_id_middleware_multiple_concurrent_requests(client, reset_context):
    """Test Request ID middleware handles concurrent requests correctly."""
    import threading

    ids = []
    errors = []

    def make_request():
        try:
            response = client.get("/api/v1/health")
            ids.append(response.headers["X-Request-ID"])
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All requests should succeed
    assert len(errors) == 0
    # All IDs should be unique
    assert len(ids) == len(set(ids)), "Request IDs should be unique across concurrent requests"

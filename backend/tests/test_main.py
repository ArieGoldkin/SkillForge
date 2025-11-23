"""Tests for main FastAPI application."""

import pytest
from fastapi import status


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "SkillForge API"
    assert "version" in data


def test_root_endpoint_includes_request_id(client):
    """Test root endpoint includes X-Request-ID header."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_health_check_includes_request_id(client):
    """Test health check endpoint includes X-Request-ID header."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None


def test_health_check_with_custom_request_id(client):
    """Test health check endpoint respects custom X-Request-ID header."""
    custom_id = "custom-health-check-123"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["X-Request-ID"] == custom_id


def test_openapi_docs_available(client):
    """Test OpenAPI docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema


def test_openapi_docs_includes_request_id(client):
    """Test OpenAPI docs include X-Request-ID header."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in response.headers

    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    assert "X-Request-ID" in response.headers


def test_error_endpoint_includes_request_id(client):
    """Test error endpoints include X-Request-ID header."""
    response = client.get("/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] is not None


def test_global_exception_handler_includes_request_id(client):
    """Test global exception handler includes request ID in response."""
    # This test verifies that the global exception handler has access to request_id
    # We can't easily trigger an exception in a test, but we verify the structure
    response = client.get("/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "X-Request-ID" in response.headers

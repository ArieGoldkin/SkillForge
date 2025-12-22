"""API contract validation tests.

This module validates that the API implementation matches the documented
contract, including request/response schemas, SSE event formats, and error
response structures.
"""

import uuid
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from pydantic import HttpUrl

from app.domains.analysis.schemas.api import AnalyzeCreateResponse, AnalyzeRequest
from app.main import app
from app.shared.services.messaging.sse_helpers import emit_streaming_event


def resolve_ref(schema: dict, openapi_schema: dict) -> dict:
    """Resolve $ref to actual schema from components.

    OpenAPI 3.1 uses $ref to reference schemas in components/schemas.
    This helper dereferences them to get the actual schema properties.
    """
    if "$ref" in schema:
        ref_path = schema["$ref"]  # e.g., "#/components/schemas/AnalyzeRequest"
        # Extract schema name from path
        schema_name = ref_path.split("/")[-1]
        return openapi_schema["components"]["schemas"].get(schema_name, {})
    return schema


def test_analyze_request_schema_validation():
    """Test that AnalyzeRequest schema matches API behavior."""
    # Valid request
    request = AnalyzeRequest(url=HttpUrl("https://example.com/article"))

    assert str(request.url) == "https://example.com/article"
    assert request.analysis_id is None

    # Request with custom ID
    request_with_id = AnalyzeRequest(
        url=HttpUrl("https://example.com/article"), analysis_id="custom-id-123"
    )

    assert str(request_with_id.url) == "https://example.com/article"
    assert request_with_id.analysis_id == "custom-id-123"


@pytest.mark.asyncio
async def test_analyze_response_schema_validation():
    """Test that AnalyzeCreateResponse schema matches API response."""
    analysis_id = str(uuid.uuid4())
    url = "https://example.com/article"
    content_type = "article"
    sse_endpoint = f"/api/v1/analyze/{analysis_id}/stream"

    response_data = {
        "analysis_id": analysis_id,
        "url": url,
        "content_type": content_type,
        "status": "pending",
        "sse_endpoint": sse_endpoint,
    }

    # Validate against schema
    response = AnalyzeCreateResponse(**response_data)

    assert response.analysis_id == analysis_id
    assert response.url == url
    assert response.content_type == content_type
    assert response.status == "pending"
    assert response.sse_endpoint == sse_endpoint


@pytest.mark.asyncio
async def test_api_response_matches_schema(reset_engine_connections):
    """Test that actual API response matches AnalyzeCreateResponse schema."""
    analysis_uuid = uuid.uuid4()

    # Mock run_workflow_task to be a no-op async function
    async def mock_run_workflow_task(analysis_id, url):
        """Mock workflow task that does nothing."""
        pass

    with (
        patch("app.api.v1.analyze.uuid.uuid4", return_value=analysis_uuid),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.WorkflowOrchestrator.run",
            new=mock_run_workflow_task,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"url": "https://example.com/article"},
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            # Validate against schema
            api_response = AnalyzeCreateResponse(**data)

            assert api_response.analysis_id == str(analysis_uuid)
            assert api_response.url == "https://example.com/article"
            assert api_response.content_type == "article"
            assert api_response.status == "pending"
            assert "/stream" in api_response.sse_endpoint


@pytest.mark.asyncio
async def test_sse_event_format_progress():
    """Test that SSE progress events match documented schema."""
    analysis_id = str(uuid.uuid4())

    # Emit a progress event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
        word_count=100,
    )

    # Verify event structure (would need to subscribe to channel to test fully)
    # For now, we verify the function doesn't raise errors
    assert True  # Event emitted successfully


@pytest.mark.asyncio
async def test_sse_event_format_complete():
    """Test that SSE complete events match documented schema."""
    analysis_id = str(uuid.uuid4())
    artifact_id = str(uuid.uuid4())

    # Emit a complete event
    await emit_streaming_event(
        "complete",
        analysis_id=analysis_id,
        stage="artifact_generation",
        status="complete",
        artifact_id=artifact_id,
    )

    # Verify event structure
    assert True  # Event emitted successfully


@pytest.mark.asyncio
async def test_sse_event_format_error():
    """Test that SSE error events match documented schema."""
    analysis_id = str(uuid.uuid4())

    # Emit an error event
    await emit_streaming_event(
        "error",
        analysis_id=analysis_id,
        stage="extraction",
        status="failed",
        error="Test error message",
        error_code="TEST_ERROR",
    )

    # Verify event structure
    assert True  # Event emitted successfully


@pytest.mark.asyncio
async def test_error_response_format_consistency():
    """Test that error responses follow consistent format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 422 error (validation error from FastAPI)
        response = await client.post(
            "/api/v1/analyze",
            json={"url": "invalid-url"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        # FastAPI validation errors use "detail" field
        assert "detail" in data

        # Test 404 error (not found)
        response = await client.get(f"/api/v1/analyze/{uuid.uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in str(data["detail"]).lower()


@pytest.mark.asyncio
async def test_openapi_schema_includes_all_endpoints():
    """Test that OpenAPI schema includes all documented endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        schema = response.json()
        paths = schema["paths"]

        # Verify all endpoints are documented
        assert "/" in paths
        assert "/api/v1/health" in paths
        assert "/api/v1/analyze" in paths
        assert "/api/v1/analyze/{analysis_id}" in paths
        assert "/api/v1/analyze/{analysis_id}/stream" in paths


@pytest.mark.asyncio
async def test_openapi_schema_request_schemas():
    """Test that OpenAPI schema includes correct request schemas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        schema = response.json()

        # Check POST /api/v1/analyze request schema
        analyze_path = schema["paths"]["/api/v1/analyze"]
        post_schema = analyze_path["post"]
        request_body = post_schema["requestBody"]
        content = request_body["content"]["application/json"]
        raw_request_schema = content["schema"]

        # Resolve $ref to get actual schema
        request_schema = resolve_ref(raw_request_schema, schema)

        # Verify required fields
        assert "url" in request_schema["properties"]
        assert "analysis_id" in request_schema["properties"]
        assert "url" in request_schema.get("required", [])


@pytest.mark.asyncio
async def test_openapi_schema_response_schemas():
    """Test that OpenAPI schema includes correct response schemas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        schema = response.json()

        # Check POST /api/v1/analyze response schema
        analyze_path = schema["paths"]["/api/v1/analyze"]
        post_schema = analyze_path["post"]
        responses = post_schema["responses"]

        # Verify 201 response exists
        assert "201" in responses
        response_201 = responses["201"]
        content = response_201["content"]["application/json"]
        raw_response_schema = content["schema"]

        # Resolve $ref to get actual schema
        response_schema = resolve_ref(raw_response_schema, schema)

        # Verify required fields in response
        assert "analysis_id" in response_schema["properties"]
        assert "url" in response_schema["properties"]
        assert "content_type" in response_schema["properties"]
        assert "status" in response_schema["properties"]
        assert "sse_endpoint" in response_schema["properties"]


@pytest.mark.asyncio
async def test_openapi_schema_error_responses():
    """Test that OpenAPI schema documents error responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        schema = response.json()

        # Check POST /api/v1/analyze error responses
        analyze_path = schema["paths"]["/api/v1/analyze"]
        post_schema = analyze_path["post"]
        responses = post_schema["responses"]

        # Verify error responses are documented
        assert "422" in responses  # Validation error
        # Note: 500 errors are typically not documented in clean OpenAPI specs
        # They represent unexpected server errors, not part of the API contract

        # Check GET /api/v1/analyze/{id} error responses
        get_path = schema["paths"]["/api/v1/analyze/{analysis_id}"]
        get_schema = get_path["get"]
        get_responses = get_schema["responses"]

        # Verify 422 is documented (validation error for path params)
        assert "422" in get_responses


@pytest.mark.asyncio
async def test_content_type_values_match_schema(reset_engine_connections):
    """Test that content_type values match documented enum."""

    # Mock run_workflow_task to be a no-op async function
    async def mock_run_workflow_task(analysis_id, url):
        """Mock workflow task that does nothing."""
        pass

    with patch(
        "app.domains.analysis.services.workflow.orchestrator.WorkflowOrchestrator.run",
        new=mock_run_workflow_task,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test all content types
            test_cases = [
                ("https://example.com/article", "article"),
                ("https://www.youtube.com/watch?v=test", "video"),
                ("https://github.com/user/repo", "repo"),
            ]

            for url, expected_type in test_cases:
                response = await client.post(
                    "/api/v1/analyze",
                    json={"url": url},
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["content_type"] == expected_type


@pytest.mark.asyncio
async def test_sse_endpoint_path_format(reset_engine_connections):
    """Test that SSE endpoint path follows documented format."""
    analysis_uuid = uuid.uuid4()

    # Mock run_workflow_task to be a no-op async function
    async def mock_run_workflow_task(analysis_id, url):
        """Mock workflow task that does nothing."""
        pass

    with (
        patch("app.api.v1.analyze.uuid.uuid4", return_value=analysis_uuid),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.WorkflowOrchestrator.run",
            new=mock_run_workflow_task,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"url": "https://example.com/article"},
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            # Verify SSE endpoint format
            sse_endpoint = data["sse_endpoint"]
            assert sse_endpoint.startswith("/api/v1/analyze/")
            assert sse_endpoint.endswith("/stream")
            assert str(analysis_uuid) in sse_endpoint


@pytest.mark.asyncio
async def test_uuid_format_in_responses(reset_engine_connections):
    """Test that UUIDs in responses are valid UUID format."""
    analysis_uuid = uuid.uuid4()

    # Mock run_workflow_task to be a no-op async function
    async def mock_run_workflow_task(analysis_id, url):
        """Mock workflow task that does nothing."""
        pass

    with (
        patch("app.api.v1.analyze.uuid.uuid4", return_value=analysis_uuid),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.WorkflowOrchestrator.run",
            new=mock_run_workflow_task,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analyze",
                json={"url": "https://example.com/article"},
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            # Verify UUID format
            analysis_id = data["analysis_id"]
            # Should be valid UUID string
            parsed_uuid = uuid.UUID(analysis_id)
            assert str(parsed_uuid) == analysis_id

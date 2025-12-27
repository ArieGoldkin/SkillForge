"""Unit tests for branded/opaque ID types using Annotated pattern.

Tests the Annotated-based ID type system introduced in 2025 best practices.
Annotated types are transparent at runtime - no conversion needed.
"""

from typing import get_args, get_origin
from uuid import UUID, uuid4

from app.core.branded_ids import (
    AnalysisID,
    ArtifactID,
    ChunkID,
    MessageID,
    SessionID,
    TopicID,
    TraceID,
)


class TestAnnotatedTypesExist:
    """Verify all branded types are properly defined."""

    def test_all_uuid_types_defined(self):
        """All UUID-based branded types are importable."""
        assert AnalysisID is not None
        assert ArtifactID is not None
        assert SessionID is not None
        assert ChunkID is not None
        assert MessageID is not None

    def test_all_string_types_defined(self):
        """All string-based branded types are importable."""
        assert TraceID is not None
        assert TopicID is not None


class TestAnnotatedTypeStructure:
    """Verify Annotated types have correct structure."""

    def test_analysis_id_is_annotated_uuid(self):
        """AnalysisID is Annotated[UUID, ...]."""
        # get_origin returns Annotated for Annotated types
        assert get_origin(AnalysisID) is not None
        # get_args returns (UUID, "analysis_id")
        args = get_args(AnalysisID)
        assert UUID in args or args[0] is UUID

    def test_trace_id_is_annotated_str(self):
        """TraceID is Annotated[str, ...]."""
        args = get_args(TraceID)
        assert str in args or args[0] is str


class TestUUIDTypesAcceptUUID:
    """Verify UUID-based branded types accept UUID values directly."""

    def test_analysis_id_accepts_uuid(self):
        """UUID can be used where AnalysisID is expected."""
        uuid_obj: AnalysisID = uuid4()
        assert isinstance(uuid_obj, UUID)

    def test_artifact_id_accepts_uuid(self):
        """UUID can be used where ArtifactID is expected."""
        uuid_obj: ArtifactID = uuid4()
        assert isinstance(uuid_obj, UUID)

    def test_session_id_accepts_uuid(self):
        """UUID can be used where SessionID is expected."""
        uuid_obj: SessionID = uuid4()
        assert isinstance(uuid_obj, UUID)

    def test_chunk_id_accepts_uuid(self):
        """UUID can be used where ChunkID is expected."""
        uuid_obj: ChunkID = uuid4()
        assert isinstance(uuid_obj, UUID)

    def test_message_id_accepts_uuid(self):
        """UUID can be used where MessageID is expected."""
        uuid_obj: MessageID = uuid4()
        assert isinstance(uuid_obj, UUID)


class TestStringTypesAcceptString:
    """Verify string-based branded types accept string values directly."""

    def test_trace_id_accepts_string(self):
        """String can be used where TraceID is expected."""
        trace: TraceID = "langfuse-trace-12345"
        assert isinstance(trace, str)

    def test_topic_id_accepts_string(self):
        """String can be used where TopicID is expected."""
        topic: TopicID = "analysis-updates"
        assert isinstance(topic, str)


class TestNoConversionNeeded:
    """Verify Annotated types require no conversion at boundaries."""

    def test_uuid_flows_through_directly(self):
        """UUID values flow through without any conversion."""
        # Simulating data flow: API → Service → Repository
        raw_uuid = uuid4()

        # API layer receives UUID
        api_id: AnalysisID = raw_uuid

        # Service uses it directly
        service_id: AnalysisID = api_id

        # Repository receives same value
        repo_id: AnalysisID = service_id

        # All are the same object - no copies, no wrappers
        assert raw_uuid is api_id is service_id is repo_id

    def test_string_flows_through_directly(self):
        """String values flow through without any conversion."""
        raw_str = "trace-abc-123"

        trace_id: TraceID = raw_str

        # Same object throughout
        assert raw_str is trace_id


class TestFunctionSignatures:
    """Test that branded types work in function signatures."""

    def test_function_accepts_branded_uuid_type(self):
        """Function with branded UUID parameter works with UUID."""

        def process_analysis(analysis_id: AnalysisID) -> str:
            return str(analysis_id)

        uuid_obj = uuid4()
        result = process_analysis(uuid_obj)
        assert result == str(uuid_obj)

    def test_function_accepts_branded_string_type(self):
        """Function with branded string parameter works with str."""

        def log_trace(trace_id: TraceID) -> str:
            return f"Trace: {trace_id}"

        result = log_trace("my-trace-id")
        assert result == "Trace: my-trace-id"

    def test_function_returns_branded_type(self):
        """Function returning branded type works correctly."""

        def create_new_analysis() -> AnalysisID:
            return uuid4()

        result = create_new_analysis()
        assert isinstance(result, UUID)


class TestTypeDocumentation:
    """Test that Annotated types carry documentation metadata."""

    def test_analysis_id_has_label(self):
        """AnalysisID carries 'analysis_id' label."""
        args = get_args(AnalysisID)
        assert "analysis_id" in args

    def test_artifact_id_has_label(self):
        """ArtifactID carries 'artifact_id' label."""
        args = get_args(ArtifactID)
        assert "artifact_id" in args

    def test_session_id_has_label(self):
        """SessionID carries 'session_id' label."""
        args = get_args(SessionID)
        assert "session_id" in args

    def test_trace_id_has_label(self):
        """TraceID carries 'trace_id' label."""
        args = get_args(TraceID)
        assert "trace_id" in args


class TestRuntimeTransparency:
    """Verify Annotated types are transparent at runtime.

    This is the key benefit over NewType - no conversion needed because
    Annotated[UUID, ...] IS just UUID at runtime.
    """

    def test_annotated_uuid_is_uuid_at_runtime(self):
        """Annotated[UUID, ...] values are UUID at runtime."""
        analysis_id: AnalysisID = uuid4()
        artifact_id: ArtifactID = uuid4()

        # Both are exactly UUID type
        assert type(analysis_id) is UUID
        assert type(artifact_id) is UUID

    def test_annotated_str_is_str_at_runtime(self):
        """Annotated[str, ...] values are str at runtime."""
        trace_id: TraceID = "trace-123"
        topic_id: TopicID = "topic-456"

        # Both are exactly str type
        assert type(trace_id) is str
        assert type(topic_id) is str

    def test_no_isinstance_check_needed(self):
        """No special isinstance checks needed for Annotated types."""
        analysis_id: AnalysisID = uuid4()

        # Standard isinstance works
        assert isinstance(analysis_id, UUID)

        # Can use in collections expecting UUID
        uuid_list: list[UUID] = [analysis_id]
        assert len(uuid_list) == 1


class TestPydanticCompatibility:
    """Test that Annotated types work with Pydantic (conceptually)."""

    def test_uuid_serializes_to_string(self):
        """UUID values serialize to string for JSON."""
        analysis_id: AnalysisID = uuid4()

        # Standard UUID → str works
        json_value = str(analysis_id)
        assert isinstance(json_value, str)
        assert len(json_value) == 36  # UUID string length

    def test_uuid_from_string(self):
        """UUID can be created from string (Pydantic deserialization)."""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"

        # Standard str → UUID works
        analysis_id: AnalysisID = UUID(uuid_str)
        assert str(analysis_id) == uuid_str

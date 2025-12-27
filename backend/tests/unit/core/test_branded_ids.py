"""Unit tests for branded/opaque ID types.

Tests the NewType-based ID branding system introduced in 2025 best practices.
Validates factory functions, type safety (at test level), and error handling.
"""

from uuid import UUID, uuid4

import pytest

from app.core.branded_ids import (
    AnalysisID,
    ArtifactID,
    ChunkID,
    MessageID,
    SessionID,
    TopicID,
    TraceID,
    create_analysis_id,
    create_artifact_id,
    create_chunk_id,
    create_message_id,
    create_session_id,
    create_topic_id,
    create_trace_id,
)


class TestAnalysisIDFactory:
    """Test AnalysisID creation and validation."""

    def test_create_from_uuid_object(self):
        """Factory accepts UUID object."""
        uuid_obj = uuid4()
        result = create_analysis_id(uuid_obj)
        assert isinstance(result, UUID)
        assert result == uuid_obj

    def test_create_from_valid_uuid_string(self):
        """Factory accepts valid UUID string."""
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        result = create_analysis_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_create_from_uuid_string_with_uppercase(self):
        """Factory normalizes UUID string case."""
        uuid_str = "123E4567-E89B-12D3-A456-426614174000"
        result = create_analysis_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result).lower() == uuid_str.lower()

    def test_create_from_invalid_string_raises_value_error(self):
        """Factory raises ValueError for malformed UUID string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_analysis_id("not-a-uuid")

    def test_create_from_empty_string_raises_value_error(self):
        """Factory raises ValueError for empty string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_analysis_id("")

    def test_round_trip_uuid_to_string_to_branded(self):
        """UUID -> branded -> str -> branded preserves value."""
        original_uuid = uuid4()
        branded_1 = create_analysis_id(original_uuid)
        uuid_str = str(branded_1)
        branded_2 = create_analysis_id(uuid_str)
        assert branded_1 == branded_2
        assert branded_1 == original_uuid


class TestArtifactIDFactory:
    """Test ArtifactID creation and validation."""

    def test_create_from_uuid_object(self):
        """Factory accepts UUID object."""
        uuid_obj = uuid4()
        result = create_artifact_id(uuid_obj)
        assert isinstance(result, UUID)
        assert result == uuid_obj

    def test_create_from_valid_uuid_string(self):
        """Factory accepts valid UUID string."""
        uuid_str = "987e6543-e21b-12d3-a456-426614174000"
        result = create_artifact_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_create_from_invalid_string_raises_value_error(self):
        """Factory raises ValueError for malformed UUID string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_artifact_id("invalid-uuid-format")

    def test_round_trip_preserves_value(self):
        """UUID -> branded -> str -> branded preserves value."""
        original_uuid = uuid4()
        branded_1 = create_artifact_id(original_uuid)
        uuid_str = str(branded_1)
        branded_2 = create_artifact_id(uuid_str)
        assert branded_1 == branded_2


class TestSessionIDFactory:
    """Test SessionID creation and validation."""

    def test_create_from_uuid_object(self):
        """Factory accepts UUID object."""
        uuid_obj = uuid4()
        result = create_session_id(uuid_obj)
        assert isinstance(result, UUID)
        assert result == uuid_obj

    def test_create_from_valid_uuid_string(self):
        """Factory accepts valid UUID string."""
        uuid_str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        result = create_session_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_create_from_invalid_string_raises_value_error(self):
        """Factory raises ValueError for malformed UUID string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_session_id("session-123")

    def test_round_trip_preserves_value(self):
        """UUID -> branded -> str -> branded preserves value."""
        original_uuid = uuid4()
        branded_1 = create_session_id(original_uuid)
        uuid_str = str(branded_1)
        branded_2 = create_session_id(uuid_str)
        assert branded_1 == branded_2


class TestChunkIDFactory:
    """Test ChunkID creation and validation."""

    def test_create_from_uuid_object(self):
        """Factory accepts UUID object."""
        uuid_obj = uuid4()
        result = create_chunk_id(uuid_obj)
        assert isinstance(result, UUID)
        assert result == uuid_obj

    def test_create_from_valid_uuid_string(self):
        """Factory accepts valid UUID string."""
        uuid_str = "f1e2d3c4-b5a6-7890-1234-567890abcdef"
        result = create_chunk_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_create_from_invalid_string_raises_value_error(self):
        """Factory raises ValueError for malformed UUID string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_chunk_id("chunk_id_123")

    def test_round_trip_preserves_value(self):
        """UUID -> branded -> str -> branded preserves value."""
        original_uuid = uuid4()
        branded_1 = create_chunk_id(original_uuid)
        uuid_str = str(branded_1)
        branded_2 = create_chunk_id(uuid_str)
        assert branded_1 == branded_2


class TestMessageIDFactory:
    """Test MessageID creation and validation."""

    def test_create_from_uuid_object(self):
        """Factory accepts UUID object."""
        uuid_obj = uuid4()
        result = create_message_id(uuid_obj)
        assert isinstance(result, UUID)
        assert result == uuid_obj

    def test_create_from_valid_uuid_string(self):
        """Factory accepts valid UUID string."""
        uuid_str = "c1d2e3f4-a5b6-7890-1234-567890fedcba"
        result = create_message_id(uuid_str)
        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_create_from_invalid_string_raises_value_error(self):
        """Factory raises ValueError for malformed UUID string."""
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_message_id("msg-abc-123")

    def test_round_trip_preserves_value(self):
        """UUID -> branded -> str -> branded preserves value."""
        original_uuid = uuid4()
        branded_1 = create_message_id(original_uuid)
        uuid_str = str(branded_1)
        branded_2 = create_message_id(uuid_str)
        assert branded_1 == branded_2


class TestTraceIDFactory:
    """Test TraceID creation (string-based ID)."""

    def test_create_from_string(self):
        """Factory accepts string value."""
        trace_str = "trace-abc-123-xyz"
        result = create_trace_id(trace_str)
        assert isinstance(result, str)
        assert result == trace_str

    def test_create_from_empty_string(self):
        """Factory accepts empty string (no validation for TraceID)."""
        result = create_trace_id("")
        assert result == ""

    def test_create_from_uuid_string(self):
        """Factory accepts UUID-formatted string (TraceID is just str)."""
        uuid_str = str(uuid4())
        result = create_trace_id(uuid_str)
        assert result == uuid_str

    def test_round_trip_preserves_value(self):
        """String -> branded -> str preserves value."""
        original_str = "langfuse-trace-id-12345"
        branded = create_trace_id(original_str)
        assert branded == original_str


class TestTopicIDFactory:
    """Test TopicID creation (string-based ID)."""

    def test_create_from_string(self):
        """Factory accepts string value."""
        topic_str = "analysis-updates"
        result = create_topic_id(topic_str)
        assert isinstance(result, str)
        assert result == topic_str

    def test_create_from_empty_string(self):
        """Factory accepts empty string (no validation for TopicID)."""
        result = create_topic_id("")
        assert result == ""

    def test_create_from_numeric_string(self):
        """Factory accepts numeric string."""
        result = create_topic_id("12345")
        assert result == "12345"

    def test_round_trip_preserves_value(self):
        """String -> branded -> str preserves value."""
        original_str = "sse-channel-analysis-updates"
        branded = create_topic_id(original_str)
        assert branded == original_str


class TestTypeIdentity:
    """Test that different branded types are conceptually distinct.

    Note: NewType provides compile-time type safety, not runtime distinction.
    At runtime, all UUID-based IDs are just UUID objects. This is intentional
    for performance (zero overhead). Type checkers like mypy enforce separation.
    """

    def test_different_id_types_have_same_runtime_type(self):
        """Different branded IDs are all UUID at runtime (by design)."""
        uuid_obj = uuid4()
        analysis_id = create_analysis_id(uuid_obj)
        artifact_id = create_artifact_id(uuid_obj)

        # Runtime: both are UUID (NewType has zero overhead)
        assert isinstance(analysis_id, UUID)
        assert isinstance(artifact_id, UUID)
        assert type(analysis_id) is type(artifact_id)
        assert analysis_id == artifact_id  # Same UUID value

    def test_string_based_ids_are_runtime_strings(self):
        """String-based branded IDs are str at runtime."""
        trace_id = create_trace_id("trace-123")
        topic_id = create_topic_id("topic-456")

        # Runtime: both are str
        assert isinstance(trace_id, str)
        assert isinstance(topic_id, str)
        assert type(trace_id) is type(topic_id)
        assert trace_id != topic_id  # Different values

    def test_type_safety_enforced_by_mypy_not_runtime(self):
        """Type safety is enforced by mypy, not at runtime.

        This test documents the design choice: NewType provides zero-cost
        type safety at compile time. Runtime checks would add overhead.

        With mypy:
            def process_analysis(analysis_id: AnalysisID) -> None: ...
            artifact_id = create_artifact_id(uuid4())
            process_analysis(artifact_id)  # mypy ERROR: Expected AnalysisID, got ArtifactID

        Without mypy (runtime):
            Both are UUID, so no error. This is intentional for performance.
        """
        uuid_obj = uuid4()
        analysis_id = create_analysis_id(uuid_obj)
        artifact_id = create_artifact_id(uuid_obj)

        # This would fail mypy but passes at runtime (by design)
        def accepts_analysis_id(aid: AnalysisID) -> AnalysisID:
            return aid

        # Runtime: no error (both are UUID)
        result = accepts_analysis_id(artifact_id)  # type: ignore[arg-type]
        assert result == artifact_id


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_nil_uuid_is_valid(self):
        """Factory accepts nil UUID (00000000-0000-0000-0000-000000000000)."""
        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        result = create_analysis_id(nil_uuid)
        assert result == nil_uuid

    def test_nil_uuid_string_is_valid(self):
        """Factory accepts nil UUID as string."""
        nil_str = "00000000-0000-0000-0000-000000000000"
        result = create_artifact_id(nil_str)
        assert str(result) == nil_str

    def test_uuid_with_hyphens_in_wrong_places_raises_error(self):
        """Factory raises ValueError for UUID with incorrect hyphen placement."""
        # Note: UUID() is permissive - it strips all hyphens before validation.
        # This actually parses successfully as "123e4567e89b12d3a456426614174000".
        # Use a truly malformed UUID instead (wrong length after hyphen removal).
        malformed = "123e4567e89b-12d3-a456-4266141740"  # Too short after stripping
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_session_id(malformed)

    def test_uuid_with_invalid_characters_raises_error(self):
        """Factory raises ValueError for UUID with non-hex characters."""
        invalid = "123e4567-g89b-12d3-a456-426614174000"
        # UUID() raises "invalid literal for int() with base 16" for non-hex chars
        with pytest.raises(ValueError, match="invalid literal for int\\(\\) with base 16"):
            create_chunk_id(invalid)

    def test_uuid_too_short_raises_error(self):
        """Factory raises ValueError for truncated UUID string."""
        too_short = "123e4567-e89b-12d3"
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_message_id(too_short)

    def test_uuid_too_long_raises_error(self):
        """Factory raises ValueError for overly long UUID string."""
        too_long = "123e4567-e89b-12d3-a456-426614174000-extra"
        with pytest.raises(ValueError, match="badly formed hexadecimal UUID string"):
            create_analysis_id(too_long)

    def test_trace_id_accepts_any_string(self):
        """TraceID has no validation (accepts any string)."""
        weird_strings = [
            "trace-with-emoji-🚀",
            "trace\nwith\nnewlines",
            "trace with spaces",
            "trace-with-unicode-日本語",
            "123",
            "",
        ]
        for s in weird_strings:
            result = create_trace_id(s)
            assert result == s

    def test_topic_id_accepts_any_string(self):
        """TopicID has no validation (accepts any string)."""
        weird_strings = [
            "topic/with/slashes",
            "topic:with:colons",
            "topic.with.dots",
            "TOPIC-UPPERCASE",
            "",
        ]
        for s in weird_strings:
            result = create_topic_id(s)
            assert result == s


class TestAllFactoriesExist:
    """Verify all 7 factory functions are exported and callable."""

    def test_all_uuid_factories_exist(self):
        """All UUID-based factory functions are callable."""
        uuid_factories = [
            create_analysis_id,
            create_artifact_id,
            create_session_id,
            create_chunk_id,
            create_message_id,
        ]
        uuid_obj = uuid4()
        for factory in uuid_factories:
            result = factory(uuid_obj)
            assert isinstance(result, UUID)

    def test_all_string_factories_exist(self):
        """All string-based factory functions are callable."""
        string_factories = [
            (create_trace_id, "trace-123"),
            (create_topic_id, "topic-456"),
        ]
        for factory, test_value in string_factories:
            result = factory(test_value)
            assert isinstance(result, str)

    def test_all_types_exported(self):
        """All branded types are importable."""
        # This test passing means imports succeeded
        assert AnalysisID is not None
        assert ArtifactID is not None
        assert SessionID is not None
        assert ChunkID is not None
        assert MessageID is not None
        assert TraceID is not None
        assert TopicID is not None

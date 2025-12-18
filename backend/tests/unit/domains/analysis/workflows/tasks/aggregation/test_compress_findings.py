"""Unit tests for finding compression module.

Tests Phase 0 implementation of finding compression for multi-phase synthesis.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.tasks.aggregation.compress_findings import (
    COMPRESSION_SYSTEM_PROMPT,
    CompressedFinding,
    _create_fallback_compressed_finding,
    _format_findings_for_compression,
    _format_value,
    build_compression_user_prompt,
    compress_all_findings,
    compress_single_finding,
)


@pytest.mark.unit
class TestCompressedFinding:
    """Test CompressedFinding Pydantic model."""

    def test_valid_compressed_finding(self):
        """Test creating a valid CompressedFinding."""
        finding = CompressedFinding(
            agent_name="security_auditor",
            key_insights=["SQL injection risk in auth", "Missing rate limiting"],
            confidence=0.9,
            data_quality="high",
            critical_warnings=["Critical: SQL injection vulnerability"],
            relevant_code_snippets=["app.get('/login', auth_handler)"],
        )

        assert finding.agent_name == "security_auditor"
        assert len(finding.key_insights) == 2
        assert finding.confidence == 0.9
        assert finding.data_quality == "high"
        assert len(finding.critical_warnings) == 1
        assert len(finding.relevant_code_snippets) == 1

    def test_confidence_validation(self):
        """Test confidence score must be between 0 and 1."""
        # Valid confidence
        finding = CompressedFinding(
            agent_name="test",
            key_insights=["insight"],
            confidence=0.5,
            data_quality="medium",
        )
        assert finding.confidence == 0.5

        # Invalid confidence - too high
        with pytest.raises(Exception):  # Pydantic validation error
            CompressedFinding(
                agent_name="test",
                key_insights=["insight"],
                confidence=1.5,
                data_quality="medium",
            )

        # Invalid confidence - negative
        with pytest.raises(Exception):  # Pydantic validation error
            CompressedFinding(
                agent_name="test",
                key_insights=["insight"],
                confidence=-0.1,
                data_quality="medium",
            )

    def test_default_fields(self):
        """Test default values for optional fields."""
        finding = CompressedFinding(
            agent_name="test",
            key_insights=["insight"],
            confidence=0.7,
            data_quality="medium",
        )

        assert finding.critical_warnings == []
        assert finding.relevant_code_snippets == []


class TestFormatValue:
    """Test _format_value helper function."""

    def test_format_dict(self):
        """Test formatting dict values."""
        value = {"key1": "val1", "key2": "val2", "key3": "val3"}
        result = _format_value(value)
        assert "{" in result
        assert "key1" in result

    def test_format_list(self):
        """Test formatting list values."""
        value = ["item1", "item2", "item3"]
        result = _format_value(value)
        assert result == "[3 items]"

    def test_format_string(self):
        """Test formatting string values."""
        value = "short string"
        result = _format_value(value)
        assert result == "short string"

    def test_format_long_string(self):
        """Test truncation of long strings."""
        value = "x" * 600
        result = _format_value(value)
        # Issue #299-304: Updated from 200 to 500 to preserve analytical depth
        assert len(result) == 500  # 497 chars + "..."
        assert result.endswith("...")


class TestFormatFindingsForCompression:
    """Test _format_findings_for_compression function."""

    def test_format_empty_findings(self):
        """Test formatting empty/None findings."""
        assert _format_findings_for_compression(None) == "No findings available"
        assert _format_findings_for_compression({}) == "No findings available"

    def test_format_dict_findings(self):
        """Test formatting dict findings."""
        findings = {
            "security_risks": [{"risk": "SQL injection"}, {"risk": "XSS"}],
            "summary": "Found 2 critical issues",
            "recommendation": "Implement input validation",
        }
        result = _format_findings_for_compression(findings)

        assert "security_risks: 2 items" in result
        assert "summary:" in result
        assert "recommendation:" in result

    def test_format_list_findings(self):
        """Test formatting list findings."""
        findings = ["finding 1", "finding 2", "finding 3"]
        result = _format_findings_for_compression(findings)

        assert "1. finding 1" in result
        assert "2. finding 2" in result
        assert "3. finding 3" in result

    def test_format_list_truncation(self):
        """Test list truncation at 10 items."""
        findings = [f"item {i}" for i in range(20)]
        result = _format_findings_for_compression(findings)

        assert "1. item 0" in result
        assert "10. item 9" in result
        assert "... and 10 more items" in result

    def test_format_string_findings(self):
        """Test formatting string findings."""
        findings = "This is a simple string finding"
        result = _format_findings_for_compression(findings)
        assert result == findings

    def test_format_long_string_truncation(self):
        """Test string truncation at 2000 chars."""
        findings = "x" * 3000
        result = _format_findings_for_compression(findings)
        assert len(result) == 2000


class TestBuildCompressionUserPrompt:
    """Test build_compression_user_prompt function."""

    def test_build_prompt_with_complete_finding(self):
        """Test building prompt with complete finding data."""
        agent_name = "security_auditor"
        finding = {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": ["SQL injection", "XSS"],
                "summary": "Found critical vulnerabilities",
            },
            "confidence_score": 0.95,
            "data_availability": "sufficient",
        }

        prompt = build_compression_user_prompt(agent_name, finding)

        assert "Agent: security_auditor" in prompt
        assert "Confidence Score: 0.95" in prompt
        assert "Data Availability: sufficient" in prompt
        assert "security_risks" in prompt

    def test_build_prompt_with_minimal_finding(self):
        """Test building prompt with minimal finding data."""
        agent_name = "test_agent"
        finding = {}  # Empty finding

        prompt = build_compression_user_prompt(agent_name, finding)

        assert "Agent: test_agent" in prompt
        assert "Confidence Score: 0.5" in prompt  # Default
        assert "Data Availability: unknown" in prompt  # Default
        assert "No findings available" in prompt

    def test_build_prompt_includes_instructions(self):
        """Test prompt includes extraction instructions."""
        finding = {
            "findings": {"key": "value"},
            "confidence_score": 0.8,
        }
        prompt = build_compression_user_prompt("test", finding)

        assert "CompressedFinding" in prompt
        assert "actionable" in prompt


class TestCreateFallbackCompressedFinding:
    """Test fallback compressed finding creation."""

    def test_fallback_with_dict_findings(self):
        """Test fallback creation with dict findings."""
        agent_name = "security_auditor"
        finding = {
            "findings": {
                "security_risks": ["risk1", "risk2"],
                "summary": "Security analysis complete",
            },
            "confidence_score": 0.7,
            "data_availability": "sufficient",
        }

        fallback = _create_fallback_compressed_finding(agent_name, finding)

        assert fallback.agent_name == "security_auditor"
        assert fallback.confidence == 0.7
        assert fallback.data_quality == "high"  # sufficient -> high
        assert len(fallback.key_insights) > 0
        assert fallback.critical_warnings == []
        assert fallback.relevant_code_snippets == []

    def test_fallback_with_empty_findings(self):
        """Test fallback creation with empty findings."""
        agent_name = "test_agent"
        finding = {}

        fallback = _create_fallback_compressed_finding(agent_name, finding)

        assert fallback.agent_name == "test_agent"
        assert fallback.confidence == 0.5  # Default
        assert fallback.data_quality == "low"  # unknown -> low
        assert len(fallback.key_insights) > 0

    def test_fallback_data_quality_mapping(self):
        """Test data_availability to data_quality mapping."""
        test_cases = [
            ("sufficient", "high"),
            ("limited", "medium"),
            ("insufficient", "low"),
            ("unknown", "low"),
        ]

        for availability, expected_quality in test_cases:
            finding = {
                "confidence_score": 0.5,
                "data_availability": availability,
            }
            fallback = _create_fallback_compressed_finding("test", finding)
            assert fallback.data_quality == expected_quality


@pytest.mark.asyncio
class TestCompressSingleFinding:
    """Test compress_single_finding function."""

    async def test_compress_single_finding_success(self):
        """Test successful compression of a single finding."""
        agent_name = "security_auditor"
        finding = {
            "findings": {"security_risks": ["SQL injection"]},
            "confidence_score": 0.9,
            "data_availability": "sufficient",
        }
        analysis_id = "test-analysis-123"

        # Mock LLM to return CompressedFinding
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value={
                "agent_name": agent_name,
                "key_insights": ["SQL injection found"],
                "confidence": 0.9,
                "data_quality": "high",
                "critical_warnings": ["Critical SQL vulnerability"],
                "relevant_code_snippets": [],
            }
        )

        # Patch asyncio.timeout to prevent actual timeout
        with patch(
            "app.domains.analysis.workflows.tasks.aggregation.compress_findings.asyncio.timeout"
        ):
            result = await compress_single_finding(
                agent_name=agent_name,
                finding=finding,
                llm=mock_llm,
                analysis_id=analysis_id,
            )

        assert isinstance(result, CompressedFinding)
        assert result.agent_name == agent_name
        assert result.confidence == 0.9
        assert len(result.key_insights) > 0

    async def test_compress_single_finding_timeout(self):
        """Test compression with timeout."""
        agent_name = "test_agent"
        finding = {"findings": {}, "confidence_score": 0.5}
        analysis_id = "test-analysis-123"

        # Mock LLM to raise TimeoutError
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Compression timeout"))

        # Patch asyncio.timeout to allow TimeoutError to propagate
        with patch(
            "app.domains.analysis.workflows.tasks.aggregation.compress_findings.asyncio.timeout"
        ) as mock_timeout:
            # Make timeout context manager raise TimeoutError
            mock_timeout.return_value.__aenter__ = AsyncMock()
            mock_timeout.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(TimeoutError):
                await compress_single_finding(
                    agent_name=agent_name,
                    finding=finding,
                    llm=mock_llm,
                    analysis_id=analysis_id,
                )


@pytest.mark.asyncio
class TestCompressAllFindings:
    """Test compress_all_findings function."""

    async def test_compress_all_findings_success(self):
        """Test successful compression of all findings."""
        agent_findings = {
            "security_auditor": {
                "findings": {"security_risks": ["SQL injection"]},
                "confidence_score": 0.9,
            },
            "tech_comparator": {
                "findings": {"primary_tech": "FastAPI"},
                "confidence_score": 0.8,
            },
        }
        analysis_id = "test-analysis-123"

        # Mock get_chat_model
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with (
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model",
                return_value=mock_llm,
            ),
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.compress_single_finding",
                return_value=CompressedFinding(
                    agent_name="test",
                    key_insights=["insight"],
                    confidence=0.8,
                    data_quality="high",
                ),
            ),
        ):
            results = await compress_all_findings(agent_findings, analysis_id)

        assert len(results) == 2
        assert all(isinstance(r, CompressedFinding) for r in results)

    async def test_compress_all_findings_empty(self):
        """Test compression with no findings."""
        agent_findings = {}
        analysis_id = "test-analysis-123"

        results = await compress_all_findings(agent_findings, analysis_id)

        assert results == []

    async def test_compress_all_findings_partial_failure(self):
        """Test compression when some agents fail."""
        agent_findings = {
            "agent1": {"findings": {}, "confidence_score": 0.8},
            "agent2": {"findings": {}, "confidence_score": 0.7},
        }
        analysis_id = "test-analysis-123"

        # Mock one success, one failure
        async def mock_compress(agent_name, finding, llm, analysis_id):
            if agent_name == "agent1":
                return CompressedFinding(
                    agent_name=agent_name,
                    key_insights=["insight"],
                    confidence=0.8,
                    data_quality="high",
                )
            raise Exception("Compression failed")

        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        with (
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model",
                return_value=mock_llm,
            ),
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.compress_single_finding",
                side_effect=mock_compress,
            ),
        ):
            results = await compress_all_findings(agent_findings, analysis_id)

        # Should still return 2 results (1 success, 1 fallback)
        assert len(results) == 2
        assert all(isinstance(r, CompressedFinding) for r in results)

    async def test_compress_all_findings_model_fallback(self):
        """Test fallback to settings model when primary compression model fails."""
        agent_findings = {
            "agent1": {"findings": {}, "confidence_score": 0.8},
        }
        analysis_id = "test-analysis-123"

        # Mock primary model failure, fallback success
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured_llm

        call_count = [0]

        def mock_get_chat_model(config=None):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (primary model) - fail
                raise Exception("Primary model not available")
            # Second call (fallback model) - succeed
            return mock_llm

        with (
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.get_chat_model",
                side_effect=mock_get_chat_model,
            ),
            patch(
                "app.domains.analysis.workflows.tasks.aggregation.compress_findings.compress_single_finding",
                return_value=CompressedFinding(
                    agent_name="agent1",
                    key_insights=["insight"],
                    confidence=0.8,
                    data_quality="high",
                ),
            ),
        ):
            results = await compress_all_findings(agent_findings, analysis_id)

        assert len(results) == 1
        # Should have tried primary model then fallback
        assert call_count[0] == 2


class TestCompressionSystemPrompt:
    """Test COMPRESSION_SYSTEM_PROMPT constant."""

    def test_system_prompt_contains_instructions(self):
        """Test system prompt contains key instructions."""
        prompt = COMPRESSION_SYSTEM_PROMPT

        assert "key_insights" in prompt
        assert "confidence" in prompt
        assert "data_quality" in prompt
        assert "critical_warnings" in prompt
        assert "relevant_code_snippets" in prompt
        assert "CompressedFinding" in prompt

    def test_system_prompt_mentions_conciseness(self):
        """Test prompt emphasizes conciseness."""
        prompt = COMPRESSION_SYSTEM_PROMPT

        assert "concise" in prompt.lower() or "500 words" in prompt

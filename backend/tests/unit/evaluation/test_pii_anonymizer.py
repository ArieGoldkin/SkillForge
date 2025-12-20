"""Unit tests for PII Anonymizer.

Tests cover:
- Basic anonymization functionality
- Allowlist handling (safe domains/emails)
- Private IP preservation
- Batch processing
- Dictionary field anonymization
- Sensitivity level configuration
- Placeholder consistency
"""

import pytest

from app.evaluation.ingestion.pii_anonymizer import (
    ALLOWLISTED_EMAILS,
    AnonymizedResult,
    PIIAnonymizer,
    PIIReplacement,
    get_anonymizer,
)
from app.shared.services.pii.types import PIIType, SensitivityLevel


@pytest.mark.unit
class TestAnonymizedResult:
    """Tests for AnonymizedResult dataclass."""

    def test_result_defaults(self):
        """Test AnonymizedResult has correct defaults."""
        result = AnonymizedResult(text="test")
        assert result.text == "test"
        assert result.replacements == []
        assert result.pii_count == 0
        assert result.skipped_allowlisted == 0
        assert result.has_pii is False
        assert result.types_found == []

    def test_result_with_replacements(self):
        """Test AnonymizedResult with actual replacements."""
        replacements = [
            PIIReplacement(
                pii_type=PIIType.EMAIL,
                start=0,
                end=15,
                placeholder="[EMAIL_1]",
            ),
            PIIReplacement(
                pii_type=PIIType.PHONE_US,
                start=20,
                end=32,
                placeholder="[PHONE_1]",
            ),
        ]
        result = AnonymizedResult(
            text="[EMAIL_1] call [PHONE_1]",
            replacements=replacements,
            pii_count=2,
            skipped_allowlisted=1,
        )
        assert result.has_pii is True
        assert len(result.types_found) == 2
        assert PIIType.EMAIL in result.types_found
        assert PIIType.PHONE_US in result.types_found

    def test_to_metadata(self):
        """Test metadata conversion."""
        result = AnonymizedResult(
            text="anonymized",
            replacements=[
                PIIReplacement(PIIType.EMAIL, 0, 10, "[EMAIL_1]"),
            ],
            pii_count=1,
            skipped_allowlisted=2,
        )
        metadata = result.to_metadata()
        assert metadata["pii_anonymized"] is True
        assert metadata["pii_count"] == 1
        assert metadata["pii_types"] == ["email"]
        assert metadata["skipped_allowlisted"] == 2


class TestPIIAnonymizerBasic:
    """Tests for basic anonymization functionality."""

    @pytest.fixture
    def anonymizer(self):
        """Create a high-sensitivity anonymizer."""
        return PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)

    def test_anonymize_email(self, anonymizer):
        """Test email anonymization."""
        text = "Contact john.doe@company.com for support"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert result.pii_count == 1
        assert "[EMAIL_1]" in result.text
        assert "john.doe@company.com" not in result.text
        assert PIIType.EMAIL in result.types_found

    def test_anonymize_phone_us(self, anonymizer):
        """Test US phone number anonymization."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert result.pii_count == 2
        assert "[PHONE_1]" in result.text
        assert "[PHONE_2]" in result.text
        assert "555-123-4567" not in result.text

    def test_anonymize_ssn(self, anonymizer):
        """Test SSN anonymization."""
        text = "SSN: 123-45-6789"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[SSN_1]" in result.text
        assert "123-45-6789" not in result.text

    def test_anonymize_credit_card(self, anonymizer):
        """Test credit card anonymization."""
        text = "Card: 4111111111111111"  # Visa test number
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[CARD_1]" in result.text
        assert "4111111111111111" not in result.text

    def test_anonymize_ipv4(self, anonymizer):
        """Test public IPv4 anonymization."""
        text = "Server at 8.8.8.8 is responding"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[IP_1]" in result.text
        assert "8.8.8.8" not in result.text

    def test_anonymize_aws_key(self, anonymizer):
        """Test AWS key anonymization."""
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[AWS_KEY_1]" in result.text
        assert "AKIAIOSFODNN7EXAMPLE" not in result.text

    def test_anonymize_github_token(self, anonymizer):
        """Test GitHub token anonymization."""
        text = "Token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[GH_TOKEN_1]" in result.text

    def test_anonymize_stripe_key(self, anonymizer):
        """Test Stripe key anonymization."""
        text = "Stripe: sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert "[STRIPE_KEY_1]" in result.text

    def test_anonymize_empty_text(self, anonymizer):
        """Test handling of empty text."""
        result = anonymizer.anonymize("")
        assert result.text == ""
        assert result.has_pii is False

    def test_anonymize_no_pii(self, anonymizer):
        """Test text with no PII."""
        text = "This is a normal sentence without any sensitive data."
        result = anonymizer.anonymize(text)

        assert result.text == text
        assert result.has_pii is False
        assert result.pii_count == 0

    def test_consistent_placeholder(self, anonymizer):
        """Test that same PII gets same placeholder."""
        text = "Email john@test.org, then email john@test.org again"
        result = anonymizer.anonymize(text)

        # Same email should get same placeholder
        assert result.text.count("[EMAIL_1]") == 2
        assert "[EMAIL_2]" not in result.text

    def test_multiple_types(self, anonymizer):
        """Test anonymization of multiple PII types."""
        text = "Contact john@corp.com at 555-123-4567, IP: 203.0.113.1"
        result = anonymizer.anonymize(text)

        assert result.has_pii is True
        assert result.pii_count == 3
        assert "[EMAIL_1]" in result.text
        assert "[PHONE_1]" in result.text
        assert "[IP_1]" in result.text


class TestPIIAnonymizerAllowlist:
    """Tests for allowlist functionality."""

    @pytest.fixture
    def anonymizer(self):
        """Create anonymizer with default allowlist."""
        return PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)

    def test_allowlisted_email_preserved(self, anonymizer):
        """Test that allowlisted emails are not anonymized."""
        for email in list(ALLOWLISTED_EMAILS)[:3]:
            text = f"Contact {email} for help"
            result = anonymizer.anonymize(text)

            assert email in result.text
            assert result.skipped_allowlisted >= 1

    def test_allowlisted_domain_preserved(self, anonymizer):
        """Test that emails with allowlisted domains are preserved."""
        text = "Email custom@example.com for testing"
        result = anonymizer.anonymize(text)

        assert "custom@example.com" in result.text
        assert result.skipped_allowlisted == 1

    def test_private_ip_preserved(self, anonymizer):
        """Test that private IPs are not anonymized."""
        private_ips = [
            "127.0.0.1",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "0.0.0.0",
        ]
        for ip in private_ips:
            text = f"Server at {ip}"
            result = anonymizer.anonymize(text)

            assert ip in result.text, f"Private IP {ip} should be preserved"
            assert result.skipped_allowlisted >= 1

    def test_public_ip_anonymized(self, anonymizer):
        """Test that public IPs are anonymized."""
        text = "Google DNS: 8.8.8.8"
        result = anonymizer.anonymize(text)

        assert "8.8.8.8" not in result.text
        assert "[IP_1]" in result.text

    def test_custom_allowlist(self):
        """Test custom allowlist additions."""
        custom = {"internal@mycompany.com", "safe@internal.net"}
        anonymizer = PIIAnonymizer(
            sensitivity=SensitivityLevel.HIGH,
            custom_allowlist=custom,
        )

        text = "Contact internal@mycompany.com for help"
        result = anonymizer.anonymize(text)

        assert "internal@mycompany.com" in result.text


class TestPIIAnonymizerSensitivity:
    """Tests for sensitivity level configuration."""

    def test_low_sensitivity_email_only(self):
        """Test LOW sensitivity only detects email."""
        anonymizer = PIIAnonymizer(sensitivity=SensitivityLevel.LOW)
        text = "Email: john@corp.com, Phone: 555-123-4567, SSN: 123-45-6789"
        result = anonymizer.anonymize(text)

        # Email should be anonymized
        assert "[EMAIL_1]" in result.text
        # Phone and SSN should remain (not detected at LOW)
        assert "555-123-4567" in result.text
        assert "123-45-6789" in result.text

    def test_medium_sensitivity(self):
        """Test MEDIUM sensitivity detects common PII."""
        anonymizer = PIIAnonymizer(sensitivity=SensitivityLevel.MEDIUM)
        text = "Email: john@corp.com, Phone: 555-123-4567, AWS: AKIAIOSFODNN7EXAMPLE"
        result = anonymizer.anonymize(text)

        # Email and phone should be anonymized
        assert "[EMAIL_1]" in result.text
        assert "[PHONE_1]" in result.text
        # AWS key should remain (not detected at MEDIUM)
        assert "AKIAIOSFODNN7EXAMPLE" in result.text

    def test_high_sensitivity_all_regex(self):
        """Test HIGH sensitivity detects all regex patterns."""
        anonymizer = PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)
        text = "Email: john@corp.com, AWS: AKIAIOSFODNN7EXAMPLE"
        result = anonymizer.anonymize(text)

        # Both should be anonymized
        assert "[EMAIL_1]" in result.text
        assert "[AWS_KEY_1]" in result.text


class TestPIIAnonymizerBatch:
    """Tests for batch processing."""

    @pytest.fixture
    def anonymizer(self):
        """Create anonymizer."""
        return PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)

    def test_anonymize_batch(self, anonymizer):
        """Test batch anonymization of multiple texts."""
        texts = [
            "Email john@corp.com",
            "Call 555-123-4567",
            "No PII here",
        ]
        results = anonymizer.anonymize_batch(texts)

        assert len(results) == 3
        assert "[EMAIL_1]" in results[0].text
        assert "[PHONE_1]" in results[1].text
        assert results[2].text == "No PII here"

    def test_anonymize_batch_empty(self, anonymizer):
        """Test batch with empty list."""
        results = anonymizer.anonymize_batch([])
        assert results == []


class TestPIIAnonymizerDict:
    """Tests for dictionary field anonymization."""

    @pytest.fixture
    def anonymizer(self):
        """Create anonymizer."""
        return PIIAnonymizer(sensitivity=SensitivityLevel.HIGH)

    def test_anonymize_dict_all_fields(self, anonymizer):
        """Test anonymizing all string fields in a dict."""
        data = {
            "title": "Contact john@corp.com",
            "body": "Call 555-123-4567",
            "count": 42,  # Non-string, should be ignored
        }
        result, replacements = anonymizer.anonymize_dict(data)

        assert "[EMAIL_1]" in result["title"]
        assert "[PHONE_1]" in result["body"]
        assert result["count"] == 42
        assert len(replacements) == 2

    def test_anonymize_dict_specific_fields(self, anonymizer):
        """Test anonymizing specific fields only."""
        data = {
            "title": "Contact john@corp.com",
            "body": "Call 555-123-4567",
        }
        result, replacements = anonymizer.anonymize_dict(data, fields=["title"])

        assert "[EMAIL_1]" in result["title"]
        # Body should be unchanged
        assert "555-123-4567" in result["body"]
        assert len(replacements) == 1

    def test_anonymize_dict_empty(self, anonymizer):
        """Test anonymizing empty dict."""
        result, replacements = anonymizer.anonymize_dict({})
        assert result == {}
        assert replacements == []


class TestGetAnonymizer:
    """Tests for get_anonymizer factory function."""

    def test_get_anonymizer_default(self):
        """Test getting default anonymizer."""
        anonymizer = get_anonymizer()
        assert anonymizer.sensitivity == SensitivityLevel.HIGH

    def test_get_anonymizer_cached(self):
        """Test that anonymizers are cached by sensitivity."""
        anon1 = get_anonymizer(SensitivityLevel.HIGH)
        anon2 = get_anonymizer(SensitivityLevel.HIGH)
        assert anon1 is anon2

    def test_get_anonymizer_different_sensitivity(self):
        """Test different sensitivities return different instances."""
        anon_high = get_anonymizer(SensitivityLevel.HIGH)
        anon_low = get_anonymizer(SensitivityLevel.LOW)
        assert anon_high is not anon_low
        assert anon_high.sensitivity == SensitivityLevel.HIGH
        assert anon_low.sensitivity == SensitivityLevel.LOW


class TestPIIReplacement:
    """Tests for PIIReplacement dataclass."""

    def test_replacement_creation(self):
        """Test PIIReplacement creation."""
        replacement = PIIReplacement(
            pii_type=PIIType.EMAIL,
            start=10,
            end=25,
            placeholder="[EMAIL_1]",
        )
        assert replacement.pii_type == PIIType.EMAIL
        assert replacement.start == 10
        assert replacement.end == 25
        assert replacement.placeholder == "[EMAIL_1]"

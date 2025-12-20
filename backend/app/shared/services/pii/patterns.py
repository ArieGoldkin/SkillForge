"""PII detection regex patterns.

These patterns are designed for high recall (catch most PII) with
reasonable precision. False positives are acceptable since we only
flag content, not redact it.

SECURITY: All patterns are pre-compiled for performance.
"""

from __future__ import annotations

import re
from typing import Final

# Pre-compiled patterns for performance
PII_PATTERNS: Final[dict[str, re.Pattern]] = {
    # Email: RFC 5322 simplified
    "email": re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    ),
    # US Phone: (555) 123-4567, 555-123-4567, +1 555 123 4567
    "phone_us": re.compile(r"\b(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # International Phone: +44 20 7123 4567, +49 30 12345678
    "phone_intl": re.compile(r"\+(?:[0-9][-.\s]?){6,14}[0-9]"),
    # SSN: 123-45-6789, 123 45 6789
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    # Credit Card: Visa, Mastercard, Amex, Discover
    "credit_card": re.compile(
        r"\b(?:"
        r"4[0-9]{12}(?:[0-9]{3})?"  # Visa
        r"|5[1-5][0-9]{14}"  # Mastercard
        r"|3[47][0-9]{13}"  # Amex
        r"|6(?:011|5[0-9]{2})[0-9]{12}"  # Discover
        r")\b"
    ),
    # IPv4: 192.168.1.1
    "ipv4": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ),
    # IPv6: Simplified pattern
    "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
    # AWS Access Key ID (20 chars total: 4 char prefix + 16 chars)
    "aws_key": re.compile(r"\b(?:AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
    # GitHub Personal Access Token
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}\b"),
    # Stripe API Key
    "stripe_key": re.compile(r"\b(?:sk|pk)_(?:live|test)_[a-zA-Z0-9]{24,}\b"),
}


# Mapping from pattern name to PIIType enum value
PATTERN_TO_TYPE: Final[dict[str, str]] = {
    "email": "email",
    "phone_us": "phone_us",
    "phone_intl": "phone_intl",
    "ssn": "ssn",
    "credit_card": "credit_card",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "aws_key": "aws_key",
    "github_token": "github_token",
    "stripe_key": "stripe_key",
}


# Patterns enabled at each sensitivity level
SENSITIVITY_PATTERNS: Final[dict[str, list[str]]] = {
    "low": ["email"],
    "medium": ["email", "phone_us", "phone_intl", "ssn", "credit_card"],
    "high": [
        "email",
        "phone_us",
        "phone_intl",
        "ssn",
        "credit_card",
        "ipv4",
        "ipv6",
        "aws_key",
        "github_token",
        "stripe_key",
    ],
    "maximum": [
        "email",
        "phone_us",
        "phone_intl",
        "ssn",
        "credit_card",
        "ipv4",
        "ipv6",
        "aws_key",
        "github_token",
        "stripe_key",
    ],  # Plus Presidio NER (future implementation)
}

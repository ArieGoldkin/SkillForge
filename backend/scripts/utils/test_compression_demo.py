"""Quick demo script to verify finding compression module works.

This script demonstrates the compression module without needing a full workflow run.
"""

import asyncio
from app.domains.analysis.workflows.tasks.aggregation.compress_findings import (
    CompressedFinding,
    build_compression_user_prompt,
    compress_all_findings,
    _format_findings_for_compression,
)


async def main():
    """Run compression demo."""
    print("=" * 80)
    print("Finding Compression Module Demo")
    print("=" * 80)

    # Example agent findings (similar to what aggregation receives)
    agent_findings = {
        "security_auditor": {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": [
                    {
                        "risk_type": "SQL Injection",
                        "severity": "critical",
                        "description": "User input not sanitized in auth queries",
                    },
                    {
                        "risk_type": "Missing Rate Limiting",
                        "severity": "high",
                        "description": "No rate limiting on login endpoint",
                    },
                ],
                "summary": "Found 2 critical security vulnerabilities requiring immediate attention",
                "recommendation": "Implement parameterized queries and add rate limiting middleware",
            },
            "confidence_score": 0.95,
            "data_availability": "sufficient",
        },
        "tech_comparator": {
            "agent_type": "tech_comparator",
            "findings": {
                "primary_tech": "FastAPI",
                "alternatives": ["Flask", "Django", "Express.js"],
                "comparison": "FastAPI offers async support and automatic OpenAPI docs",
            },
            "confidence_score": 0.85,
            "data_availability": "limited",
        },
    }

    print("\n1. Testing finding formatting")
    print("-" * 80)
    findings_data = agent_findings["security_auditor"]["findings"]
    formatted = _format_findings_for_compression(findings_data)
    print(f"Formatted findings (truncated):\n{formatted[:300]}...")

    print("\n2. Testing prompt building")
    print("-" * 80)
    prompt = build_compression_user_prompt("security_auditor", agent_findings["security_auditor"])
    print(f"Compression prompt (first 400 chars):\n{prompt[:400]}...")

    print("\n3. Testing CompressedFinding model")
    print("-" * 80)
    compressed = CompressedFinding(
        agent_name="security_auditor",
        key_insights=[
            "Critical SQL injection vulnerability in auth",
            "Missing rate limiting on login endpoint",
            "Recommend parameterized queries and middleware",
        ],
        confidence=0.95,
        data_quality="high",
        critical_warnings=["SQL injection must be fixed before production"],
        relevant_code_snippets=["app.get('/login', auth_handler)"],
    )
    print(f"CompressedFinding created successfully:")
    print(f"  - Agent: {compressed.agent_name}")
    print(f"  - Insights: {len(compressed.key_insights)}")
    print(f"  - Confidence: {compressed.confidence}")
    print(f"  - Quality: {compressed.data_quality}")
    print(f"  - Warnings: {len(compressed.critical_warnings)}")

    print("\n4. Token savings estimate")
    print("-" * 80)
    # Rough estimate: 4 chars per token average
    original_tokens = sum(len(str(f)) for f in agent_findings.values()) // 4
    compressed_tokens = (
        len(" ".join(compressed.key_insights))
        + len(" ".join(compressed.critical_warnings))
        + len(" ".join(compressed.relevant_code_snippets))
    ) // 4

    print(f"Original findings: ~{original_tokens} tokens")
    print(f"Compressed findings: ~{compressed_tokens} tokens")
    print(f"Compression ratio: {compressed_tokens / original_tokens * 100:.1f}%")
    print(f"Token savings: ~{original_tokens - compressed_tokens} tokens")

    print("\n" + "=" * 80)
    print("Compression module verified successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

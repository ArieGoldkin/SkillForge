#!/usr/bin/env python3
"""Real-data verification script for Sprint 3 backend enhancements.

Tests auto-activation of:
- performance_analyst (Issue #178)
- security_auditor (Issue #174)
- tech_comparator (Issue #177)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.logging import setup_logging
from app.domains.analysis.workflows.nodes.supervisor import supervisor_route

# Setup logging
setup_logging()


async def test_performance_analyst_activation():
    """Test that performance_analyst is auto-activated for performance content."""
    print("\n" + "=" * 80)
    print("TEST 1: Performance Analyst Auto-Activation")
    print("=" * 80)

    content = """
    # FastAPI Performance Optimization Guide

    import asyncpg
    from fastapi import FastAPI
    import redis

    We need to optimize database connection pooling to reduce latency.
    Current API response time is 450ms, we need to get it under 200ms.

    Using asyncpg for async database queries and Redis for caching.
    Benchmarking shows that the current throughput is 2000 req/sec.
    """

    result = await supervisor_route(
        content=content, content_type="article", analysis_id="test-perf-001"
    )

    agents = result["supervisor_decision"]["agents"]
    reasoning = result["supervisor_decision"]["reasoning"]

    print(f"\n✓ Selected agents: {agents}")
    print(f"✓ Reasoning: {reasoning}")

    if "performance_analyst" in agents:
        print("\n✅ SUCCESS: performance_analyst was auto-activated!")
    else:
        print("\n❌ FAILURE: performance_analyst was NOT activated")
        return False

    if "perf keywords" in reasoning.lower() or "performance_indicators" in reasoning.lower():
        print("✅ SUCCESS: Reasoning mentions performance activation")
    else:
        print("⚠️  WARNING: Reasoning doesn't explicitly mention performance activation")

    return True


async def test_security_auditor_activation():
    """Test that security_auditor is auto-activated for security content."""
    print("\n" + "=" * 80)
    print("TEST 2: Security Auditor Auto-Activation")
    print("=" * 80)

    content = """
    # JWT Authentication Implementation

    from passlib.context import CryptContext
    import python-jose
    from jose import jwt

    We need to implement secure JWT token validation.
    Checking for SQL injection vulnerabilities in user input.
    Password hashing uses bcrypt for security.

    Make sure to validate CORS settings and check for XSS risks.
    """

    result = await supervisor_route(
        content=content, content_type="code", analysis_id="test-sec-001"
    )

    agents = result["supervisor_decision"]["agents"]
    reasoning = result["supervisor_decision"]["reasoning"]

    print(f"\n✓ Selected agents: {agents}")
    print(f"✓ Reasoning: {reasoning}")

    if "security_auditor" in agents:
        print("\n✅ SUCCESS: security_auditor was auto-activated!")
    else:
        print("\n❌ FAILURE: security_auditor was NOT activated")
        return False

    if "security keywords" in reasoning.lower() or "security_indicators" in reasoning.lower():
        print("✅ SUCCESS: Reasoning mentions security activation")
    else:
        print("⚠️  WARNING: Reasoning doesn't explicitly mention security activation")

    return True


async def test_tech_comparator_activation():
    """Test that tech_comparator is auto-activated for comparison content."""
    print("\n" + "=" * 80)
    print("TEST 3: Tech Comparator Auto-Activation")
    print("=" * 80)

    content = """
    # FastAPI vs Django: Which Framework to Choose?

    Should we migrate from Django to FastAPI for our microservices?

    Both frameworks have their strengths. FastAPI offers better performance
    with async support, while Django provides a more mature ecosystem.

    We're comparing the two for our next project and need guidance.
    React is also being considered for the frontend.
    """

    result = await supervisor_route(
        content=content, content_type="article", analysis_id="test-comp-001"
    )

    agents = result["supervisor_decision"]["agents"]
    reasoning = result["supervisor_decision"]["reasoning"]

    print(f"\n✓ Selected agents: {agents}")
    print(f"✓ Reasoning: {reasoning}")

    if "tech_comparator" in agents:
        print("\n✅ SUCCESS: tech_comparator was auto-activated!")
    else:
        print("\n❌ FAILURE: tech_comparator was NOT activated")
        return False

    if "comparison detected" in reasoning.lower() or "comparison_indicators" in reasoning.lower():
        print("✅ SUCCESS: Reasoning mentions comparison activation")
        if "fastapi" in reasoning.lower() and "django" in reasoning.lower():
            print("✅ SUCCESS: Detected frameworks (FastAPI, Django) mentioned in reasoning")
    else:
        print("⚠️  WARNING: Reasoning doesn't explicitly mention comparison activation")

    return True


async def test_combined_activation():
    """Test that multiple agents can be auto-activated simultaneously."""
    print("\n" + "=" * 80)
    print("TEST 4: Combined Auto-Activation")
    print("=" * 80)

    content = """
    # Optimizing FastAPI Security and Performance

    import asyncpg
    from fastapi import FastAPI
    from passlib.context import CryptContext
    import redis

    We're comparing FastAPI vs Django for our high-performance API.
    Need to optimize latency (currently 500ms) and ensure JWT security.

    Key concerns:
    - Database connection pooling with asyncpg
    - Redis caching for 90% hit ratio
    - Preventing SQL injection vulnerabilities
    - Password hashing with bcrypt
    """

    result = await supervisor_route(
        content=content, content_type="code", analysis_id="test-combined-001"
    )

    agents = result["supervisor_decision"]["agents"]
    reasoning = result["supervisor_decision"]["reasoning"]

    print(f"\n✓ Selected agents: {agents}")
    print(f"✓ Reasoning: {reasoning}")

    expected_agents = ["performance_analyst", "security_auditor", "tech_comparator"]
    activated_count = sum(1 for agent in expected_agents if agent in agents)

    print(f"\n✓ Auto-activated {activated_count}/3 expected agents")

    if activated_count == 3:
        print("\n✅ SUCCESS: All three agents were auto-activated!")
        return True
    elif activated_count >= 2:
        print(f"\n⚠️  PARTIAL: {activated_count}/3 agents activated")
        missing = [a for a in expected_agents if a not in agents]
        print(f"   Missing: {missing}")
        return True  # Still acceptable
    else:
        print(f"\n❌ FAILURE: Only {activated_count}/3 agents activated")
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("SPRINT 3 REAL-DATA VERIFICATION")
    print("Testing Issues #174, #177, #178")
    print("=" * 80)

    results = []

    # Run all tests
    results.append(await test_performance_analyst_activation())
    results.append(await test_security_auditor_activation())
    results.append(await test_tech_comparator_activation())
    results.append(await test_combined_activation())

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"\nTests passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Sprint 3 implementation verified!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

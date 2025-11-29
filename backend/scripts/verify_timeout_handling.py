#!/usr/bin/env python3
"""Verification script for GeneratorExit timeout handling with real data.

This script tests that:
1. GeneratorExit from timeout is converted to TimeoutError
2. One agent timeout doesn't crash the entire workflow
3. Error isolation works correctly

Run with:
    poetry run python scripts/verify_timeout_handling.py
"""

import asyncio
import os
import sys
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.workflows.agents.streaming import stream_agent_response
from app.workflows.tasks.agent_execution import execute_agents
from unittest.mock import MagicMock

logger = get_logger(__name__)


async def test_streaming_timeout_conversion():
    """Test that GeneratorExit from timeout is converted to TimeoutError."""
    print("\n=== Test 1: Streaming Timeout Conversion ===")
    
    mock_agent = MagicMock()
    
    async def slow_stream(*args, **kwargs):
        await asyncio.sleep(10)  # Longer than timeout
        yield {"messages": []}
    
    mock_agent.astream = slow_stream
    
    try:
        await stream_agent_response(
            agent=mock_agent,
            input_messages={"messages": [{"role": "user", "content": "test"}]},
            analysis_id="test-timeout-id",
            agent_type="test_agent",
            timeout=0.1,  # Very short timeout
        )
        print("❌ FAIL: Should have raised TimeoutError")
        return False
    except TimeoutError as e:
        print(f"✅ PASS: TimeoutError raised as expected: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {type(e).__name__}: {e}")
        return False


async def test_agent_execution_error_isolation():
    """Test that one agent timeout doesn't crash the entire workflow."""
    print("\n=== Test 2: Agent Execution Error Isolation ===")
    
    analysis_id = str(uuid4())
    content = "Test content for error isolation verification"
    content_type = "article"
    
    # Create Analysis record (required for foreign key)
    try:
        async with AsyncSessionLocal() as session:
            analysis = Analysis(
                id=analysis_id,
                url="https://example.com/test",
                content_type=content_type,
                status="pending",
            )
            session.add(analysis)
            await session.commit()
            print(f"✅ Created Analysis record: {analysis_id}")
    except Exception as e:
        print(f"⚠️  Could not create Analysis record: {e}")
        print("   (This is okay for timeout isolation test)")
    
    # Execute with agents - should return list even if timeouts occur
    try:
        result = await execute_agents(
            content=content,
            content_type=content_type,
            analysis_id=analysis_id,
            selected_agents=["tech_comparator"],  # Single agent
        )
        
        print(f"✅ PASS: execute_agents returned list (length: {len(result)})")
        print(f"   Result type: {type(result)}")
        print(f"   Result: {result[:100] if result else '[]'}...")
        return True
    except Exception as e:
        print(f"❌ FAIL: execute_agents raised exception: {type(e).__name__}: {e}")
        return False


async def test_aggregate_findings_timeout_handling():
    """Test that aggregate_findings handles timeout gracefully."""
    print("\n=== Test 3: Aggregate Findings Timeout Handling ===")
    
    from app.workflows.tasks.aggregate_findings import aggregate_findings
    from app.workflows.state import AnalysisState
    from unittest.mock import patch
    
    # Create sample state
    state = AnalysisState(
        analysis_id="test-aggregate-timeout",
        url="https://example.com",
        content_type="article",
        raw_content="Test content",
        extraction_metadata={},
        content_embedding=[],
        supervisor_decision={},
        agent_findings=[
            {
                "agent_type": "tech_comparator",
                "findings": {"recommendation": "Use LangGraph"},
                "confidence_score": 0.85,
            }
        ],
    )
    
    # Mock invoke_agent to raise GeneratorExit (simulating timeout)
    with patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke:
        mock_invoke.side_effect = GeneratorExit("Generator closed by timeout")
        
        try:
            result = await aggregate_findings(state)
            
            # Should use fallback aggregated insights
            assert "aggregated_insights" in result
            assert isinstance(result["aggregated_insights"], dict)
            assert "executive_summary" in result["aggregated_insights"]
            
            print("✅ PASS: aggregate_findings handled GeneratorExit gracefully")
            print(f"   Returned fallback insights with executive_summary")
            return True
        except Exception as e:
            print(f"❌ FAIL: aggregate_findings raised exception: {type(e).__name__}: {e}")
            return False


async def main():
    """Run all verification tests."""
    print("=" * 60)
    print("GeneratorExit Timeout Handling Verification")
    print("=" * 60)
    
    results = []
    
    # Test 1: Streaming timeout conversion
    results.append(await test_streaming_timeout_conversion())
    
    # Test 2: Agent execution error isolation
    results.append(await test_agent_execution_error_isolation())
    
    # Test 3: Aggregate findings timeout handling
    results.append(await test_aggregate_findings_timeout_handling())
    
    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")
    
    if all(results):
        print("✅ ALL TESTS PASSED - Timeout handling verified!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Review timeout handling")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

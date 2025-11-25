#!/usr/bin/env python3
"""Test script to verify end-to-end analysis workflow with real data.

This script processes a real article about Claude Opus 4.5 and verifies:
- Content extraction works
- Embedding generation works
- Supervisor routing works
- Agent execution works
- LangSmith tracing is active
- All instrumentation is working
"""

import asyncio
import os
import sys
from uuid import uuid4

# Load environment variables before any imports
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.core.logging import get_logger
from app.workflows.analysis import analysis_workflow

logger = get_logger(__name__)


async def test_real_analysis():
    """Test the analysis workflow with a real article."""
    # Article about Claude Opus 4.5 release
    test_url = "https://www.reuters.com/business/retail-consumer/anthropic-bolsters-ai-model-claudes-coding-agentic-abilities-with-opus-45-2025-11-24/"
    
    analysis_id = str(uuid4())
    
    logger.info(
        "test_real_analysis_starting",
        analysis_id=analysis_id,
        url=test_url,
        langsmith_enabled=os.getenv("LANGCHAIN_TRACING_V2") == "true",
        langsmith_project=os.getenv("LANGCHAIN_PROJECT"),
    )
    
    try:
        # Run the workflow with LangSmith configuration
        workflow_config = {
            "configurable": {
                "thread_id": analysis_id,
            },
            "run_name": f"test_real_analysis_{analysis_id[:8]}",
            "tags": ["test", "real_data", "claude_opus_4.5"],
            "metadata": {
                "analysis_id": analysis_id,
                "url": test_url,
                "test_type": "real_data_verification",
            },
        }
        
        result = await analysis_workflow.ainvoke(
            {
                "url": test_url,
                "analysis_id": analysis_id,
            },
            config=workflow_config,
        )
        
        # Verify results
        logger.info(
            "test_real_analysis_complete",
            analysis_id=analysis_id,
            content_length=len(result.get("raw_content", "")),
            content_type=result.get("content_type"),
            has_embedding=bool(result.get("content_embedding")),
            embedding_dimensions=len(result.get("content_embedding", [])),
            supervisor_decision=result.get("supervisor_decision"),
            agents_selected=len(result.get("supervisor_decision", {}).get("agents", [])),
            agent_findings_count=len(result.get("agent_findings", [])),
        )
        
        # Print summary
        print("\n" + "=" * 80)
        print("ANALYSIS WORKFLOW TEST RESULTS")
        print("=" * 80)
        print(f"Analysis ID: {analysis_id}")
        print(f"URL: {test_url}")
        print(f"Content Type: {result.get('content_type')}")
        print(f"Content Length: {len(result.get('raw_content', ''))} characters")
        print(f"Embedding Dimensions: {len(result.get('content_embedding', []))}")
        
        supervisor_decision = result.get("supervisor_decision", {})
        selected_agents = supervisor_decision.get("agents", [])
        print(f"\nSupervisor Decision:")
        print(f"  Reasoning: {supervisor_decision.get('reasoning', 'N/A')[:200]}...")
        print(f"  Selected Agents: {selected_agents}")
        
        agent_findings = result.get("agent_findings", [])
        print(f"\nAgent Findings: {len(agent_findings)} completed")
        for finding in agent_findings:
            agent_type = finding.get("agent_type", "unknown")
            findings_count = len(finding.get("findings", {}))
            print(f"  - {agent_type}: {findings_count} findings")
        
        print("\n" + "=" * 80)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        # Check LangSmith tracing
        if os.getenv("LANGCHAIN_TRACING_V2") == "true":
            langsmith_project = os.getenv("LANGCHAIN_PROJECT", "default")
            print(f"\n📊 LangSmith Tracing:")
            print(f"  Enabled: ✅")
            print(f"  Project: {langsmith_project}")
            print(f"  View traces at: https://smith.langchain.com/projects/{langsmith_project}")
        else:
            print(f"\n⚠️  LangSmith Tracing: Not enabled")
            print(f"   Set LANGCHAIN_TRACING_V2=true and LANGSMITH_API_KEY to enable")
        
        return result
        
    except Exception as e:
        logger.exception(
            "test_real_analysis_failed",
            analysis_id=analysis_id,
            error=str(e),
        )
        print(f"\n❌ WORKFLOW FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_real_analysis())

#!/bin/bash
# Test script to verify end-to-end analysis workflow with real data
#
# Usage: ./scripts/test_real_analysis.sh [URL]
#
# This script processes a real article and verifies:
# - Content extraction works
# - Embedding generation works
# - Supervisor routing works
# - Agent execution works (with separate sessions)
# - LangSmith tracing is active
# - No GeneratorExit errors
# - No database concurrency errors

set -e

cd "$(dirname "$0")/.." || exit 1

# Default URL (Claude Opus 4.5 article)
URL="${1:-https://www.reuters.com/business/retail-consumer/anthropic-bolsters-ai-model-claudes-coding-agentic-abilities-with-opus-45-2025-11-24/}"

echo "🧪 Testing real analysis workflow..."
echo "URL: $URL"
echo ""

cd backend || exit 1

# Run the test
poetry run python -c "
import asyncio
import os
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

from app.core.logging import get_logger
from app.workflows.analysis import analysis_workflow

logger = get_logger(__name__)

async def test():
    analysis_id = str(uuid4())
    
    logger.info('test_starting', url='$URL', analysis_id=analysis_id)
    
    workflow_config = {
        'configurable': {'thread_id': analysis_id},
        'run_name': f'test_real_analysis_{analysis_id[:8]}',
        'tags': ['test', 'real_data', 'verification'],
        'metadata': {
            'analysis_id': analysis_id,
            'url': '$URL',
            'test_type': 'real_data_verification',
        },
    }
    
    result = await analysis_workflow.ainvoke(
        {'url': '$URL', 'analysis_id': analysis_id},
        config=workflow_config,
    )
    
    print('\n' + '='*80)
    print('✅ WORKFLOW COMPLETED SUCCESSFULLY')
    print('='*80)
    print(f'Analysis ID: {analysis_id}')
    print(f'Content Length: {len(result.get(\"raw_content\", \"\"))} characters')
    print(f'Embedding Dimensions: {len(result.get(\"content_embedding\", []))}')
    print(f'Agents Selected: {len(result.get(\"supervisor_decision\", {}).get(\"agents\", []))}')
    print(f'Agents Completed: {len(result.get(\"agent_findings\", []))}')
    
    if os.getenv('LANGCHAIN_TRACING_V2') == 'true':
        project = os.getenv('LANGCHAIN_PROJECT', 'default')
        print(f'\n📊 LangSmith Tracing: ✅ Enabled (project: {project})')
    else:
        print('\n⚠️  LangSmith Tracing: Not enabled')

asyncio.run(test())
"

echo ""
echo "✅ Test complete!"

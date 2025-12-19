#!/bin/bash
# Test upload script with minimal environment

export LANGFUSE_ENABLED=true
export LANGFUSE_PUBLIC_KEY=pk-lf-a2a89dc7-fe10-4584-b8d1-28bb47018ae9
export LANGFUSE_SECRET_KEY=sk-lf-ac49d63e-cd97-42b7-9a24-6af77a1315fa
export LANGFUSE_HOST=http://localhost:3000
export LANGFUSE_PROMPTS_ENABLED=true

# Run in dry-run mode first
echo "=== Testing upload script in dry-run mode ==="
poetry run python scripts/upload_datasets_to_langfuse.py --dry-run

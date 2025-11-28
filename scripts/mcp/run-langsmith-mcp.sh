#!/bin/bash
# Wrapper script for LangSmith MCP server
# Loads environment variables from .mcp.env and runs the langsmith MCP server
#
# Environment variables expected in .mcp.env:
#   LANGSMITH_API_KEY - LangSmith API key (get from https://smith.langchain.com/settings)
#   LANGSMITH_ENDPOINT - LangSmith API endpoint (optional, defaults to cloud)
#   LANGSMITH_PROJECT - LangSmith project name (optional)

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load environment variables from .mcp.env if it exists
MCP_ENV_FILE="$PROJECT_ROOT/.mcp.env"
if [ -f "$MCP_ENV_FILE" ]; then
  set -a  # Automatically export all variables
  source "$MCP_ENV_FILE" 2>/dev/null || true
  set +a  # Turn off automatic export
fi

# Validate that LANGSMITH_API_KEY is set
if [ -z "${LANGSMITH_API_KEY:-}" ]; then
  echo "Error: LANGSMITH_API_KEY not set in .mcp.env" >&2
  echo "Get your API key from: https://smith.langchain.com/settings" >&2
  exit 1
fi

# Export environment variables for the MCP server
export LANGSMITH_API_KEY

# Optional: Export endpoint and project if set
if [ -n "${LANGSMITH_ENDPOINT:-}" ]; then
  export LANGSMITH_ENDPOINT
fi

if [ -n "${LANGSMITH_PROJECT:-}" ]; then
  export LANGSMITH_PROJECT
fi

# Run the langsmith MCP server using uvx
exec env LANGSMITH_API_KEY="$LANGSMITH_API_KEY" uvx langsmith-mcp-server


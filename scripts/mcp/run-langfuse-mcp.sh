#!/bin/bash
# Wrapper script for Langfuse MCP server
# Loads environment variables from .mcp.env and runs the Langfuse MCP server
#
# Usage: ./run-langfuse-mcp.sh
#
# Environment variables expected in .mcp.env:
#   LANGFUSE_HOST - Langfuse server URL (e.g., http://localhost:3000)
#   LANGFUSE_PUBLIC_KEY - Public API key from Langfuse dashboard
#   LANGFUSE_SECRET_KEY - Secret API key from Langfuse dashboard

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

# Validate required environment variables
if [ -z "${LANGFUSE_PUBLIC_KEY:-}" ]; then
  echo "Error: LANGFUSE_PUBLIC_KEY not set in .mcp.env" >&2
  echo "Please set LANGFUSE_PUBLIC_KEY in $MCP_ENV_FILE" >&2
  exit 1
fi

if [ -z "${LANGFUSE_SECRET_KEY:-}" ]; then
  echo "Error: LANGFUSE_SECRET_KEY not set in .mcp.env" >&2
  echo "Please set LANGFUSE_SECRET_KEY in $MCP_ENV_FILE" >&2
  exit 1
fi

# Set default host if not provided
export LANGFUSE_BASEURL="${LANGFUSE_HOST:-http://localhost:3000}"

# Run the Langfuse MCP server (using @meltstudio/langfuse-mcp-server)
exec npx -y @meltstudio/langfuse-mcp-server@latest

#!/bin/bash
# Wrapper script for PostgreSQL MCP server
# Loads environment variables from .mcp.env and runs the postgres MCP server
#
# Usage: ./run-postgres-mcp.sh [ENV] [DATABASE_NAME]
#   ENV: dev, test, staging, or prod (defaults to dev)
#   DATABASE_NAME: Optional database name to append to URL (for test databases)
#
# Environment variables expected in .mcp.env:
#   POSTGRES_URL_DEV - Development database URL (full URL)
#   POSTGRES_URL_TEST - Test database base URL (without database name)
#   POSTGRES_URL_STAGING - Staging database URL (full URL)
#   POSTGRES_URL_PROD - Production database URL (full URL)

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

# Determine environment and optional database name
# First argument is the environment (dev/test/staging/prod)
# Second argument is optional database name (for test databases)
MCP_ENV="${1:-dev}"
DB_NAME="${2:-}"

# Select the appropriate database URL based on environment
case "$MCP_ENV" in
  dev)
    POSTGRES_URL="${POSTGRES_URL_DEV:-}"
    ;;
  test)
    POSTGRES_URL="${POSTGRES_URL_TEST:-}"
    # If database name is provided, append it to the base URL
    # Otherwise, connect to default 'postgres' database for cross-database queries
    if [ -n "$DB_NAME" ]; then
      POSTGRES_URL="${POSTGRES_URL}/${DB_NAME}"
    else
      POSTGRES_URL="${POSTGRES_URL}/postgres"
    fi
    ;;
  staging)
    POSTGRES_URL="${POSTGRES_URL_STAGING:-}"
    ;;
  prod)
    POSTGRES_URL="${POSTGRES_URL_PROD:-}"
    ;;
  *)
    echo "Error: Invalid environment '$MCP_ENV'. Must be dev, test, staging, or prod." >&2
    exit 1
    ;;
esac

# Validate that we have a database URL
if [ -z "$POSTGRES_URL" ]; then
  echo "Error: POSTGRES_URL_${MCP_ENV^^} not set in .mcp.env" >&2
  exit 1
fi

# Export the database URL for the MCP server (for backwards compatibility)
export POSTGRES_DEV_URL="$POSTGRES_URL"
if [ "$MCP_ENV" = "test" ]; then
  export POSTGRES_TEST_URL="$POSTGRES_URL"
fi

# Run the postgres MCP server
exec npx @modelcontextprotocol/server-postgres "$POSTGRES_URL"


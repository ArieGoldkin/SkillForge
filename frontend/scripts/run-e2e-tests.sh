#!/bin/bash
# E2E Test Runner for Test Environment
# Loads .env.test and runs Playwright tests

set -e

cd "$(dirname "$0")/.."

# Check if .env.test exists
if [ ! -f .env.test ]; then
  echo "❌ Error: .env.test file not found"
  echo "   Please copy .env.test.example to .env.test and fill in credentials:"
  echo "   cp .env.test.example .env.test"
  exit 1
fi

# Load environment variables from .env.test
export $(cat .env.test | grep -v '^#' | xargs)

# Verify required variables are set
if [ -z "$LANGFUSE_EMAIL" ] || [ -z "$LANGFUSE_PASSWORD" ]; then
  echo "⚠️  Warning: LANGFUSE_EMAIL or LANGFUSE_PASSWORD not set in .env.test"
  echo "   Some Langfuse-related tests may be skipped"
fi

# Set defaults if not already set
export PLAYWRIGHT_BASE_URL=${PLAYWRIGHT_BASE_URL:-http://localhost:5174}
export API_BASE_URL=${API_BASE_URL:-http://localhost:8501}
export LANGFUSE_URL=${LANGFUSE_URL:-http://localhost:3001}

echo "🚀 Running E2E tests against test environment..."
echo "   Frontend: $PLAYWRIGHT_BASE_URL"
echo "   Backend:  $API_BASE_URL"
echo "   Langfuse: $LANGFUSE_URL"
echo ""

# Run Playwright tests
npx playwright test --project=chromium "$@"


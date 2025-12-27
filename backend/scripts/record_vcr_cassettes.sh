#!/usr/bin/env bash
# Record VCR cassettes for Tavily tests
#
# Usage:
#   ./scripts/record_vcr_cassettes.sh             # Record all Tavily tests
#   ./scripts/record_vcr_cassettes.sh test_name   # Record specific test

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}VCR Cassette Recorder${NC}"
echo "========================================"

# Check if we're in the backend directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from backend/ directory${NC}"
    exit 1
fi

# Check if TAVILY_API_KEY is set
if [ -z "${TAVILY_API_KEY}" ]; then
    echo -e "${YELLOW}Warning: TAVILY_API_KEY not set${NC}"
    echo ""
    echo "To record cassettes with real API responses:"
    echo "  export TAVILY_API_KEY=your-actual-api-key"
    echo "  ./scripts/record_vcr_cassettes.sh"
    echo ""
    read -p "Continue with placeholder key? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    export TAVILY_API_KEY="test-placeholder-key"
fi

# Determine which tests to run
if [ -z "$1" ]; then
    TEST_TARGET="tests/unit/services/tools/test_tavily_search.py"
    echo "Recording all Tavily tests..."
else
    TEST_TARGET="tests/unit/services/tools/test_tavily_search.py::$1"
    echo "Recording test: $1"
fi

echo ""
echo "Test target: $TEST_TARGET"
echo "Record mode: all (overwrite existing)"
echo ""

# Run tests with VCR in record mode
echo -e "${GREEN}Running pytest with VCR_RECORD_MODE=all...${NC}"
VCR_RECORD_MODE=all poetry run pytest "$TEST_TARGET" -v --tb=short

# Check if cassettes were created
CASSETTE_DIR="tests/cassettes/unit/tavily_search"
if [ -d "$CASSETTE_DIR" ]; then
    CASSETTE_COUNT=$(find "$CASSETTE_DIR" -name "*.yaml" | wc -l | tr -d ' ')
    echo ""
    echo -e "${GREEN}Success! Created/updated $CASSETTE_COUNT cassette(s)${NC}"
    echo ""
    echo "Cassettes location: $CASSETTE_DIR"
    ls -lh "$CASSETTE_DIR"/*.yaml 2>/dev/null || true

    # Security check
    echo ""
    echo -e "${YELLOW}Security Check:${NC} Verifying API keys are filtered..."

    # Check for common API key patterns
    LEAKED_KEYS=0

    # Check for Tavily keys (tvly-)
    if grep -r "tvly-" "$CASSETTE_DIR" 2>/dev/null; then
        echo -e "${RED}WARNING: Found potential Tavily API key in cassettes!${NC}"
        LEAKED_KEYS=1
    fi

    # Check for OpenAI keys (sk-)
    if grep -r "sk-[a-zA-Z0-9]" "$CASSETTE_DIR" 2>/dev/null | grep -v "REDACTED"; then
        echo -e "${RED}WARNING: Found potential OpenAI API key in cassettes!${NC}"
        LEAKED_KEYS=1
    fi

    # Check for unredacted authorization headers
    if grep -r "authorization:" "$CASSETTE_DIR" 2>/dev/null | grep -v "REDACTED"; then
        echo -e "${RED}WARNING: Found unredacted authorization header in cassettes!${NC}"
        LEAKED_KEYS=1
    fi

    if [ $LEAKED_KEYS -eq 0 ]; then
        echo -e "${GREEN}✓ No API keys found - cassettes are safe to commit${NC}"
    else
        echo ""
        echo -e "${RED}ERROR: API keys detected in cassettes!${NC}"
        echo "DO NOT commit these cassettes. Fix the filtering in conftest.py first."
        exit 1
    fi
else
    echo -e "${RED}Warning: Cassette directory not found${NC}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review cassettes: cat $CASSETTE_DIR/*.yaml"
echo "  2. Run tests: poetry run pytest tests/unit/services/tools/test_tavily_search.py -v"
echo "  3. Commit cassettes: git add tests/cassettes/ && git commit -m 'test: add VCR cassettes for Tavily tests'"

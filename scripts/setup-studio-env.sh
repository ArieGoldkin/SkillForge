#!/bin/bash
# Setup script for LangSmith Studio debugging environment
# This creates a separate virtual environment to avoid dependency conflicts
# with sse-starlette (langgraph-cli requires <2.2.0, FastAPI uses ^3.0.3)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
STUDIO_VENV="$BACKEND_DIR/.venv-studio"

echo "Setting up LangSmith Studio debugging environment..."
echo ""

# Check if Python 3.13 is available
if ! command -v python3.13 &> /dev/null; then
    echo "Error: Python 3.13 is required but not found."
    echo "Please install Python 3.13 first."
    exit 1
fi

# Create separate virtual environment for Studio
echo "Creating Studio virtual environment at: $STUDIO_VENV"
python3.13 -m venv "$STUDIO_VENV"

# Activate the virtual environment
echo "Activating Studio virtual environment..."
source "$STUDIO_VENV/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install langgraph-cli with inmem support
echo "Installing langgraph-cli[inmem]..."
pip install "langgraph-cli[inmem]"

# Install project dependencies (this will install sse-starlette 3.0.3, but that's OK)
# We'll use langgraph-cli from this venv, not from the project dependencies
echo "Installing project dependencies..."
cd "$BACKEND_DIR"
pip install -e .

echo ""
echo "✅ Studio environment setup complete!"
echo ""
echo "To use Studio:"
echo "  1. Activate the Studio environment:"
echo "     source $STUDIO_VENV/bin/activate"
echo ""
echo "  2. Start the LangGraph dev server:"
echo "     cd $BACKEND_DIR"
echo "     langgraph dev"
echo ""
echo "  3. Studio UI will open at http://127.0.0.1:2024"
echo ""
echo "Note: This environment has langgraph-cli installed. FastAPI should"
echo "      be run from the main poetry environment to use sse-starlette 3.0.3"



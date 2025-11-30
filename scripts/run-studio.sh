#!/bin/bash
# Quick script to activate Studio environment and run langgraph dev

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
STUDIO_VENV="$BACKEND_DIR/.venv-studio"

if [ ! -d "$STUDIO_VENV" ]; then
    echo "Studio environment not found. Running setup..."
    "$SCRIPT_DIR/setup-studio-env.sh"
fi

echo "Activating Studio environment..."
source "$STUDIO_VENV/bin/activate"

cd "$BACKEND_DIR"

echo "Starting LangGraph dev server..."
echo "Studio UI will open at http://127.0.0.1:2024"
echo "Press Ctrl+C to stop"
echo ""

langgraph dev



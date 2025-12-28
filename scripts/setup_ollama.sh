#!/bin/bash
# ============================================================================
# Ollama Setup Script for Self-Hosted GitHub Actions Runner
# ============================================================================
# This script sets up Ollama with the required models for SkillForge CI.
# Run this once on your self-hosted runner (M4 Max 256GB recommended).
#
# Issue #606: CI Cost Reduction via Local Models
#
# Usage:
#   chmod +x scripts/setup_ollama.sh
#   ./scripts/setup_ollama.sh
#
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║           SKILLFORGE OLLAMA SETUP FOR CI                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 1. Install Ollama
# ============================================================================
echo "📦 Step 1: Checking Ollama installation..."

if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed: $(ollama --version)"
else
    echo "🔧 Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ollama
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    echo "✅ Ollama installed"
fi

# ============================================================================
# 2. Start Ollama Service
# ============================================================================
echo ""
echo "🚀 Step 2: Ensuring Ollama service is running..."

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama server is already running"
else
    echo "🔧 Starting Ollama server..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use launchd
        brew services start ollama || ollama serve &
    else
        # Linux - use systemd or background
        if command -v systemctl &> /dev/null; then
            sudo systemctl start ollama
        else
            ollama serve &
        fi
    fi
    sleep 5

    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama server started"
    else
        echo "❌ Failed to start Ollama server"
        exit 1
    fi
fi

# ============================================================================
# 3. Pull Required Models
# ============================================================================
echo ""
echo "📥 Step 3: Pulling required models..."
echo "   This may take a while (total ~80GB for all models)"
echo ""

MODELS=(
    "nomic-embed-text"      # Embeddings: 768 dims, ~0.5GB
    "qwen2.5-coder:32b"     # Coding: 73.7% Aider, ~35GB
    "deepseek-r1:70b"       # Reasoning: GPT-4 level, ~42GB
)

for model in "${MODELS[@]}"; do
    echo "📥 Pulling $model..."
    if ollama list | grep -q "$model"; then
        echo "   ✅ Already available"
    else
        ollama pull "$model"
        echo "   ✅ Downloaded"
    fi
done

# ============================================================================
# 4. Verify Models
# ============================================================================
echo ""
echo "🔍 Step 4: Verifying models..."

echo ""
echo "Available models:"
ollama list
echo ""

# ============================================================================
# 5. Test Embeddings
# ============================================================================
echo "🧪 Step 5: Testing embedding generation..."

EMBED_TEST=$(curl -s http://localhost:11434/api/embeddings \
    -d '{"model":"nomic-embed-text","prompt":"test embedding"}')

if echo "$EMBED_TEST" | grep -q "embedding"; then
    echo "✅ Embeddings working"
else
    echo "❌ Embeddings test failed"
    echo "$EMBED_TEST"
fi

# ============================================================================
# 6. Configure Environment
# ============================================================================
echo ""
echo "⚙️  Step 6: Environment configuration..."
echo ""
echo "Add these to your shell profile (~/.zshrc or ~/.bashrc):"
echo ""
echo "  # Ollama configuration for SkillForge CI"
echo "  export OLLAMA_ENABLED=true"
echo "  export OLLAMA_HOST=http://localhost:11434"
echo "  export OLLAMA_MODEL_REASONING=deepseek-r1:70b"
echo "  export OLLAMA_MODEL_CODING=qwen2.5-coder:32b"
echo "  export OLLAMA_MODEL_EMBED=nomic-embed-text"
echo ""
echo "  # Performance optimization for M4 Max"
echo "  export OLLAMA_MAX_LOADED_MODELS=3"
echo "  export OLLAMA_KEEP_ALIVE=5m"
echo ""

# ============================================================================
# 7. Summary
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                         SETUP COMPLETE                             ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo "║                                                                    ║"
echo "║  Models installed:                                                 ║"
echo "║    • nomic-embed-text  (embeddings, 768 dims)                      ║"
echo "║    • qwen2.5-coder:32b (coding, tool calling)                      ║"
echo "║    • deepseek-r1:70b   (reasoning, G-Eval)                         ║"
echo "║                                                                    ║"
echo "║  Expected CI cost savings: 93% (~₪625/month)                       ║"
echo "║                                                                    ║"
echo "║  To test locally:                                                  ║"
echo "║    cd backend && OLLAMA_ENABLED=true poetry run pytest             ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"

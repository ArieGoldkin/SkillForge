#!/bin/bash
# Reinstall MCP servers for Cursor IDE
# This script ensures all MCP packages are properly installed

set -e

echo "🔄 Reinstalling MCP servers..."

# Clear npm cache (if using npm)
if command -v npm &> /dev/null; then
    echo "Clearing npm cache..."
    npm cache clean --force 2>/dev/null || true
fi

# Clear pnpm cache (if using pnpm)
if command -v pnpm &> /dev/null; then
    echo "Clearing pnpm cache..."
    pnpm store prune 2>/dev/null || true
fi

# Install each MCP server package
echo ""
echo "Installing MCP server packages..."

echo "  📦 @modelcontextprotocol/server-memory"
npx -y @modelcontextprotocol/server-memory@latest --version || echo "  ⚠️  Warning: memory server install failed"

echo "  📦 @modelcontextprotocol/server-sequential-thinking"
npx -y @modelcontextprotocol/server-sequential-thinking@latest --version || echo "  ⚠️  Warning: sequential-thinking server install failed"

echo "  📦 @upstash/context7-mcp"
npx -y @upstash/context7-mcp@latest --version || echo "  ⚠️  Warning: context7 server install failed"

echo "  📦 @playwright/mcp"
npx -y @playwright/mcp@latest --version || echo "  ⚠️  Warning: playwright server install failed"

echo "  📦 @modelcontextprotocol/server-postgres"
npx -y @modelcontextprotocol/server-postgres@latest --version || echo "  ⚠️  Warning: postgres-mcp server install failed"

echo "  📦 langfuse-mcp"
npx -y langfuse-mcp@latest --version || echo "  ⚠️  Warning: langfuse server install failed"

echo ""
echo "✅ MCP server reinstallation complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Restart Cursor IDE completely (quit and reopen)"
echo "  2. Check MCP server status in Cursor IDE settings"
echo "  3. If errors persist, check 'Show Output' for detailed error messages"
echo "  4. Ensure .mcp.env file exists with correct environment variables"

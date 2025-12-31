#!/bin/bash
# Sync .mcp.env variables into .mcp.json
# Use this if Cursor IDE doesn't automatically load .mcp.env

set -e

if [ ! -f ".mcp.env" ]; then
    echo "❌ Error: .mcp.env file not found"
    echo "   Run: cp .mcp.env.example .mcp.env"
    exit 1
fi

# Load environment variables from .mcp.env
export $(grep -v '^#' .mcp.env | xargs)

# Create a temporary .mcp.json with actual values
echo "🔄 Syncing .mcp.env values into .mcp.json..."

# Use Node.js or Python to properly update JSON
if command -v node &> /dev/null; then
    node << 'EOF'
const fs = require('fs');
const path = require('path');

// Load .mcp.env
const envFile = fs.readFileSync('.mcp.env', 'utf8');
const env = {};
envFile.split('\n').forEach(line => {
  const match = line.match(/^([^#=]+)=(.*)$/);
  if (match) {
    env[match[1].trim()] = match[2].trim();
  }
});

// Load .mcp.json
const mcpJson = JSON.parse(fs.readFileSync('.mcp.json', 'utf8'));

// Update environment variables in postgres-mcp
if (mcpJson.mcpServers['postgres-mcp']?.env) {
  mcpJson.mcpServers['postgres-mcp'].env.POSTGRES_CONNECTION_STRING = 
    env.POSTGRES_CONNECTION_STRING || 
    `postgresql://${env.POSTGRES_USER}:${env.POSTGRES_PASSWORD}@${env.POSTGRES_HOST}:${env.POSTGRES_PORT}/${env.POSTGRES_DB}`;
}

// Update environment variables in langfuse
if (mcpJson.mcpServers.langfuse?.env) {
  mcpJson.mcpServers.langfuse.env.LANGFUSE_HOST = env.LANGFUSE_HOST || 'http://localhost:3000';
  mcpJson.mcpServers.langfuse.env.LANGFUSE_PUBLIC_KEY = env.LANGFUSE_PUBLIC_KEY || '';
  mcpJson.mcpServers.langfuse.env.LANGFUSE_SECRET_KEY = env.LANGFUSE_SECRET_KEY || '';
}

// Write back
fs.writeFileSync('.mcp.json', JSON.stringify(mcpJson, null, 2) + '\n');
console.log('✅ Updated .mcp.json with values from .mcp.env');
EOF
else
    echo "⚠️  Node.js not found. Please install Node.js to use this script."
    echo "   Alternatively, manually update .mcp.json with values from .mcp.env"
    exit 1
fi

echo ""
echo "✅ Done! Restart Cursor IDE for changes to take effect."

# Issue #385: Implement Langfuse MCP Server for Prompts

**Status:** 📋 Planned
**Branch:** `issue/378-385-langfuse-phase2`
**Milestone:** Langfuse Migration Phase 2
**Priority:** 🔵 LOW (Nice-to-have)
**Estimated Effort:** 6-8 hours
**Dependencies:** Issue #379 (Prompt Management) - MUST be complete first

---

## Summary

Integrate Langfuse's native MCP server to enable **prompt iteration directly from Claude Code**. This is a developer productivity enhancement that allows AI assistants to fetch and update prompts without leaving the development environment.

**Important**: This is a **nice-to-have feature** that depends on #379 being fully implemented. It provides convenience but is not critical to core functionality.

## Why This Matters

Once #379 (Prompt Management) is complete, developers will manage prompts in Langfuse UI. This MCP integration enables:

- **Inline prompt editing**: Update prompts directly from Claude Code conversations
- **Faster iteration**: No context switching to Langfuse web UI
- **AI-assisted prompt engineering**: Claude can suggest and apply prompt improvements
- **Version control**: Create new prompt versions programmatically
- **Label management**: Promote prompts between environments (staging → production)

## Key Features

### Read Operations
- **List Prompts**: Browse all prompts with filtering
- **Get Prompt**: Fetch specific prompt with variable compilation
- **Cursor Pagination**: Navigate large prompt libraries

### Write Operations
- **Create Prompts**: Generate new text/chat prompt versions
- **Update Labels**: Promote prompts between environments

## MCP Server Configuration

Add to `.mcp.json`:

\`\`\`json
{
  "mcpServers": {
    "langfuse": {
      "command": "npx",
      "args": ["-y", "@langfuse/mcp-server-langfuse@latest"],
      "env": {
        "LANGFUSE_PUBLIC_KEY": "${LANGFUSE_PUBLIC_KEY}",
        "LANGFUSE_SECRET_KEY": "${LANGFUSE_SECRET_KEY}",
        "LANGFUSE_BASEURL": "http://localhost:3000"
      }
    }
  }
}
\`\`\`

## Implementation Checklist

### Phase 1: Setup (2 hours)
- [ ] Add Langfuse MCP server to `.mcp.json`
- [ ] Create `.mcp.env` with credentials
- [ ] Document credentials in `.mcp.env.example`
- [ ] Restart Claude Code and verify connection

### Phase 2: Testing (2 hours)
- [ ] Test getPrompt for existing prompts
- [ ] Test listPrompts with filters
- [ ] Test createChatPrompt for new versions
- [ ] Test updatePromptLabels for promotion
- [ ] Verify in Langfuse UI

### Phase 3: Documentation (2 hours)
- [ ] Create `docs/guides/LANGFUSE_MCP_INTEGRATION.md`
- [ ] Create `docs/workflows/prompt-iteration-with-claude.md`
- [ ] Update `CLAUDE.md` MCP Servers section
- [ ] Document troubleshooting

### Phase 4: Examples (2 hours)
- [ ] Document supervisor prompt improvement workflow
- [ ] Document A/B test variant creation
- [ ] Document label promotion workflow

## Available MCP Tools

1. **getPrompt**(name, label, version) - Fetch specific prompt
2. **listPrompts**(filter, tag, cursor) - List all prompts
3. **createTextPrompt**(name, prompt, config) - Create text prompt version
4. **createChatPrompt**(name, messages, config) - Create chat prompt version
5. **updatePromptLabels**(name, version, labels) - Update label assignments

## Example Workflow

\`\`\`
User: "Claude, improve the supervisor prompt to be more concise"

Claude:
1. Uses getPrompt("analysis-supervisor-routing", label="production")
2. Analyzes current prompt (300 tokens)
3. Creates improved version (200 tokens) via createChatPrompt()
4. Assigns "staging" label
5. User tests staging prompt
6. Claude promotes to production via updatePromptLabels()
\`\`\`

## Benefits

- **50% faster iteration**: No UI context switching
- **AI-assisted improvements**: Claude suggests enhancements
- **Programmatic workflows**: Automate version management
- **Better documentation**: Decisions captured in conversation

## Rollback Plan

Disable MCP server by commenting out in `.mcp.json`:

\`\`\`json
{
  "mcpServers": {
    // "langfuse": { ... }  // Disabled
  }
}
\`\`\`

No data loss - MCP only interfaces with Langfuse, doesn't modify local state.

## Files to Create

- `.mcp.json` - Add langfuse server config
- `.mcp.env` - Credentials (gitignored)
- `.mcp.env.example` - Template
- `docs/guides/LANGFUSE_MCP_INTEGRATION.md`
- `docs/workflows/prompt-iteration-with-claude.md`

## Related Issues

- **#379**: Prompt Management (REQUIRED dependency)
- **#378**: Session & User Tracking (complementary)
- **#383**: Token/Cost Tracking (measure costs)
- **#372**: Langfuse Migration (foundation)

## Resources

- [Langfuse MCP Server Docs](https://langfuse.com/docs/prompt-management/features/mcp-server)
- [Langfuse MCP GitHub](https://github.com/langfuse/mcp-server-langfuse)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Priority Justification**: LOW priority because:
- Depends on #379 completion
- Developer convenience, not core functionality
- Manual Langfuse UI workflow fully functional
- Can implement after higher priority features

**See agent task a8cd0a4 output for complete 700+ line detailed documentation.**

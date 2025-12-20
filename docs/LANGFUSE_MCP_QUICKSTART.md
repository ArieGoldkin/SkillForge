# Langfuse MCP Integration - Quick Start Guide

**Issue:** #385
**Time to Setup:** 5 minutes
**Last Updated:** December 19, 2025

## TL;DR

Enable prompt management from Claude Code CLI by connecting to Langfuse's native MCP server.

**Benefits:**
- Create/update prompts directly from Claude Code sessions
- View prompt versions without leaving the CLI
- Iterate on prompts with AI assistance
- Query trace data conversationally

---

## 5-Minute Setup

### Step 1: Start Langfuse (1 min)

```bash
# From project root
docker-compose up -d langfuse-web langfuse-worker

# Verify it's running
curl http://localhost:3000/api/health
# Expected: {"status":"ok"}
```

### Step 2: Get API Keys (2 min)

1. Open http://localhost:3000
2. Login with dev credentials:
   - Email: `dev@skillforge.local`
   - Password: `skillforge-dev-password`
3. Navigate to: **Project Settings → API Keys**
4. Copy both keys:
   - Public Key (starts with `pk-lf-...`)
   - Secret Key (starts with `sk-lf-...`)

### Step 3: Configure MCP Server (2 min)

```bash
# 1. Create .mcp.env from template
cp .mcp.env.example .mcp.env

# 2. Edit .mcp.env and paste your API keys
nano .mcp.env
# Update these three lines:
#   LANGFUSE_HOST=http://localhost:3000
#   LANGFUSE_PUBLIC_KEY=pk-lf-YOUR-KEY-HERE
#   LANGFUSE_SECRET_KEY=sk-lf-YOUR-KEY-HERE

# 3. Secure the file
chmod 600 .mcp.env

# 4. Update .mcp.json (add langfuse server)
cp .mcp.json.example .mcp.json
# The langfuse server is already configured in the example

# 5. Restart Claude Code CLI
# Close and reopen Claude Code completely
```

### Step 4: Verify Installation (30 seconds)

Open Claude Code and test:

```plaintext
User: "List all Langfuse prompts"

Expected: Claude responds with prompt list (may be empty)
```

If you get an error, see [Troubleshooting](#troubleshooting).

---

## First Use: Create a Test Prompt

```plaintext
User: "Create a test prompt called 'hello_world' that just says hello"

Claude: [Creates prompt via langfuse.create_prompt]

User: "Show me the hello_world prompt"

Claude: [Displays prompt content and metadata]

User: "Update it to say 'Hello, {{name}}!'"

Claude: [Creates version 2 with new content]

User: "Show version history for hello_world"

Claude: [Lists versions 1 and 2]
```

Congratulations! You now have prompt management working.

---

## Common Use Cases

### Use Case 1: Browse Existing Prompts

```plaintext
"List all prompts in the system"
"Show me prompts with 'agent' in the name"
"What prompts are labeled 'production'?"
```

### Use Case 2: Inspect Prompt Details

```plaintext
"Show me the content_analysis prompt"
"Get version 5 of the tech_comparison prompt"
"What's in the production RAG prompt?"
```

### Use Case 3: Create New Prompts

```plaintext
"Create a prompt for summarizing technical articles"
"I need a prompt that extracts code examples from docs"
"Make a prompt for security code reviews"
```

### Use Case 4: Update Prompts

```plaintext
"Make the content_analysis prompt more concise"
"Update tech_comparison to focus on performance"
"Add error handling instructions to the RAG prompt"
```

### Use Case 5: Compare Versions

```plaintext
"Compare versions 5 and 6 of content_analysis"
"Show version history for the RAG prompt"
"What changed in the latest security_audit prompt?"
```

---

## MCP Tools Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `get_prompt` | Fetch specific version | "Show me the RAG prompt" |
| `list_prompts` | Browse all prompts | "List all prompts" |
| `create_prompt` | Add new prompt | "Create a summarization prompt" |
| `update_prompt` | Create new version | "Make it more concise" |
| `get_prompt_versions` | View history | "Show version history" |

---

## Integration with SkillForge Backend

The MCP server complements the existing `PromptManager` service:

```
┌─────────────────────────────────────────────────────────────────┐
│                        PROMPT ECOSYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Claude Code CLI (Development)                                  │
│  ──────────────────────────────                                 │
│  • Direct prompt management via MCP                             │
│  • No caching (always latest)                                   │
│  • Use for: Creating, updating, comparing prompts               │
│                                                                 │
│  SkillForge Backend (Runtime)                                   │
│  ────────────────────────────                                   │
│  • PromptManager with 3-level caching                           │
│  • LRU (in-memory) → Redis → Langfuse                           │
│  • Use for: High-performance prompt retrieval                   │
│                                                                 │
│  Both access same Langfuse database → Consistent state          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** Prompt updates via MCP are visible to PromptManager after cache TTL (default: 5 minutes).

---

## Troubleshooting

### Issue: "Langfuse tools not available"

**Check 1:** Is Langfuse running?
```bash
docker-compose ps langfuse-web
# Should show "Up"
```

**Check 2:** Is .mcp.json configured?
```bash
cat .mcp.json | grep -A 10 langfuse
# Should show langfuse server config
```

**Check 3:** Did you restart Claude Code?
- Close and reopen Claude Code completely
- MCP config only loads at startup

### Issue: "Authentication failed"

**Check 1:** Are keys correct?
```bash
cat .mcp.env | grep LANGFUSE_
# Verify keys match Langfuse UI (Project Settings → API Keys)
```

**Check 2:** Is host URL correct?
```bash
# Test API access
curl -H "Authorization: Bearer ${LANGFUSE_PUBLIC_KEY}" \
     http://localhost:3000/api/public/prompts
# Should return JSON, not 401
```

### Issue: "Connection timeout"

**Check 1:** Is Langfuse accessible?
```bash
curl -I http://localhost:3000/api/health
# Should return 200 OK
```

**Check 2:** Check firewall/VPN
- Some VPNs block localhost:3000
- Temporarily disable and test

---

## Next Steps

1. **Migrate Agent Prompts:** Move hardcoded prompts from code to Langfuse
2. **Enable A/B Testing:** Test prompt variations with different labels
3. **Add to CI/CD:** Automate prompt deployment pipeline
4. **Track Performance:** Link prompts to trace quality metrics

---

## Full Documentation

For complete details, see:
- **Full Guide:** [docs/LANGFUSE_MCP_INTEGRATION.md](./LANGFUSE_MCP_INTEGRATION.md)
- **Langfuse Skill:** [.claude/skills/langfuse-observability/SKILL.md](../.claude/skills/langfuse-observability/SKILL.md)
- **Backend Integration:** [backend/app/shared/services/prompts/prompt_manager.py](../backend/app/shared/services/prompts/prompt_manager.py)

---

## Security Reminders

- ✅ `.mcp.env` is gitignored
- ✅ Set file permissions: `chmod 600 .mcp.env`
- ✅ Never commit credentials
- ✅ Rotate keys every 90 days
- ✅ Use separate keys for dev/prod

---

**Questions?** See [troubleshooting section](./LANGFUSE_MCP_INTEGRATION.md#troubleshooting-guide) or ask in Claude Code.

# Langfuse MCP Server Integration Guide

**Issue:** #385
**Status:** Design Complete
**Last Updated:** December 19, 2025

## Overview

This guide documents the integration of Langfuse's native MCP server into Claude Code CLI, enabling direct prompt iteration, version management, and observability query from within the development workflow.

**Key Benefits:**
- Iterate on prompts directly from Claude Code sessions
- View prompt versions and performance metrics without leaving the CLI
- Create and update prompts with AI assistance
- Query trace data and costs from conversational context
- Seamless integration with existing Langfuse observability

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [MCP Server Configuration](#mcp-server-configuration)
3. [Credential Management](#credential-management)
4. [MCP Tools Reference](#mcp-tools-reference)
5. [Common Workflows](#common-workflows)
6. [CLAUDE.md Integration](#claudemd-integration)
7. [Testing & Verification](#testing--verification)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Security Best Practices](#security-best-practices)

---

## Architecture Overview

### MCP Integration Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     LANGFUSE MCP ARCHITECTURE                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Claude Code CLI                                                          │
│   ════════════════                                                         │
│   ┌──────────────────────────────────────────────────────────────┐        │
│   │  User: "Show me the latest version of the RAG prompt"       │        │
│   │  Claude: [Uses langfuse MCP tool: get_prompt]               │        │
│   └──────────────────────────────────────────────────────────────┘        │
│                           │                                                │
│                           ▼                                                │
│   ┌──────────────────────────────────────────────────────────────┐        │
│   │              MCP Transport Layer (stdio)                     │        │
│   │  - Manages stdin/stdout communication                        │        │
│   │  - Handles tool invocation serialization                     │        │
│   │  - Provides error handling and retry logic                   │        │
│   └──────────────────────────────────────────────────────────────┘        │
│                           │                                                │
│                           ▼                                                │
│   ┌──────────────────────────────────────────────────────────────┐        │
│   │           Langfuse Native MCP Server                         │        │
│   │  Endpoint: http://localhost:3000/api/public/mcp              │        │
│   │  - get_prompt(name, version?, label?)                        │        │
│   │  - list_prompts(page?, limit?)                               │        │
│   │  - create_prompt(name, prompt, config?, labels?)             │        │
│   │  - update_prompt(name, prompt, config?, labels?)             │        │
│   │  - get_prompt_versions(name, page?, limit?)                  │        │
│   └──────────────────────────────────────────────────────────────┘        │
│                           │                                                │
│                           ▼                                                │
│   ┌──────────────────────────────────────────────────────────────┐        │
│   │              Langfuse PostgreSQL Database                    │        │
│   │  - Prompts registry                                          │        │
│   │  - Version history                                           │        │
│   │  - Trace metadata                                            │        │
│   │  - Cost tracking data                                        │        │
│   └──────────────────────────────────────────────────────────────┘        │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP TOOL INVOCATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER REQUEST                                                        │
│     "Update the content analysis prompt to be more concise"            │
│                                                                         │
│  2. CLAUDE INTERPRETS INTENT                                            │
│     → Identifies: update_prompt tool needed                            │
│     → Extracts: prompt_name, new_content                               │
│                                                                         │
│  3. MCP TOOL CALL                                                       │
│     Tool: update_prompt                                                 │
│     Params: {                                                           │
│       "name": "content_analysis",                                       │
│       "prompt": "Analyze the following content...",                     │
│       "config": {"temperature": 0.7, "model": "claude-sonnet-4"}       │
│     }                                                                   │
│                                                                         │
│  4. LANGFUSE MCP SERVER PROCESSES                                       │
│     ✓ Authenticates using LANGFUSE_SECRET_KEY                          │
│     ✓ Validates prompt format                                          │
│     ✓ Creates new version in database                                  │
│     ✓ Returns version metadata                                         │
│                                                                         │
│  5. CLAUDE PRESENTS RESULT                                              │
│     "I've updated the content_analysis prompt to version 3.            │
│      The new version is more concise and focuses on key insights."     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Server Configuration

### .mcp.json Configuration

Add the Langfuse MCP server to your `.mcp.json` file:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    },
    "langfuse": {
      "command": "npx",
      "args": [
        "-y",
        "@langfuse/mcp-server"
      ],
      "env": {
        "LANGFUSE_HOST": "${LANGFUSE_HOST}",
        "LANGFUSE_PUBLIC_KEY": "${LANGFUSE_PUBLIC_KEY}",
        "LANGFUSE_SECRET_KEY": "${LANGFUSE_SECRET_KEY}"
      }
    }
  }
}
```

**Key Configuration Elements:**

| Field | Value | Purpose |
|-------|-------|---------|
| `command` | `npx` | Uses npx to run the MCP server without global install |
| `args[0]` | `-y` | Auto-accept package installation |
| `args[1]` | `@langfuse/mcp-server` | Official Langfuse MCP server package |
| `env.LANGFUSE_HOST` | `${LANGFUSE_HOST}` | Self-hosted Langfuse URL (e.g., http://localhost:3000) |
| `env.LANGFUSE_PUBLIC_KEY` | `${LANGFUSE_PUBLIC_KEY}` | Public API key for read operations |
| `env.LANGFUSE_SECRET_KEY` | `${LANGFUSE_SECRET_KEY}` | Secret API key for write operations |

**Environment Variable Interpolation:**
- The `${VAR_NAME}` syntax reads from `.mcp.env` file
- Claude Code CLI automatically loads `.mcp.env` before starting MCP servers
- Never hardcode credentials in `.mcp.json` (security risk)

---

## Credential Management

### .mcp.env Template

Create a `.mcp.env` file in the project root (same directory as `.mcp.json`):

```bash
# =============================================================================
# Langfuse MCP Server Credentials
# =============================================================================
# Copy this template to .mcp.env and fill in your Langfuse API credentials.
# This file is gitignored - NEVER commit credentials to version control.
#
# Get your API keys from:
#   1. Start Langfuse: docker-compose up -d langfuse-web langfuse-worker
#   2. Open: http://localhost:3000
#   3. Login: dev@skillforge.local / skillforge-dev-password
#   4. Navigate to: Project Settings → API Keys
#   5. Copy both Public Key and Secret Key
# =============================================================================

# -----------------------------------------------------------------------------
# Langfuse Connection Settings
# -----------------------------------------------------------------------------

# Langfuse host URL (self-hosted instance)
# Development: http://localhost:3000
# Production: https://langfuse.yourdomain.com
LANGFUSE_HOST=http://localhost:3000

# Langfuse Public Key (read-only operations)
# Format: pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# Used for: get_prompt, list_prompts, get_prompt_versions
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here

# Langfuse Secret Key (read-write operations)
# Format: sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
# Used for: create_prompt, update_prompt, trace queries
# SECURITY: Keep this secret! Never commit to git!
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here

# -----------------------------------------------------------------------------
# Optional: Project-Specific Settings
# -----------------------------------------------------------------------------

# Optional: Default project to use for MCP operations
# If not set, uses the default project from your Langfuse instance
# LANGFUSE_PROJECT_ID=

# Optional: Release/environment tagging for prompts
# Useful for separating dev/staging/production prompts
# LANGFUSE_RELEASE=development
```

### Security Best Practices

1. **File Permissions:**
   ```bash
   # Restrict .mcp.env to owner read/write only
   chmod 600 .mcp.env
   ```

2. **Git Ignore:**
   Ensure `.mcp.env` is in your `.gitignore`:
   ```gitignore
   # MCP Server credentials
   .mcp.env
   ```

3. **Key Rotation:**
   - Rotate keys every 90 days
   - Use different keys for development vs. production
   - Revoke keys immediately if compromised

4. **Access Control:**
   - Use read-only keys (`LANGFUSE_PUBLIC_KEY`) when possible
   - Limit secret key (`LANGFUSE_SECRET_KEY`) usage to trusted developers
   - Consider separate Langfuse projects for different teams

---

## MCP Tools Reference

### Tool 1: get_prompt

**Description:** Fetch a specific prompt version from Langfuse registry.

**Use Cases:**
- View current production prompt
- Compare prompt versions
- Inspect prompt configuration (model, temperature, etc.)
- Copy prompt for local testing

**Function Signature:**
```typescript
get_prompt(
  name: string,          // Prompt name (e.g., "content_analysis")
  version?: number,      // Optional: specific version number (default: latest)
  label?: string         // Optional: version label (e.g., "production", "staging")
): PromptVersion
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Unique prompt identifier |
| `version` | number | No | Specific version number (default: latest) |
| `label` | string | No | Version label filter (e.g., "production") |

**Response Schema:**
```typescript
interface PromptVersion {
  id: string;                   // Unique version ID
  name: string;                 // Prompt name
  version: number;              // Version number
  prompt: string;               // Prompt template content
  config: {                     // LLM configuration
    model?: string;             // e.g., "claude-sonnet-4"
    temperature?: number;       // e.g., 0.7
    max_tokens?: number;        // e.g., 2000
    [key: string]: any;         // Additional provider-specific config
  };
  labels: string[];             // Version labels (e.g., ["production"])
  created_at: string;           // ISO 8601 timestamp
  created_by: string;           // User who created this version
}
```

**Example Invocation:**
```plaintext
User: "Show me the latest content_analysis prompt"

Claude: [Calls get_prompt("content_analysis")]
```

**Example Response:**
```json
{
  "id": "pm_abc123",
  "name": "content_analysis",
  "version": 5,
  "prompt": "Analyze the following technical content and extract:\n1. Core concepts\n2. Implementation patterns\n3. Key insights\n\nContent: {{content}}",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "labels": ["production"],
  "created_at": "2025-12-15T10:30:00Z",
  "created_by": "yonatan@skillforge.dev"
}
```

---

### Tool 2: list_prompts

**Description:** List all prompts in the Langfuse registry with pagination.

**Use Cases:**
- Browse available prompts
- Audit prompt inventory
- Find prompts by naming convention
- Check prompt deployment status

**Function Signature:**
```typescript
list_prompts(
  page?: number,         // Page number (1-indexed, default: 1)
  limit?: number         // Items per page (default: 20, max: 100)
): PromptList
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | number | No | Page number (default: 1) |
| `limit` | number | No | Items per page (default: 20, max: 100) |

**Response Schema:**
```typescript
interface PromptList {
  data: PromptSummary[];        // Array of prompt summaries
  meta: {
    page: number;               // Current page
    limit: number;              // Items per page
    total_items: number;        // Total prompts
    total_pages: number;        // Total pages
  };
}

interface PromptSummary {
  name: string;                 // Prompt name
  latest_version: number;       // Latest version number
  labels: string[];             // Active labels
  created_at: string;           // First created timestamp
  updated_at: string;           // Last updated timestamp
  version_count: number;        // Total versions
}
```

**Example Invocation:**
```plaintext
User: "List all prompts in the system"

Claude: [Calls list_prompts(page=1, limit=20)]
```

**Example Response:**
```json
{
  "data": [
    {
      "name": "content_analysis",
      "latest_version": 5,
      "labels": ["production"],
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2025-12-15T10:30:00Z",
      "version_count": 5
    },
    {
      "name": "tech_comparison",
      "latest_version": 3,
      "labels": ["staging"],
      "created_at": "2025-11-05T14:20:00Z",
      "updated_at": "2025-12-10T09:15:00Z",
      "version_count": 3
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total_items": 2,
    "total_pages": 1
  }
}
```

---

### Tool 3: create_prompt

**Description:** Create a new prompt in the Langfuse registry.

**Use Cases:**
- Add new prompts from Claude Code session
- Test prompt variations quickly
- Document prompts with AI assistance
- Initialize prompt registry for new features

**Function Signature:**
```typescript
create_prompt(
  name: string,          // Unique prompt name
  prompt: string,        // Prompt template content
  config?: object,       // LLM configuration
  labels?: string[]      // Optional version labels
): PromptVersion
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Unique prompt identifier (alphanumeric + underscores) |
| `prompt` | string | Yes | Prompt template (supports {{variable}} placeholders) |
| `config` | object | No | LLM configuration (model, temperature, etc.) |
| `labels` | string[] | No | Version labels (e.g., ["development"]) |

**Config Schema:**
```typescript
interface PromptConfig {
  model?: string;              // LLM model name
  temperature?: number;        // 0.0-2.0 (default: provider default)
  max_tokens?: number;         // Max response tokens
  top_p?: number;              // Nucleus sampling (0.0-1.0)
  frequency_penalty?: number;  // -2.0 to 2.0
  presence_penalty?: number;   // -2.0 to 2.0
  [key: string]: any;          // Provider-specific config
}
```

**Example Invocation:**
```plaintext
User: "Create a new prompt called 'security_audit' for analyzing code security"

Claude: [Calls create_prompt with generated content]
```

**Example Request:**
```json
{
  "name": "security_audit",
  "prompt": "Analyze the following code for security vulnerabilities:\n\n{{code}}\n\nFocus on:\n1. SQL injection risks\n2. XSS vulnerabilities\n3. Authentication issues\n4. Data exposure risks",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.3,
    "max_tokens": 3000
  },
  "labels": ["development"]
}
```

**Example Response:**
```json
{
  "id": "pm_xyz789",
  "name": "security_audit",
  "version": 1,
  "prompt": "Analyze the following code for security vulnerabilities:\n\n{{code}}\n\nFocus on:\n1. SQL injection risks\n2. XSS vulnerabilities\n3. Authentication issues\n4. Data exposure risks",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.3,
    "max_tokens": 3000
  },
  "labels": ["development"],
  "created_at": "2025-12-19T15:45:00Z",
  "created_by": "yonatan@skillforge.dev"
}
```

---

### Tool 4: update_prompt

**Description:** Create a new version of an existing prompt.

**Use Cases:**
- Iterate on prompt quality
- A/B test prompt variations
- Promote prompts from dev → staging → production
- Fix issues in production prompts

**Function Signature:**
```typescript
update_prompt(
  name: string,          // Existing prompt name
  prompt: string,        // New prompt content
  config?: object,       // Updated LLM configuration
  labels?: string[]      // Updated labels
): PromptVersion
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Existing prompt name |
| `prompt` | string | Yes | New prompt template content |
| `config` | object | No | Updated LLM configuration |
| `labels` | string[] | No | Updated labels (replaces existing) |

**Versioning Behavior:**
- Creates a new version (increments version number)
- Previous versions remain accessible
- Labels are version-specific (not inherited)
- Config changes tracked in version history

**Example Invocation:**
```plaintext
User: "Update the content_analysis prompt to be more concise and focus on implementation details"

Claude: [Calls update_prompt with refined content]
```

**Example Request:**
```json
{
  "name": "content_analysis",
  "prompt": "Analyze this technical content for implementation patterns:\n\n{{content}}\n\nExtract:\n• Core concepts (1 sentence each)\n• Implementation steps (numbered list)\n• Code examples (if present)\n• Key insights (max 3)",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.5,
    "max_tokens": 1500
  },
  "labels": ["staging"]
}
```

**Example Response:**
```json
{
  "id": "pm_abc124",
  "name": "content_analysis",
  "version": 6,
  "prompt": "Analyze this technical content for implementation patterns:\n\n{{content}}\n\nExtract:\n• Core concepts (1 sentence each)\n• Implementation steps (numbered list)\n• Code examples (if present)\n• Key insights (max 3)",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.5,
    "max_tokens": 1500
  },
  "labels": ["staging"],
  "created_at": "2025-12-19T16:00:00Z",
  "created_by": "yonatan@skillforge.dev"
}
```

---

### Tool 5: get_prompt_versions

**Description:** Fetch version history for a specific prompt.

**Use Cases:**
- Compare prompt evolution over time
- Rollback to previous version
- Audit who changed what
- Analyze prompt performance by version

**Function Signature:**
```typescript
get_prompt_versions(
  name: string,          // Prompt name
  page?: number,         // Page number (default: 1)
  limit?: number         // Items per page (default: 20, max: 100)
): PromptVersionList
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Prompt name |
| `page` | number | No | Page number (default: 1) |
| `limit` | number | No | Items per page (default: 20, max: 100) |

**Response Schema:**
```typescript
interface PromptVersionList {
  data: PromptVersion[];        // Array of versions (newest first)
  meta: {
    page: number;
    limit: number;
    total_items: number;        // Total versions for this prompt
    total_pages: number;
  };
}
```

**Example Invocation:**
```plaintext
User: "Show me the version history for content_analysis prompt"

Claude: [Calls get_prompt_versions("content_analysis")]
```

**Example Response:**
```json
{
  "data": [
    {
      "id": "pm_abc124",
      "name": "content_analysis",
      "version": 6,
      "prompt": "Analyze this technical content for implementation patterns...",
      "config": {"model": "claude-sonnet-4-20250514", "temperature": 0.5},
      "labels": ["staging"],
      "created_at": "2025-12-19T16:00:00Z",
      "created_by": "yonatan@skillforge.dev"
    },
    {
      "id": "pm_abc123",
      "name": "content_analysis",
      "version": 5,
      "prompt": "Analyze the following technical content and extract...",
      "config": {"model": "claude-sonnet-4-20250514", "temperature": 0.7},
      "labels": ["production"],
      "created_at": "2025-12-15T10:30:00Z",
      "created_by": "yonatan@skillforge.dev"
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total_items": 6,
    "total_pages": 1
  }
}
```

---

## Common Workflows

### Workflow 1: Create and Test a New Prompt

**Scenario:** You need to create a new prompt for extracting code examples from technical articles.

**Steps:**

```plaintext
[User] "I need a new prompt for extracting code examples from articles.
        Can you help me create it?"

[Claude] "I'll help you create a code extraction prompt. Let me design
         it with clear instructions and variable placeholders."

[Claude calls create_prompt]:
{
  "name": "code_extractor",
  "prompt": "Extract all code examples from this article:\n\n{{article}}\n\n
             For each code block:\n1. Language/framework\n2. Purpose\n
             3. Key patterns\n4. Dependencies\n\nFormat as JSON array.",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.2,
    "max_tokens": 3000
  },
  "labels": ["development"]
}

[Claude] "I've created the code_extractor prompt (v1) in development.
         Would you like me to test it with a sample article?"

[User] "Yes, test it with the LangGraph guide"

[Claude] "Great! Let me retrieve the guide and test the prompt..."
[Proceeds with testing using the newly created prompt]
```

**Benefits:**
- AI-assisted prompt design
- Immediate testing capability
- Versioned from day one
- Clear development → production path

---

### Workflow 2: Compare Prompt Versions for A/B Testing

**Scenario:** You want to compare two versions of a prompt to see which performs better.

**Steps:**

```plaintext
[User] "Compare versions 5 and 6 of the content_analysis prompt.
        Which one is better?"

[Claude calls get_prompt("content_analysis", version=5)]
[Claude calls get_prompt("content_analysis", version=6)]

[Claude] "I've retrieved both versions. Here's the comparison:

VERSION 5 (Production):
- More verbose (150 tokens)
- Temperature: 0.7 (more creative)
- Max tokens: 2000
- Focus: Comprehensive analysis

VERSION 6 (Staging):
- More concise (80 tokens)
- Temperature: 0.5 (more focused)
- Max tokens: 1500
- Focus: Implementation patterns

Key differences:
1. V6 is 47% shorter (saves cost)
2. V6 uses lower temperature (more consistent)
3. V6 has explicit output format (bullet points)

Recommendation: Test v6 on 20% of traffic before full rollout."

[User] "Good analysis. Promote v6 to production"

[Claude calls update_prompt]:
{
  "name": "content_analysis",
  "prompt": "[content from v6]",
  "config": "[config from v6]",
  "labels": ["production"]
}

[Claude] "Done! Version 6 is now labeled 'production'.
         Version 5 remains available for rollback if needed."
```

**Benefits:**
- Data-driven prompt optimization
- Clear version comparison
- Safe rollback capability
- Cost impact visibility

---

### Workflow 3: Troubleshoot Prompt Performance Issues

**Scenario:** A prompt is producing poor results in production. You need to investigate and fix it.

**Steps:**

```plaintext
[User] "The tech_comparison prompt is giving shallow comparisons.
        Can you investigate?"

[Claude calls get_prompt("tech_comparison", label="production")]

[Claude] "I've retrieved the production prompt. Let me analyze it:

CURRENT PROMPT (v3):
'Compare {{tech_a}} and {{tech_b}}. List pros and cons.'

ISSUES IDENTIFIED:
1. Too vague - no structure
2. Missing comparison dimensions (performance, DX, ecosystem)
3. No output format specified
4. Temperature too high (0.9) - inconsistent results

RECOMMENDED FIX:
I'll create an improved version with:
- Structured comparison framework
- Explicit output format
- Lower temperature (0.5)
- Token limit reduction (cost optimization)"

[Claude calls update_prompt]:
{
  "name": "tech_comparison",
  "prompt": "Compare {{tech_a}} vs {{tech_b}}:\n\n
             1. Performance (latency, throughput)\n
             2. Developer Experience (API, docs)\n
             3. Ecosystem (libs, community)\n
             4. Use Cases (best for...)\n
             5. Trade-offs\n\nFormat as markdown table.",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.5,
    "max_tokens": 1500
  },
  "labels": ["staging"]
}

[Claude] "I've created version 4 in staging. Run it on test cases
         before promoting to production."
```

**Benefits:**
- Root cause analysis
- Immediate iteration
- Staged rollout (staging → production)
- Quality improvement tracking

---

### Workflow 4: Migrate Prompts from Code to Langfuse

**Scenario:** You have hardcoded prompts in your codebase and want to migrate them to Langfuse for better management.

**Steps:**

```plaintext
[User] "I have prompts hardcoded in app/workflows/tasks/runners.py.
        Help me migrate them to Langfuse."

[Claude reads the file]

[Claude] "I found 8 agent prompts in the file. I'll migrate them to
         Langfuse one by one. Let's start with the Tech Comparator:"

[Claude calls create_prompt]:
{
  "name": "agent_tech_comparator",
  "prompt": "[extracted from code]",
  "config": {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "labels": ["production"]
}

[Repeats for all 8 agents]

[Claude] "Migration complete! All 8 agent prompts are now in Langfuse:

1. agent_tech_comparator (v1)
2. agent_security_auditor (v1)
3. agent_implementation_planner (v1)
4. agent_code_inspector (v1)
5. agent_prerequisites_extractor (v1)
6. agent_learning_path (v1)
7. agent_use_case_analyzer (v1)
8. agent_integration_feasibility (v1)

Next steps:
1. Update code to use PromptManager.get_prompt()
2. Test each agent with Langfuse prompts
3. Remove hardcoded prompts from codebase
4. Add prompt versioning to CI/CD"

[User] "Perfect! Show me how to update the code"

[Claude generates refactored code with PromptManager integration]
```

**Benefits:**
- Centralized prompt management
- Version control for prompts
- No code deployments for prompt changes
- A/B testing capability

---

## CLAUDE.md Integration

Add the following section to your `CLAUDE.md` file to enable automatic Langfuse MCP awareness:

```markdown
## 🔧 Langfuse MCP Integration

**MCP Server:** langfuse (installed)
**Status:** Active
**Endpoint:** http://localhost:3000/api/public/mcp

### Available Tools

| Tool | Purpose | Common Use |
|------|---------|------------|
| `get_prompt` | Fetch prompt version | "Show me the RAG prompt" |
| `list_prompts` | Browse prompt registry | "List all production prompts" |
| `create_prompt` | Add new prompt | "Create a summarization prompt" |
| `update_prompt` | Create new version | "Make the prompt more concise" |
| `get_prompt_versions` | View version history | "Compare prompt versions" |

### Activation Triggers

**High-Confidence (Always Use Langfuse MCP):**
- "show/get the {name} prompt"
- "list all prompts"
- "create a prompt for {purpose}"
- "update/improve the {name} prompt"
- "compare prompt versions"
- "what changed in the {name} prompt"

**Medium-Confidence (Consider Langfuse MCP):**
- "why is {agent} giving poor results"
- "migrate prompts from code"
- "optimize prompt costs"
- "test prompt variations"

### Example Usage

```plaintext
User: "Show me the content_analysis prompt"
Claude: [Uses langfuse.get_prompt("content_analysis")]

User: "Make it more concise"
Claude: [Uses langfuse.update_prompt with refined version]

User: "List all agent prompts"
Claude: [Uses langfuse.list_prompts, filters by "agent_" prefix]
```

### Integration with Prompt Manager

The Langfuse MCP server works alongside the Python `PromptManager` service:

```
┌─────────────────────────────────────────────────────────────────┐
│                      PROMPT FLOW                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Development (Claude Code)                                      │
│  ────────────────────────                                       │
│  Claude MCP → Langfuse API → PostgreSQL                        │
│  (Direct prompt management)                                     │
│                                                                 │
│  Runtime (SkillForge Backend)                                   │
│  ───────────────────────────                                    │
│  PromptManager → Redis Cache → Langfuse API → PostgreSQL       │
│  (Multi-level cached retrieval)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- MCP server bypasses caching (always gets latest version)
- PromptManager uses 3-level caching (LRU → Redis → Langfuse)
- Both use the same Langfuse database (consistent state)
- Prompt updates via MCP are immediately visible to PromptManager
```

---

## Testing & Verification

### Pre-Deployment Checklist

Before using the Langfuse MCP integration, verify:

- [ ] **Langfuse Running:** `docker-compose ps langfuse-web` shows "Up"
- [ ] **UI Accessible:** http://localhost:3000 loads successfully
- [ ] **API Keys Generated:** Copied from Project Settings → API Keys
- [ ] **`.mcp.env` Created:** File exists in project root with keys
- [ ] **`.mcp.env` Permissions:** `ls -l .mcp.env` shows `-rw-------` (600)
- [ ] **`.mcp.env` Gitignored:** `git check-ignore .mcp.env` returns `.mcp.env`
- [ ] **`.mcp.json` Updated:** Langfuse server added to `mcpServers` object
- [ ] **Claude Code Restarted:** Close and reopen Claude Code CLI after config changes

### Verification Tests

#### Test 1: MCP Server Connection

```plaintext
User: "Can you list the available MCP tools?"

Expected: Claude should list langfuse tools (get_prompt, list_prompts, etc.)
```

#### Test 2: List Prompts

```plaintext
User: "List all prompts in Langfuse"

Expected: Returns prompt list (may be empty if first run)
```

#### Test 3: Create Prompt

```plaintext
User: "Create a test prompt called 'hello_world' that just says hello"

Expected: Successfully creates prompt, returns version 1
```

#### Test 4: Get Prompt

```plaintext
User: "Show me the hello_world prompt"

Expected: Returns the prompt you just created
```

#### Test 5: Update Prompt

```plaintext
User: "Update hello_world to say 'Hello, {{name}}!'"

Expected: Creates version 2, returns new content
```

#### Test 6: Version History

```plaintext
User: "Show version history for hello_world"

Expected: Returns 2 versions (v1 and v2)
```

### Debugging Connection Issues

If MCP tools aren't available, check the following:

```bash
# 1. Verify Langfuse is running
docker-compose ps langfuse-web
# Expected: State = Up

# 2. Test Langfuse API directly
curl http://localhost:3000/api/health
# Expected: {"status": "ok"}

# 3. Verify MCP server starts without errors
# Check Claude Code logs (location varies by platform):
# macOS: ~/Library/Logs/Claude/claude-code.log
# Look for lines containing "langfuse" and check for errors

# 4. Test API key authentication
curl -H "Authorization: Bearer ${LANGFUSE_PUBLIC_KEY}" \
     http://localhost:3000/api/public/prompts
# Expected: JSON response with prompts array

# 5. Validate .mcp.env format
cat .mcp.env | grep LANGFUSE
# Expected: All three variables set (LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
```

---

## Troubleshooting Guide

### Issue 1: MCP Server Not Found

**Symptoms:**
- Claude says "I don't have access to Langfuse tools"
- No langfuse tools in `/context` output

**Possible Causes:**

1. **`.mcp.json` not in project root**
   ```bash
   # Verify file location
   ls -la .mcp.json
   # Should be in same directory as CLAUDE.md
   ```

2. **Invalid JSON syntax**
   ```bash
   # Validate JSON
   cat .mcp.json | python -m json.tool
   # Should output formatted JSON without errors
   ```

3. **Claude Code not restarted**
   - Close and reopen Claude Code completely
   - MCP config is only loaded at startup

**Fix:**
- Ensure `.mcp.json` is in project root
- Validate JSON syntax
- Restart Claude Code CLI

---

### Issue 2: Authentication Failed

**Symptoms:**
- Error: "Unauthorized" or "Invalid API key"
- Tools available but return 401/403 errors

**Possible Causes:**

1. **Wrong API keys**
   ```bash
   # Verify keys match Langfuse UI
   cat .mcp.env | grep LANGFUSE_
   # Compare with Project Settings in Langfuse UI
   ```

2. **Keys not loaded**
   ```bash
   # Check if .mcp.env is in correct location
   ls -la .mcp.env
   # Should be in same directory as .mcp.json
   ```

3. **Wrong project keys**
   - Langfuse has multiple projects
   - Each project has different API keys

**Fix:**
1. Open Langfuse UI: http://localhost:3000
2. Navigate to: Project Settings → API Keys
3. Copy fresh keys
4. Update `.mcp.env`
5. Restart Claude Code

---

### Issue 3: Connection Timeout

**Symptoms:**
- Error: "Connection timeout"
- Tools hang for 30+ seconds

**Possible Causes:**

1. **Langfuse not running**
   ```bash
   docker-compose ps langfuse-web
   # Should show "Up"
   ```

2. **Wrong host URL**
   ```bash
   # Verify LANGFUSE_HOST in .mcp.env
   cat .mcp.env | grep LANGFUSE_HOST
   # Should be http://localhost:3000 for local dev
   ```

3. **Network issues**
   ```bash
   # Test direct API access
   curl -I http://localhost:3000/api/health
   # Should return 200 OK
   ```

**Fix:**
1. Start Langfuse: `docker-compose up -d langfuse-web langfuse-worker`
2. Verify host URL matches running instance
3. Check firewall/VPN blocking localhost:3000

---

### Issue 4: Prompt Not Found

**Symptoms:**
- Error: "Prompt 'xyz' not found"
- `get_prompt` returns null/empty

**Possible Causes:**

1. **Wrong prompt name**
   - Prompt names are case-sensitive
   - Check exact name with `list_prompts`

2. **Prompt in different project**
   - Langfuse supports multiple projects
   - API keys are project-specific

3. **Version/label mismatch**
   - Requesting version that doesn't exist
   - Label filter excludes all versions

**Fix:**
```plaintext
User: "List all prompts"
[Verify exact prompt name]

User: "Show versions for {correct_name}"
[Check which versions exist]

User: "Get {correct_name} version {existing_version}"
[Use specific version]
```

---

### Issue 5: Create/Update Prompt Fails

**Symptoms:**
- Error: "Failed to create/update prompt"
- 400 Bad Request errors

**Possible Causes:**

1. **Invalid prompt name**
   - Must be alphanumeric + underscores
   - No spaces or special characters

2. **Missing required fields**
   ```typescript
   // Required fields
   {
     "name": "required",
     "prompt": "required"
   }
   ```

3. **Invalid config format**
   ```typescript
   // Config must be valid JSON object
   {
     "config": {
       "model": "string",
       "temperature": 0.7  // number, not string
     }
   }
   ```

**Fix:**
1. Use snake_case names: `content_analysis`, not `Content Analysis`
2. Ensure all required fields present
3. Validate config as JSON object
4. Check Langfuse UI for error details

---

### Issue 6: Stale Prompt Versions

**Symptoms:**
- Backend uses old prompt version
- Recent MCP updates not reflected in runtime

**Cause:**
- PromptManager has 3-level caching (LRU → Redis → Langfuse)
- Cache TTL defaults to 5 minutes
- Prompt updated via MCP but cache not invalidated

**Fix Option 1 - Wait for TTL:**
```bash
# Wait 5 minutes for cache to expire
sleep 300
# Test again
```

**Fix Option 2 - Clear Redis Cache:**
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Clear prompt cache namespace
KEYS prompt:*
DEL prompt:content_analysis:v6
DEL prompt:content_analysis:latest
```

**Fix Option 3 - Restart Backend:**
```bash
# Restart backend to clear LRU cache
docker-compose restart backend
```

**Prevention:**
- Set lower cache TTL for development: `REDIS_CACHE_TTL=60`
- Use cache invalidation in PromptManager (future enhancement)
- Label development prompts differently than production

---

## Security Best Practices

### 1. Credential Management

**DO:**
- ✅ Store credentials in `.mcp.env` (gitignored)
- ✅ Use `chmod 600 .mcp.env` (owner read/write only)
- ✅ Rotate keys every 90 days
- ✅ Use separate keys for dev/staging/production
- ✅ Revoke compromised keys immediately

**DON'T:**
- ❌ Hardcode keys in `.mcp.json`
- ❌ Commit `.mcp.env` to git
- ❌ Share keys via Slack/email
- ❌ Use production keys in development
- ❌ Reuse keys across projects

### 2. Access Control

**Production Prompts:**
- Use read-only keys for most developers
- Limit write access to senior engineers
- Require PR review for production prompt changes
- Use label-based environments (dev/staging/production)

**Sensitive Prompts:**
- Store security-critical prompts in separate Langfuse project
- Use different API keys with restricted access
- Enable audit logging for prompt changes

### 3. Network Security

**Self-Hosted Langfuse:**
- Use HTTPS in production (`https://langfuse.yourdomain.com`)
- Enable authentication/authorization
- Restrict network access (firewall rules)
- Use reverse proxy (nginx/caddy)

**Cloud-Hosted Langfuse:**
- Use VPN or private network
- Enable IP whitelisting
- Use API key rotation

### 4. Audit Trail

**Enable Logging:**
- Langfuse tracks all prompt changes (who, when, what)
- Review audit logs monthly
- Set up alerts for suspicious activity

**Change Management:**
- Document why prompts were changed
- Link changes to GitHub issues/PRs
- Use version labels to track rollouts

---

## Appendix: MCP Architecture Details

### MCP Protocol Overview

**Model Context Protocol (MCP)** is a standardized way for AI models to interact with external tools and data sources. It uses stdio (stdin/stdout) for communication between the Claude Code CLI and MCP servers.

```
┌────────────────────────────────────────────────────────────────────────┐
│                       MCP PROTOCOL LAYERS                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Layer 4: Application (Claude Code CLI)                                │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  User: "Show me the content_analysis prompt"                 │     │
│  │  Claude: Interprets intent → Calls tool → Formats response   │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                           │                                            │
│                           ▼                                            │
│  Layer 3: Tool Invocation (MCP Client)                                 │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  Tool: get_prompt                                            │     │
│  │  Params: {"name": "content_analysis"}                        │     │
│  │  Serialization: JSON-RPC 2.0                                 │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                           │                                            │
│                           ▼                                            │
│  Layer 2: Transport (stdio)                                            │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  stdin → MCP Server: {"method":"tools/call",...}             │     │
│  │  stdout ← MCP Server: {"result":{...}}                       │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                           │                                            │
│                           ▼                                            │
│  Layer 1: MCP Server (Langfuse)                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  1. Parse JSON-RPC request                                   │     │
│  │  2. Authenticate with Langfuse API                           │     │
│  │  3. Execute tool logic                                       │     │
│  │  4. Return JSON-RPC response                                 │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Langfuse MCP Implementation

The Langfuse MCP server is implemented as a Node.js package (`@langfuse/mcp-server`) that:

1. **Exposes 5 tools** via MCP protocol
2. **Authenticates** using Langfuse API keys (from environment)
3. **Proxies requests** to Langfuse REST API
4. **Formats responses** as JSON-RPC 2.0

**Source Code:** https://github.com/langfuse/langfuse-mcp

---

## Next Steps

### Immediate Actions

1. **Install MCP Server:**
   ```bash
   # Add langfuse to .mcp.json (see configuration section)
   # Create .mcp.env with API keys
   # Restart Claude Code CLI
   ```

2. **Verify Installation:**
   ```plaintext
   User: "List all Langfuse prompts"
   # Should work without errors
   ```

3. **Migrate First Prompt:**
   ```plaintext
   User: "Create a test_prompt to verify the integration"
   # Test full create → get → update → versions workflow
   ```

### Integration Milestones

- [ ] **Week 1:** Install and verify MCP integration
- [ ] **Week 2:** Migrate 3 high-impact prompts from code to Langfuse
- [ ] **Week 3:** Add prompt versioning to CI/CD
- [ ] **Week 4:** Enable A/B testing for 1 prompt
- [ ] **Month 2:** Migrate all 8 agent prompts
- [ ] **Month 3:** Implement automatic prompt optimization based on trace data

### Advanced Features (Future)

- **Prompt Optimization:** Analyze trace data to automatically suggest prompt improvements
- **Cost Tracking:** Query token usage and costs per prompt version
- **Trace Analysis:** Link prompts to trace quality metrics
- **Batch Operations:** Bulk update prompts across environments

---

**Documentation Version:** 1.0.0
**Last Updated:** December 19, 2025
**Maintained By:** Yonatan Gross (yonatan@skillforge.dev)

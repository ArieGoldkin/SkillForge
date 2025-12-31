# Cursor IDE Rules for Claude Agents & Skills

This directory contains Cursor IDE rules that bridge the gap between Cursor IDE's rule system and the existing `.claude/agents/` and `.claude/skills/` structure used by Claude Code.

## Directory Structure

```
.cursor/rules/
├── agents/              # Agent rule files (one per agent)
│   ├── backend-system-architect.mdc
│   ├── frontend-ui-developer.mdc
│   └── ...
├── skills/              # Skill rule files (key skills)
│   ├── langgraph-workflows.mdc
│   ├── api-design-framework.mdc
│   └── ...
├── agent-delegation.mdc # Agent selection guide
├── skill-usage.mdc      # Progressive skill loading guide
└── README.md           # This file
```

## How It Works

### Cursor IDE vs Claude Code

**Claude Code** (terminal-based):
- Native support for `.claude/agents/` and `.claude/skills/`
- Auto-discovery via `agent-registry.json`
- Direct agent invocation via Task tool

**Cursor IDE** (editor-based):
- Uses `.cursor/rules/` directory with `.mdc` files
- Rules are instructions, not executable agents
- Rules reference `.claude/` structure for patterns

### Rule Files (.mdc format)

Each rule file contains:
- **Metadata** (YAML frontmatter): description, globs, priority, alwaysApply
- **Content**: When to use, capabilities, examples, references

### Agent Rules

Agent rule files (`.cursor/rules/agents/*.mdc`) provide:
- When to use the agent pattern
- Key capabilities from `agent-registry.json`
- Related skills to reference
- Example usage patterns
- Model selection guidance
- Boundary constraints

### Skill Rules

Skill rule files (`.cursor/rules/skills/*.mdc`) provide:
- Progressive loading protocol (capabilities.json → SKILL.md → references)
- What the skill provides
- When to use it
- Related agents
- Token optimization strategies

## Usage

### For Cursor IDE

1. **Automatic**: Cursor IDE reads `.cursor/rules/` automatically
2. **Context-aware**: Rules with `globs` apply when matching files are open
3. **Priority**: Rules with higher `priority` are considered first
4. **Always apply**: Rules with `alwaysApply: true` are always considered

### For Developers

When working on a task:

1. **Check agent rules**: See `.cursor/rules/agents/` for relevant agent patterns
2. **Check skill rules**: See `.cursor/rules/skills/` for relevant skill patterns
3. **Reference full definitions**: Follow links to `.claude/agents/` and `.claude/skills/`
4. **Use delegation guide**: See `agent-delegation.mdc` for agent selection
5. **Optimize loading**: See `skill-usage.mdc` for progressive skill loading

## Key Files

- **agent-delegation.mdc**: Decision tree for selecting the right agent
- **skill-usage.mdc**: Progressive loading protocol to save tokens
- **mcp-usage.mdc**: MCP server usage guide and tool selection
- **agents/*.mdc**: Individual agent pattern guides
- **skills/*.mdc**: Individual skill usage guides

## Source of Truth

The `.claude/` directory structure remains the source of truth:
- `.claude/agents/` - Full agent definitions
- `.claude/skills/` - Full skill definitions
- `.claude/agent-registry.json` - Agent and skill catalog

Cursor IDE rules act as a bridge/interface to help Cursor understand and use the Claude structure.

## MCP Configuration

MCP servers use environment variables from `.mcp.env`:

1. **Copy template**: `cp .mcp.env.example .mcp.env`
2. **Fill in values**: Edit `.mcp.env` with your actual credentials
3. **Never commit**: `.mcp.env` is in `.gitignore` (secrets!)
4. **Restart Cursor**: After changing `.mcp.env`, restart Cursor IDE

**Files**:
- `.mcp.json` - Server definitions (committed)
- `.mcp.env` - Environment variables (NOT committed)
- `.mcp.env.example` - Template (committed)

See `.cursor/rules/mcp-usage.mdc` for detailed MCP usage guide.

## Best Practices

1. **Keep rules focused**: Each rule file <200 lines
2. **Reference full definitions**: Point to `.claude/` for details
3. **Use metadata**: Leverage `globs`, `alwaysApply`, `priority`
4. **Progressive loading**: Load skills incrementally, not all at once
5. **Check workflows**: Use pre-composed workflows when available
6. **Use `.mcp.env`**: Never hardcode secrets in `.mcp.json`

## Integration with .cursorrules

The main `.cursorrules` file references this directory and provides:
- High-level project rules
- Quality gates
- Code standards
- Links to agent/skill system

See `.cursorrules` for the complete project rules.

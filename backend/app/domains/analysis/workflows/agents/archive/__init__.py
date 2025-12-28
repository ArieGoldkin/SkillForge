"""Archived agents - not currently connected to the workflow.

These agents are preserved for potential future use but are NOT
imported or executed by the current LangGraph workflow.

To revive an agent:
1. Move the file to the parent agents/ directory
2. Add to agents/__init__.py
3. Create corresponding node in nodes/
4. Wire into the LangGraph workflow

See README.md for why each agent was archived.
"""

# Intentionally empty - do not export anything

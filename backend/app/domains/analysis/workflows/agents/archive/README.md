# Archived Agents

These agents were removed from the active workflow but preserved for future use.

## Why Archived

| Agent | Reason | Date | Issue |
|-------|--------|------|-------|
| fact_validator | Tier 2 validation - not yet integrated | Dec 2025 | #414 |
| research_analyst | Superseded by deep_researcher | Dec 2025 | #414 |
| freshness_checker | Tier 2 validation - not yet integrated | Dec 2025 | #414 |
| alternatives_finder | Tier 2 validation - not yet integrated | Dec 2025 | #414 |
| source_credibility | Tier 2 validation - not yet integrated | Dec 2025 | #414 |

## Revival Instructions

1. Move agent file to `agents/` directory
2. Add import to `agents/__init__.py`
3. Create node in `nodes/{agent_name}_node.py`
4. Add node to LangGraph workflow in `graph.py`
5. Add routing logic in supervisor

## Template Locations

Templates for these agents are preserved in `app/shared/services/prompts/templates/agents/_archive/`:
- `alternatives_finder.j2`
- `freshness_checker.j2`
- `research_analyst.j2`
- `source_credibility.j2`

The `fact_validator.j2` template is still in `templates/agents/tier2/` since it may be integrated in the future.

## Prompt Manager Mapping

The archived agents are still mapped in `app/shared/services/prompts/prompt_manager.py` under the "Archive" section (lines 73-77) for easy revival.

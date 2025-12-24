# Issue #498: Agent Registry with Tier Metadata

## Summary

Create an agent registry system with tier metadata to support 3-tier agent architecture.

**Design:** See [GitHub Issue #498](https://github.com/ArieGoldkin/SkillForge/issues/498) for full specification.

## Quick Reference

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: UNIVERSAL     │  Always run on ALL content        │
│  ──────────────────────┼──────────────────────────────────  │
│  KEY_INSIGHTS          │  PROS_CONS                        │
│  AUDIENCE_FIT          │  ACTIONABLE                       │
├─────────────────────────────────────────────────────────────┤
│  TIER 2: VALIDATION    │  Tool-enabled, Standard mode+     │
│  ──────────────────────┼──────────────────────────────────  │
│  FACT_VALIDATOR        │  SOURCE_CREDIBILITY               │
│  FRESHNESS_CHECKER     │  ALTERNATIVES_FINDER              │
├─────────────────────────────────────────────────────────────┤
│  TIER 3: RESEARCH      │  Deep dive only, memory-enabled   │
│  ──────────────────────┼──────────────────────────────────  │
│  DEEP_RESEARCHER       │  COMMUNITY_PULSE                  │
│  KNOWLEDGE_CURATOR     │  LEARNING_PATH_ADVISOR            │
└─────────────────────────────────────────────────────────────┘
```

## Implementation

File: `app/domains/analysis/agents/registry.py`

```python
from enum import IntEnum
from dataclasses import dataclass

class AgentTier(IntEnum):
    UNIVERSAL = 1    # Always run
    VALIDATION = 2   # Standard mode+
    RESEARCH = 3     # Deep dive only

@dataclass
class AgentMetadata:
    name: str
    tier: AgentTier
    tools: list[str] = None
    requires_memory: bool = False

def get_agents_for_mode(mode: AnalysisMode) -> list[str]:
    max_tier = {
        AnalysisMode.QUICK: AgentTier.UNIVERSAL,
        AnalysisMode.STANDARD: AgentTier.VALIDATION,
        AnalysisMode.DEEP_DIVE: AgentTier.RESEARCH,
    }[mode]
    return [name for name, meta in AGENT_REGISTRY.items() if meta.tier <= max_tier]
```

## Acceptance Criteria

From issue #498:
- [ ] AgentRegistry class with tier metadata
- [ ] `get_agents_for_mode()` returns correct agents per mode
- [ ] Existing 8 agents mapped to appropriate tiers
- [ ] Unit tests for registry operations
- [ ] Documentation for adding new agents

## References

- [GitHub Issue #498](https://github.com/ArieGoldkin/SkillForge/issues/498)
- Depends on: #490 (Content-Type Routing) ✅ CLOSED

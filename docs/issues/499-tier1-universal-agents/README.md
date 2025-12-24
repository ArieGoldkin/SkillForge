# Issue #499: Tier 1 Universal Agents (Always Run)

## Summary

Implement 4 universal agents that run on ALL content types, replacing code-focused agents that fail on non-code content.

**Design:** See [GitHub Issue #499](https://github.com/ArieGoldkin/SkillForge/issues/499)
**Depends on:** #498 (Agent Registry) ✅ CLOSED, #490 (Content-Type Routing) ✅ CLOSED

## Universal Agents (Tier 1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 1: UNIVERSAL - Always run on ALL content                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  KEY_INSIGHTS          │  Extract 3-5 main takeaways                   │
│  ──────────────────────┼────────────────────────────────────────────── │
│  - What matters most   │  insights: list[Insight]                      │
│  - Why it's important  │  novelty_score: float                         │
│                                                                         │
│  PROS_CONS             │  Balanced analysis                            │
│  ──────────────────────┼────────────────────────────────────────────── │
│  - Strengths/weaknesses│  pros: list[str], cons: list[str]             │
│  - Overall verdict     │  verdict: str                                 │
│                                                                         │
│  AUDIENCE_FIT          │  Who benefits from this                       │
│  ──────────────────────┼────────────────────────────────────────────── │
│  - Target audiences    │  audiences: list[Audience]                    │
│  - Prerequisites       │  prerequisites: list[str]                     │
│                                                                         │
│  ACTIONABLE            │  Concrete next steps                          │
│  ──────────────────────┼────────────────────────────────────────────── │
│  - What to do next     │  actions: list[Action]                        │
│  - Helpful resources   │  resources: list[Resource]                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why Universal?

These agents work on ANY content type:
- ✅ News article → Extracts key insights about announcement
- ✅ Tutorial → Summarizes what you'll learn
- ✅ Research paper → Distills main findings
- ✅ Code repo → Explains what it does and who needs it

## Implementation Approach

Uses registry from #498 for tier metadata. Each agent:
1. Inherits from `BaseUniversalAgent`
2. Has Pydantic output schema for validation
3. Uses content-agnostic prompts (no code assumptions)
4. Integrates with Langfuse for observability

## Acceptance Criteria

From issue #499:
- [ ] 4 universal agents implemented
- [ ] All work on news articles (no code assumptions)
- [ ] All work on tutorials with code
- [ ] All work on research papers
- [ ] Output schemas validated with Pydantic
- [ ] Unit tests with golden dataset (3 content types)
- [ ] Langfuse traces show all 4 agents run

## References

- [GitHub Issue #499](https://github.com/ArieGoldkin/SkillForge/issues/499)
- Depends on: #498 (Agent Registry) ✅, #490 (Content-Type Routing) ✅

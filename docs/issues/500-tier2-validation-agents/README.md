# Issue #500: Tier 2 Validation Agents + Tavily Integration

## Summary

Implement 4 validation agents with external tool access (Tavily Search, GitHub API) for fact-checking and freshness validation. These Tier 2 agents run in Standard/Deep mode only (not Quick).

## Validation Agents (Tier 2)

| Agent | Purpose | Tools | Output |
|-------|---------|-------|--------|
| **FACT_VALIDATOR** | Verify claims against web sources | Tavily Search | `claims: list[Claim], validation_score: float` |
| **SOURCE_CREDIBILITY** | Assess source reputation | Heuristics + GitHub | `credibility_score: float, signals: list[Signal]` |
| **FRESHNESS_CHECKER** | Check if content is current | GitHub, npm, PyPI APIs | `is_outdated: bool, latest_versions: dict` |
| **ALTERNATIVES_FINDER** | Find competing solutions | Tavily + PGVector | `alternatives: list[Alternative]` |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYSIS WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│  Tier 1 (Universal)     │  Tier 2 (Validation)    │  Tier 3     │
│  ─────────────────────  │  ─────────────────────  │  ────────── │
│  • key_insights         │  • fact_validator       │  • security │
│  • pros_cons            │  • source_credibility   │  • deps     │
│  • actionable           │  • freshness_checker    │  • tech_cmp │
│  • audience_fit         │  • alternatives_finder  │  • code_ql  │
│                         │                         │             │
│  [No external tools]    │  [Tavily, GitHub, npm]  │  [GitHub++] │
│  Always runs            │  Standard/Deep only     │  Deep only  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      EXTERNAL SERVICES         │
                    ├───────────────────────────────┤
                    │  Tavily API ($0.01/search)    │
                    │  GitHub API (free, rate-ltd)  │
                    │  npm/PyPI (free, rate-ltd)    │
                    └───────────────────────────────┘
```

## Tool Integration

### Tavily Search API
- Web search for fact validation
- ~3 searches per analysis = $0.03/analysis
- Advanced search depth with answer extraction

### GitHub API
- Repository stats for credibility signals
- Release/version checking for freshness
- Rate limited: 5000 req/hour with token

### npm/PyPI APIs
- Package version checking
- Latest version comparison
- Free, rate-limited

## Implementation Phases

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| 1 | Tavily tool wrapper + config | ~2 hours |
| 2 | fact_validator agent | ~3 hours |
| 3 | source_credibility agent | ~2 hours |
| 4 | freshness_checker agent | ~2 hours |
| 5 | alternatives_finder agent | ~3 hours |
| 6 | Registry integration + tests | ~2 hours |

### Phase 1: Tavily Tool Wrapper
- [ ] Add `TAVILY_API_KEY` to config
- [ ] Create `app/shared/services/tools/tavily_search.py`
- [ ] Implement search with caching (Redis)
- [ ] Add to MCP registry

### Phase 2: Fact Validator Agent
- [ ] Create `app/domains/analysis/workflows/agents/fact_validator.py`
- [ ] Implement claim extraction prompt
- [ ] Implement validation logic with Tavily
- [ ] Add to agent registry as Tier 2

### Phase 3: Source Credibility Agent
- [ ] Create `app/domains/analysis/workflows/agents/source_credibility.py`
- [ ] Implement credibility heuristics
- [ ] Integrate GitHub API for repo stats
- [ ] Add to agent registry as Tier 2

### Phase 4: Freshness Checker Agent
- [ ] Create `app/domains/analysis/workflows/agents/freshness_checker.py`
- [ ] Implement version extraction from content
- [ ] Integrate npm/PyPI version APIs
- [ ] Add to agent registry as Tier 2

### Phase 5: Alternatives Finder Agent
- [ ] Create `app/domains/analysis/workflows/agents/alternatives_finder.py`
- [ ] Implement Tavily search for alternatives
- [ ] Integrate PGVector for similar past analyses
- [ ] Add to agent registry as Tier 2

### Phase 6: Integration
- [ ] Update supervisor to route Tier 2 agents
- [ ] Add mode gating (Standard/Deep only)
- [ ] Add Langfuse traces for tool calls
- [ ] Comprehensive unit tests

## Cost Analysis

| Component | Cost per Call | Notes |
|-----------|--------------|-------|
| Tavily Search | $0.01/search | ~3 searches per analysis |
| GitHub API | Free | Rate limited |
| npm/PyPI API | Free | Rate limited |
| LLM (validation) | $0.0004 | DeepSeek V3 |
| **Total Tier 2** | **~$0.035** | Per analysis |

## File-by-File Implementation

| File | Change Type | Description |
|------|-------------|-------------|
| `app/core/config.py` | Modify | Add TAVILY_API_KEY |
| `app/shared/services/tools/tavily_search.py` | **New** | Tavily search wrapper |
| `app/domains/analysis/workflows/agents/fact_validator.py` | **New** | Fact validation agent |
| `app/domains/analysis/workflows/agents/source_credibility.py` | **New** | Source credibility agent |
| `app/domains/analysis/workflows/agents/freshness_checker.py` | **New** | Freshness checking agent |
| `app/domains/analysis/workflows/agents/alternatives_finder.py` | **New** | Alternatives finder agent |
| `app/shared/services/mcp/registry.py` | Modify | Add Tier 2 agent configs |
| `tests/unit/domains/analysis/workflows/agents/test_tier2_agents.py` | **New** | Tier 2 agent tests |

## Acceptance Criteria

- [ ] Tavily Search integration working
- [ ] GitHub API wrapper for repo stats
- [ ] npm/PyPI version checking
- [ ] 4 validation agents implemented
- [ ] Tool results cached (Redis) to reduce costs
- [ ] Agents only run in Standard/Deep mode (not Quick)
- [ ] Langfuse traces show tool calls
- [ ] All tests pass
- [ ] Lint checks pass

## Dependencies

- **#498** (Agent Registry) - ✅ Completed
- **#436** (MCP Tool Integration) - ✅ Completed

## References

- [GitHub Issue #500](https://github.com/ArieGoldkin/SkillForge/issues/500)
- [Tavily API Docs](https://docs.tavily.com/)
- [LangGraph Tool-Calling](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/)

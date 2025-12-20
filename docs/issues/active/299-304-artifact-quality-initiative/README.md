# Issues #299-#304: Artifact Quality Initiative

**Status:** Planning
**Branch:** `issue/299-304-artifact-quality-initiative`
**Date:** 2025-12-14

## Executive Summary

This initiative transforms SkillForge artifacts from basic summaries into **triple-purpose documents** that serve:
1. **AI Coding Assistants** (Claude Code, Cursor, Windsurf, Copilot, etc.)
2. **Tutor System** (syllabus generation, Socratic questioning, lesson delivery)
3. **Human Readers** (learning, documentation, reference)

## Problem Statement

### Current State

The golden dataset loader (`load_golden_dataset.py`) creates **fake artifacts** using `generate_artifact_markdown()` that bypass the entire LangGraph workflow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT ARTIFACT GENERATION (BROKEN)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   load_golden_dataset.py                                                │
│          │                                                              │
│          ▼                                                              │
│   ┌──────────────────┐                                                  │
│   │ generate_artifact│  Bypasses entire workflow!                       │
│   │ _markdown()      │  Creates fake content with:                      │
│   │                  │  - Generic code snippets                         │
│   │                  │  - No agent analysis                             │
│   │                  │  - No real insights                              │
│   └────────┬─────────┘                                                  │
│            │                                                            │
│            ▼                                                            │
│   ┌──────────────────┐                                                  │
│   │ "Artifact"       │  Result: Short, useless documents                │
│   │ (98 documents)   │  with 0 agent findings                           │
│   └──────────────────┘                                                  │
│                                                                         │
│   8 Agents: ████████ (COMPLETELY BYPASSED)                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Impact

| Consumer | Current Experience | Target Experience |
|----------|-------------------|-------------------|
| **AI Assistants** | No usable prompts | Copy-paste implementation guide |
| **Tutor System** | No concepts/exercises | Structured lessons + quizzes |
| **Humans** | Generic summaries | Rich learning document |

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEW ARTIFACT GENERATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   URL/Content Input                                                          │
│          │                                                                   │
│          ▼                                                                   │
│   ┌──────────────┐    ┌──────────────┐                                       │
│   │ Content      │    │ Proactive    │ #300                                  │
│   │ Extraction   │───▶│ Memory       │ Inject relevant past                  │
│   │ (Jina AI)    │    │ Recall       │ analyses into context                 │
│   └──────┬───────┘    └──────┬───────┘                                       │
│          │                   │                                               │
│          ▼                   ▼                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    8-AGENT FAN-OUT                                   │   │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │   │
│   │  │Tech     │ │Security │ │Implement│ │Pattern  │                    │   │
│   │  │Comparator│ │Auditor │ │Planner │ │Recognizer│                    │   │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                    │   │
│   │       │           │           │           │                         │   │
│   │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐                    │   │
│   │  │Dependency│ │Code    │ │Complexity│ │Learning │                    │   │
│   │  │Mapper   │ │Extractor│ │Assessor │ │Path     │                    │   │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                    │   │
│   └───────┼───────────┼───────────┼───────────┼─────────────────────────┘   │
│           │           │           │           │                              │
│           └───────────┴─────┬─────┴───────────┘                              │
│                             ▼                                                │
│                   ┌──────────────────┐                                       │
│                   │ AGGREGATION +    │ #302 + #303                           │
│                   │ SYNTHESIS        │ New schema + prompt                   │
│                   │                  │ for triple-consumer                   │
│                   └────────┬─────────┘                                       │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌──────────────────┐                                       │
│                   │ QUALITY GATE     │ #301                                  │
│                   │ (LLM-as-Judge)   │ Evaluate before                       │
│                   │                  │ proceeding                            │
│                   └────────┬─────────┘                                       │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌──────────────────┐                                       │
│                   │ ARTIFACT         │ #304                                  │
│                   │ TEMPLATE         │ Jinja2 rendering                      │
│                   │ (artifact.j2)    │ for all consumers                     │
│                   └────────┬─────────┘                                       │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌──────────────────┐                                       │
│                   │ TRIPLE-PURPOSE   │                                       │
│                   │ ARTIFACT         │                                       │
│                   │                  │                                       │
│                   │ • AI Prompt      │ ◀── For Claude Code, Cursor, etc.    │
│                   │ • Core Concepts  │ ◀── For Tutor System                 │
│                   │ • Exercises      │ ◀── For Learning                     │
│                   │ • Diagrams       │ ◀── For Visual Learners              │
│                   │ • TL;DR          │ ◀── For Quick Reference              │
│                   └──────────────────┘                                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Issue Breakdown

### Issue #299: Golden Dataset Fix (Critical)

**Problem:** `generate_artifact_markdown()` creates fake content bypassing workflow.

**Solution:** Delete this function and update the loader to either:
- Run minimal workflow with test data, OR
- Use backup/restore from real analyses

**Files:**
- `backend/scripts/load_golden_dataset.py` - Delete fake generation

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/299

---

### Issue #300: Proactive Memory Recall (High Priority)

**Problem:** Existing `proactive_recall.py` is implemented but not wired into workflow.

**Solution:** Add `inject_context` node before agent fan-out that:
1. Queries similar past analyses via vector search
2. Injects relevant findings into agent prompts
3. Enables cross-document learning

**Files:**
- `backend/app/workflows/graph_builder.py` - Add inject_context node
- `backend/app/services/memory/proactive_recall.py` - Already exists

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/300

---

### Issue #301: Quality Validation Gate (High Priority)

**Problem:** No quality checks before artifact generation.

**Solution:** Add `quality_gate` node after synthesis that:
1. Uses existing LLM-as-judge evaluators
2. Validates relevance, depth, coherence
3. Triggers retry if below threshold

**Files:**
- `backend/app/workflows/graph_builder.py` - Add quality_gate node
- `backend/app/evaluation/evaluators/quality.py` - Already exists

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/301

---

### Issue #302: Triple-Purpose Schema Enhancement (Critical)

**Problem:** Current `AggregatedInsights` schema lacks fields for all three consumers.

**Solution:** Add new Pydantic models:

```python
class TLDRSection(BaseModel):
    summary: str
    key_takeaways: list[str]
    time_to_implement: str

class CoreConcept(BaseModel):
    name: str
    definition: str
    why_it_matters: str
    related_concepts: list[str]
    complexity_level: Literal["beginner", "intermediate", "advanced"]

class AIAssistantPrompt(BaseModel):
    context: str
    implementation_steps: list[str]
    code_snippets: list[CodeSnippet]
    file_structure: dict[str, Any]
    success_criteria: list[str]

class Exercise(BaseModel):
    title: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    hints: list[str]
    solution: str
    learning_objectives: list[str]

class MermaidDiagram(BaseModel):
    title: str
    type: Literal["flowchart", "sequence", "class", "er"]
    mermaid_code: str
    description: str

class SelfAssessment(BaseModel):
    quiz_questions: list[QuizQuestion]
    mastery_checklist: list[str]

class GlossaryTerm(BaseModel):
    term: str
    definition: str
    see_also: list[str]
```

**Files:**
- `backend/app/workflows/tasks/schemas/aggregated_insights.py`

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/302

---

### Issue #303: Synthesis Prompt Rewrite (Critical)

**Problem:** Current prompt produces generic summaries without triple-consumer fields.

**Solution:** Rewrite `AGGREGATED_INSIGHTS_SYNTHESIS_PROMPT` to:
1. Request all new schema fields
2. Map each agent's findings to specific output sections
3. Include validation and retry logic

**Agent → Output Mapping:**

| Agent | Contributes To |
|-------|---------------|
| `tech_comparator` | TL;DR tradeoffs, glossary terms |
| `security_auditor` | Exercises (security challenges), pitfalls |
| `implementation_planner` | AI prompt steps, file structure |
| `pattern_recognizer` | Diagrams (patterns), core concepts |
| `dependency_mapper` | Prerequisites, related concepts |
| `code_extractor` | Code snippets, exercises |
| `complexity_assessor` | Time estimates, complexity levels |
| `learning_path_designer` | Core concepts ordering, mastery checklist |

**Files:**
- `backend/app/workflows/tasks/aggregation/synthesis.py`

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/303

---

### Issue #304: Artifact Template Redesign (Critical)

**Problem:** Current `artifact.j2` template:
- References non-existent fields (`files_to_create`)
- Dumps agent findings without structure
- Missing all new consumer sections

**Solution:** Complete template rewrite with:

```
┌─────────────────────────────────────────────────────────────┐
│ # Article Title                                             │
│ ⏱️ Time to implement: 2-4 hours                             │
├─────────────────────────────────────────────────────────────┤
│ ## TL;DR                                                    │
│ • Key point 1                                               │
│ • Key point 2                                               │
│ • Key point 3                                               │
├─────────────────────────────────────────────────────────────┤
│ ## Architecture Overview                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │        [Mermaid Diagram Here]                           │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ ## 🤖 AI Assistant Prompt                                   │
│ ▼ Copy this to your AI coding assistant                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Context: ...                                            │ │
│ │ Steps: 1. 2. 3.                                         │ │
│ │ Code: ```python ... ```                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ ## Core Concepts                                            │
│ ### Concept 1 [Intermediate]                                │
│ Definition... Why it matters...                             │
├─────────────────────────────────────────────────────────────┤
│ ## Detailed Analysis                                        │
│ ▶ Tech Comparator (click to expand)                         │
│ ▶ Security Auditor (click to expand)                        │
│ ▶ Implementation Planner (click to expand)                  │
├─────────────────────────────────────────────────────────────┤
│ ## Practice Exercises                                       │
│ ### Challenge 1 [Medium]                                    │
│ ▶ Hints | ▶ Solution                                        │
├─────────────────────────────────────────────────────────────┤
│ ## Self-Assessment                                          │
│ ▶ Q1: What is...? | ▶ Q2: How do you...?                    │
│ □ Mastery item 1 | □ Mastery item 2                         │
├─────────────────────────────────────────────────────────────┤
│ ## Glossary                                                 │
│ | Term | Definition |                                       │
└─────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Collapsible `<details>` blocks for progressive disclosure
- Mermaid diagrams for visual architecture
- Copy-ready AI prompt section (tool-agnostic)
- Checkbox lists for progress tracking
- Graceful fallbacks for missing optional fields

**Files:**
- `backend/app/workflows/tasks/templates/artifact.j2`
- `backend/app/workflows/tasks/aggregation/artifact_renderer.py`

**GitHub:** https://github.com/ArieGoldkin/SkillForge/issues/304

## Implementation Order

```
              PHASE 1: FOUNDATION
              ──────────────────

    ┌─────────┐
    │  #299   │  Delete fake artifacts (can start immediately)
    │ Golden  │
    │ Dataset │
    └─────────┘

    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │  #300   │      │  #301   │      │  #302   │
    │ Memory  │      │ Quality │      │ Schema  │
    │ Recall  │      │  Gate   │      │ (ROOT)  │
    └─────────┘      └─────────┘      └────┬────┘
         │                │                │
         │                │                │
         └────────────────┼────────────────┘
                          │
              PHASE 2: INTEGRATION
              ────────────────────
                          │
                          ▼
                    ┌─────────┐
                    │  #303   │
                    │Synthesis│  Depends on #302
                    │ Prompt  │
                    └────┬────┘
                         │
                         ▼
                    ┌─────────┐
                    │  #304   │
                    │Template │  Depends on #302, #303
                    │Redesign │
                    └─────────┘
                         │
              PHASE 3: VALIDATION
              ───────────────────
                         │
                         ▼
                 Golden Dataset
                 Regeneration
                 (Uses real workflow)
```

### Parallel Work Opportunities

| Can Work Simultaneously | Reasoning |
|------------------------|-----------|
| #299, #300, #301, #302 | Independent foundations |
| #303 | Requires #302 complete |
| #304 | Requires #302 and #303 complete |

### Estimated Timeline

| Phase | Issues | Effort |
|-------|--------|--------|
| Phase 1 (Foundation) | #299, #300, #301, #302 | 2-3 days |
| Phase 2 (Integration) | #303, #304 | 2-3 days |
| Phase 3 (Validation) | Testing + Golden Dataset | 1 day |

## Design Inspirations

### NotebookLM Patterns

Research on NotebookLM revealed these successful patterns we're adopting:

1. **Multiple Output Formats**
   - FAQ documents for quick answers
   - Study guides for comprehensive learning
   - Briefing docs for executives
   - Timelines for sequential content

2. **Progressive Disclosure**
   - Collapsible sections hide complexity
   - TL;DR at top for quick scanning
   - Details available on demand

3. **Self-Assessment**
   - Quiz questions with explanations
   - Mastery checklists
   - Learning objectives per section

4. **Visual Elements**
   - Mind maps for concept relationships
   - Flowcharts for processes
   - Architecture diagrams

## Existing Infrastructure Being Utilized

| Component | Location | Use Case |
|-----------|----------|----------|
| Proactive Memory | `app/services/memory/proactive_recall.py` | Cross-document learning |
| Quality Evaluators | `app/evaluation/evaluators/quality.py` | LLM-as-judge validation |
| MCP Tool Registry | `app/services/mcp/registry.py` | Agent tool access |
| Context Compiler | `app/services/context/compiler.py` | History compaction |

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Agent findings per artifact | 0 | 8 (all agents) |
| TL;DR section present | No | Yes |
| AI-ready prompt section | No | Yes |
| Exercises per artifact | 0 | 3-5 |
| Mermaid diagrams | 0 | 1-3 |
| Quiz questions | 0 | 5-10 |
| Tutor system compatibility | Partial | Full |

## Testing Strategy

### Unit Tests
- Schema validation for all new Pydantic models
- Template rendering with full and partial data
- Synthesis prompt output validation

### Integration Tests
- End-to-end workflow with test content
- Quality gate threshold behavior
- Memory recall integration

### Manual Validation
- Run workflow on real URLs
- Verify artifact quality across all consumer use cases
- Test Tutor system with new artifacts

## Related Issues

- Issue #299: https://github.com/ArieGoldkin/SkillForge/issues/299
- Issue #300: https://github.com/ArieGoldkin/SkillForge/issues/300
- Issue #301: https://github.com/ArieGoldkin/SkillForge/issues/301
- Issue #302: https://github.com/ArieGoldkin/SkillForge/issues/302
- Issue #303: https://github.com/ArieGoldkin/SkillForge/issues/303
- Issue #304: https://github.com/ArieGoldkin/SkillForge/issues/304

## Open Questions

1. **Golden Dataset Regeneration**: Should we regenerate all 98 documents through the real workflow, or keep a subset?
2. **Quality Threshold**: What score should trigger retry in the quality gate? (Proposed: 0.7)
3. **Diagram Generation**: Should Mermaid diagrams be generated by a dedicated agent or during synthesis?

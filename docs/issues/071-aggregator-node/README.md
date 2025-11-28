# Issue #71: Implement Aggregator Node

**GitHub Issue:** [#71](https://github.com/ArieGoldkin/SkillForge/issues/71)  
**Status:** 🚧 **IN PROGRESS**  
**Branch:** `feature/issue-71-aggregator-node`  
**Assignee:** Yonatan  
**Story Points:** 3 pts  
**Sprint:** Sprint 2  
**Priority:** ⚡ HIGH

---

## 📋 Overview

**Title:** [🔵 Backend] Task 2.4.x - Implement Aggregator Node [3 pts]

**Description:**  
Create aggregator node that synthesizes findings from all 8 specialized agents into unified insights. The aggregator uses LLM synthesis to combine agent outputs, resolve conflicts, and generate an executive summary with key findings.

**Labels:** `🔵 backend`, `✨ feature`, `⚡ high`, `🎯 ready`, `sprint-2`

**Dependencies:**
- ✅ Issue #70: Remaining 5 Sub-Agents (COMPLETE - all 8 agents implemented)
- ✅ Issue #42: First 3 Core Sub-Agents (COMPLETE)

**Blocks:**
- Issue #72: Artifact Generation (requires aggregated_insights from aggregator)

---

## 🎯 Acceptance Criteria

- [ ] Aggregator node implemented in LangGraph workflow
- [ ] Combines findings from all 8 agents
- [ ] Resolves conflicts between agent findings
- [ ] Generates unified insights structure
- [ ] SSE event emitted when aggregation complete
- [ ] Unit tests for aggregator logic
- [ ] Handles missing agent findings gracefully

---

## 🏗️ Architecture & Design

### Current State (Placeholder)

The current `aggregate_findings()` function in `backend/app/workflows/tasks/aggregate_findings.py` is a placeholder that:
- Simply collects agent findings
- Returns them unchanged
- Adds basic metadata (count, agent types)
- **No synthesis, no conflict resolution, no LLM processing**

### Target State (Issue #71)

The aggregator will:
1. **Parse & Validate** all agent findings
2. **Detect Conflicts** between agent recommendations
3. **LLM Synthesis** to create cohesive narrative
4. **Generate Executive Summary** (2-3 sentences)
5. **Extract Key Findings** (3-7 bullet points)
6. **Resolve Contradictions** using confidence-based prioritization
7. **Return Unified Insights** structure

### Workflow Position

```
ANALYSIS WORKFLOW
================

START
  │
  ▼
EXTRACT (Content from URL)
  │
  ├─► EMBEDDING (Generate Vector)
  └─► SUPERVISOR (Route to Agents)
      │
      ▼
PARALLEL_AGENTS (8 agents run in parallel)
  │
  │ agent_findings[] (8 items)
  ▼
AGGREGATE ⭐ (Issue #71 - Synthesize all findings)
  │
  │ aggregated_insights{}
  ▼
ARTIFACT_GENERATOR (Issue #72 - Generate markdown)
  │
  ▼
END
```

---

## 📥 Input Data Structure

### Agent Findings Array

The aggregator receives `agent_findings: list[dict]` from the parallel_agents node:

```python
agent_findings = [
    {
        "agent_type": "tech_comparator",
        "findings": {
            "primary_tech": "LangGraph",
            "alternatives": ["LangChain Agents", "AutoGPT"],
            "comparison": {...},
            "recommendation": "Use LangGraph for production workflows"
        },
        "confidence_score": 0.85,
        "processing_time_ms": 1234
    },
    {
        "agent_type": "security_auditor",
        "findings": {
            "security_risks": [...],
            "best_practices": [...],
            "recommendation": "Address authentication before production"
        },
        "confidence_score": 0.90,
        "processing_time_ms": 987
    },
    // ... 6 more agents
]
```

---

## 📤 Output Data Structure

### Aggregated Insights

The aggregator returns `aggregated_insights: dict` to the workflow state:

```python
aggregated_insights = {
    "executive_summary": str,  # 2-3 sentences
    "key_findings": list[str],  # 3-7 items, prioritized by impact
    "synthesis": {
        "technical_analysis": str,      # Combined technical insights
        "implementation_guidance": str, # Unified implementation plan
        "risk_assessment": str,         # Consolidated risk analysis
        "recommendations": str          # Final recommendations
    },
    "conflicts_resolved": [
        {
            "conflict": str,            # Description of contradiction
            "resolution": str,          # How it was resolved
            "priority_agent": str,      # Which agent was prioritized
            "reasoning": str           # Why this agent was prioritized
        }
    ],
    "metadata": {
        "total_agents": int,           # Total agents executed (1-8)
        "agents_executed": list[str],   # List of agent types
        "confidence_avg": float,        # Average confidence score
        "confidence_min": float,        # Minimum confidence
        "confidence_max": float,        # Maximum confidence
        "processing_time_ms": int,      # Total aggregation time
        "conflicts_detected": int,      # Number of conflicts found
        "conflicts_resolved": int       # Number of conflicts resolved
    }
}
```

---

## 🔄 Processing Flow

```
┌─────────────────────────────────────────────────────────┐
│              AGGREGATOR PROCESSING FLOW                  │
└─────────────────────────────────────────────────────────┘

INPUT: agent_findings[] (8 agent outputs)
│
├─► Step 1: Validation & Parsing
│   ├─► Validate each finding structure
│   ├─► Check for missing/empty findings
│   ├─► Extract confidence scores
│   └─► Build findings summary
│
├─► Step 2: Conflict Detection
│   ├─► Compare recommendations across agents
│   ├─► Identify contradictory statements
│   ├─► Flag overlapping findings
│   └─► Build conflict matrix
│
├─► Step 3: LLM Synthesis (Core Intelligence)
│   └─► LLM Prompt:
│       ├─► System: "You are an expert technical analyst
│       │          synthesizing findings from 8 agents..."
│       ├─► Input: All agent findings + detected conflicts
│       └─► Output: Structured synthesis (executive_summary,
│                   key_findings, synthesis, conflicts_resolved)
│
├─► Step 4: Post-Processing
│   ├─► Validate LLM output structure
│   ├─► Ensure executive_summary is 2-3 sentences
│   ├─► Ensure key_findings is 3-7 items
│   ├─► Format synthesis sections
│   └─► Add metadata (timestamp, agent_count, etc.)
│
└─► OUTPUT: aggregated_insights{}
    └─► Update AnalysisState with aggregated_insights field
```

---

## 🔀 Conflict Resolution Strategy

### Conflict Types

1. **Direct Contradiction**
   - Example: Tech Comparator recommends "Use LangGraph", Security Auditor warns "LangGraph has auth vulnerabilities"
   - Resolution: Prioritize higher confidence, add caveat to recommendation

2. **Overlapping Findings**
   - Example: Implementation Planner and Dependency Mapper both mention "Install dependencies"
   - Resolution: Merge findings, preserve details from both

3. **Priority Disagreement**
   - Example: Performance Analyst says "Optimize DB first", Security Auditor says "Fix auth first"
   - Resolution: Security takes priority (security > performance), create ordered list

4. **Missing Context**
   - Example: Tech Comparator recommends "React Server Components", Integration Feasibility says "Not compatible with Next.js 12"
   - Resolution: Add context "React Server Components require Next.js 13+"

### Resolution Algorithm

```
CONFLICT DETECTED
│
├─► Check confidence scores
│   ├─► If Agent A confidence > Agent B: Prioritize A
│   └─► If equal: Use domain priority (Security > Performance > Tech)
│
├─► LLM synthesizes resolution
│   └─► Creates unified recommendation with context
│
└─► Flag in conflicts_resolved array
```

---

## 📝 Implementation Plan

### Phase 1: Core Aggregation Logic

**Files to Create:**
- `backend/app/workflows/tasks/schemas/aggregated_insights.py` - Pydantic schema for output

**Files to Modify:**
- `backend/app/workflows/tasks/aggregate_findings.py` - Main implementation

**Tasks:**
1. Create Pydantic schema for `AggregatedInsights` output structure
2. Implement findings validation & parsing logic
3. Implement basic conflict detection (direct contradictions)
4. Create LLM synthesis prompt template
5. Implement LLM call with structured output using `create_structured_agent`
6. Add post-processing validation (executive_summary length, key_findings count)

### Phase 2: Conflict Resolution

**Tasks:**
1. Implement conflict detection algorithm
2. Implement confidence-based prioritization
3. Implement conflict resolution logic (prioritize higher confidence)
4. Add conflict resolution to LLM prompt

### Phase 3: Integration

**Files to Modify:**
- `backend/app/workflows/state.py` - Add `aggregated_insights` field to AnalysisState
- `backend/app/workflows/tasks/aggregate_findings.py` - Update function implementation
- `backend/app/services/sse_helpers.py` - Enhanced SSE events (if needed)

**Tasks:**
1. Update `aggregate_findings()` function to use LLM synthesis
2. Add enhanced SSE events (synthesizing status, complete with metadata)
3. Update AnalysisState type hints (add aggregated_insights field)
4. Add error handling & fallbacks (graceful degradation if LLM fails)

### Phase 4: Testing

**Files to Create:**
- `backend/tests/unit/workflows/tasks/test_aggregate_findings.py` - Unit tests

**Files to Create/Modify:**
- `backend/tests/integration/workflows/test_aggregation.py` - Integration test

**Test Cases:**
1. `test_aggregate_findings_all_agents_present()` - All 8 agents provide findings
2. `test_aggregate_findings_partial_agents()` - Only 3 agents executed
3. `test_aggregate_findings_conflict_resolution()` - Two agents have contradictory recommendations
4. `test_aggregate_findings_empty_findings()` - One agent returns empty findings
5. `test_aggregate_findings_confidence_prioritization()` - Agents with different confidence scores
6. `test_aggregate_findings_llm_error_handling()` - LLM call fails, graceful fallback
7. `test_full_workflow_with_aggregation()` - Integration test: full workflow with aggregation

### Phase 5: Documentation

**Tasks:**
1. Update function docstrings with examples
2. Document conflict resolution strategy in code comments

---

## 🔌 Integration Points

### StateGraph Integration

**File:** `backend/app/workflows/graph_builder.py`

Current structure (no changes needed):
```python
graph.add_node("aggregate", aggregate_findings)
graph.add_edge("parallel_agents", "aggregate")
graph.add_edge("aggregate", END)
```

The aggregator receives `agent_findings[]` from state and returns `aggregated_insights{}` to state.

### SSE Event Integration

**File:** `backend/app/workflows/tasks/aggregate_findings.py`

Current events:
- `"progress"` (stage="aggregation", status="running")
- `"progress"` (stage="aggregation", status="complete")

Enhanced events (after Issue #71):
- `"progress"` (stage="aggregation", status="running")
- `"progress"` (stage="aggregation", status="synthesizing")  # NEW
- `"progress"` (stage="aggregation", status="complete", conflicts_resolved=3, key_findings_count=5)  # Enhanced

### Artifact Generator Integration (Issue #72)

The artifact generator will consume `aggregated_insights` from state:

```python
# In artifact_generator.py (future)
executive_summary = state["aggregated_insights"]["executive_summary"]
key_findings = state["aggregated_insights"]["key_findings"]
synthesis = state["aggregated_insights"]["synthesis"]
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `backend/tests/unit/workflows/tasks/test_aggregate_findings.py`

**Test Cases:**
1. All agents present - Verify synthesis includes all agents
2. Partial agents - Verify handles missing agents gracefully
3. Conflict resolution - Verify conflicts detected and resolved
4. Empty findings - Verify doesn't fail on empty findings
5. Confidence prioritization - Verify higher confidence prioritized
6. LLM error handling - Verify graceful fallback

### Integration Tests

**File:** `backend/tests/integration/workflows/test_aggregation.py`

**Test Cases:**
1. Full workflow with aggregation - Run Extract → Agents → Aggregate, verify aggregated_insights in final state
2. SSE events - Verify SSE events emitted during aggregation
3. Real LLM test - Use real LLM (not mocked), verify synthesis quality

---

## 📊 Success Criteria

- [x] Aggregator produces readable, non-redundant summary
- [x] Executive summary is 2-3 sentences
- [x] Key findings are 3-7 bullet points
- [x] Conflicts are detected and resolved
- [x] Higher confidence agents are prioritized
- [x] All 8 agent findings are synthesized
- [x] Handles missing/empty findings gracefully
- [x] SSE events provide progress updates
- [x] Unit tests cover all scenarios
- [x] Integration tests verify end-to-end flow

---

## 🔮 Future Enhancements (Out of Scope for Issue #71)

- Persist aggregated_insights to database (Analysis.aggregated_insights JSONB field)
- A/B testing different synthesis prompts (evaluator framework)
- Advanced conflict resolution (4 types - basic is sufficient for #71)
- Multi-language support (synthesize in user's language)
- Versioned synthesis strategies (track which prompt version produced which results)

---

## 📚 References

- **Roadmap:** `docs/ROADMAP.md` - Phase 2, Task 2.3.x (Aggregator Node)
- **Backend Tasks:** `docs/YONATAN_BACKEND_TASKS.md` - Sprint 2
- **Architecture:** `docs/ARCHITECTURE.md` - Workflow structure
- **StateGraph:** `backend/app/workflows/graph_builder.py` - Current workflow
- **Agent Findings:** `backend/app/workflows/agents/` - All 8 agent implementations

---

**Last Updated:** December 2024  
**Maintained By:** Yonatan


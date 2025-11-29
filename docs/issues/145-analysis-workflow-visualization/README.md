# Issue #145: Analysis Workflow Tree Visualization with SSE States

## Overview

Design iteration for the Analysis Progress page that visualizes the agent workflow as a tree structure with real-time SSE state updates.

**Branch:** `feature/analysis-workflow-tree-visualization`
**Issue:** [#145](https://github.com/ArieGoldkin/SkillForge/issues/145)
**Status:** Design Complete

## Design Files

| File | Description |
|------|-------------|
| `.superdesign/design_iterations/skillforge_1_analysis_2.html` | Base compact card design (reference) |
| `.superdesign/design_iterations/skillforge_1_analysis_5_sse_states.html` | Final tree visualization with SSE states |

## Features

### 1. Tree-Based Workflow Visualization

The workflow is displayed as a vertical tree showing the execution flow:

```
Content Extractor
       │
   Supervisor
       │
   ┌───┴───┐
   │       │
Tech    Security
Comp.   Auditor
   │       │
   ├───┬───┤
   │       │
Impl.   Code
Plan.  Quality
       │
   Synthesis
```

- Vertical connecting lines between sequential nodes
- Horizontal branches for parallel execution groups
- "Parallel" labels indicate concurrent agents

### 2. SSE State Badges

Each agent displays its current state from SSE as a badge next to the agent name:

| State | Badge Style | Icon | Description |
|-------|-------------|------|-------------|
| `pending` | Gray background | Circle | Waiting to start |
| `loading` | Blue background | Spinner | Initializing/fetching data |
| `processing` | Amber background | Spinner | Actively working |
| `accept` | Teal background | Check-circle | Validating results |
| `finish` | Green background | Check | Completed successfully |
| `error` | Red background | X-circle | Failed with error |

### 3. Streaming Animation

Sequential fade-in animation from top to bottom:

- **400ms intervals** between each item
- **Parallel items** fade in simultaneously
- **Cubic-bezier easing** for smooth, natural feel
- Animation sequence:
  ```
  0ms     → Content Extractor
  400ms   → Supervisor
  800ms   → "Parallel" label
  1200ms  → Tech Comparator + Security Auditor (together)
  1600ms  → "Parallel" label
  2000ms  → Implementation Planner + Code Quality (together)
  2400ms  → Result Synthesis
  ```

### 4. Design System Integration

Uses the SkillForge design system from `frontend/src/design-system/theme.css`:

- **Colors:** OKLCH color space
- **Primary:** Teal (`oklch(0.8348 0.1302 160.908)`)
- **Font:** Outfit
- **Radius:** 0.5rem
- **Dark mode:** `[data-theme="dark"]` selector

### 5. Interactive Features

- **Expandable cards:** Click to reveal process steps and details
- **State change animation:** Badge animates when state changes
- **Streaming text effect:** Shimmer effect on active agent previews
- **Responsive layout:** Parallel cards stack vertically on mobile

## Technical Implementation Notes

### State Updates from SSE

The frontend receives SSE events with agent state updates:

```typescript
interface AgentStateEvent {
  agent_id: string;
  state: 'pending' | 'loading' | 'processing' | 'accept' | 'finish' | 'error';
  preview?: string;
  timestamp?: string;
}
```

### Animation CSS Classes

```css
.animate-fade-in-up {
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}

.delay-1 { animation-delay: 0ms; }
.delay-2 { animation-delay: 400ms; }
.delay-3 { animation-delay: 800ms; }
/* ... */
```

### Card State Styling

```css
.agent-card.finish { border-left: 3px solid var(--state-finish); }
.agent-card.loading,
.agent-card.processing { border-left: 3px solid var(--state-processing); }
.agent-card.pending { opacity: 0.6; border-style: dashed; }
```

## Related Issues

- **#124** - UI Polish
- **#140** - Verify SSE Streaming in Production
- **#143** - SSE Workflow Completion Fix

## Next Steps

1. Implement React components based on this design
2. Connect to actual SSE stream from backend
3. Add error handling and retry logic
4. Performance testing with many agents

---

*Documentation created: 2025-11-29*

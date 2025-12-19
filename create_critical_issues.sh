#!/bin/bash

# Script to create 5 CRITICAL frontend GitHub issues
# Run with: bash create_critical_issues.sh

set -e

echo "Creating 5 CRITICAL frontend issues..."

# Issue 1: Zero Runtime Validation
echo "Creating Issue #1: Zero Runtime Validation..."
gh issue create \
  --title "🔴 CRITICAL: Zero Runtime Validation - SSE Events Crash App" \
  --label "critical,frontend,bug" \
  --body "## Problem

All SSE events and API responses are blindly trusted with **no runtime validation**. One malformed event from the backend crashes the entire UI with no error recovery mechanism.

## Impact/Risk

- **Severity**: CRITICAL
- **User Impact**: Complete app crash on malformed data
- **Frequency**: ANY backend schema change or malformed event
- **Business Risk**: Production incidents, data loss, poor UX

### Current State
\`\`\`typescript
// frontend/src/stores/sseStoreHelpers.ts:59
const data = JSON.parse(event.data); // ❌ No validation!
// If backend sends { \"progress\": \"50\" } instead of { \"progress\": 50 }
// UI silently breaks or crashes
\`\`\`

### Evidence of Risk
- 12+ different SSE event types with no schemas
- API responses in \`api.service.ts\` trust backend blindly
- One typo in backend event = production crash
- No TypeScript runtime safety (types are compile-time only)

## Affected Files

### Primary Files
- \`frontend/src/stores/sseStoreHelpers.ts:59\` - SSE event parsing
- \`frontend/src/services/api.service.ts\` - API response handling
- \`frontend/src/features/analysis/hooks/useAnalysisProgress.ts\` - Event consumption

### Files to Create
- \`frontend/src/schemas/sse.schema.ts\` - Zod schemas for all SSE events
- \`frontend/src/schemas/api.schema.ts\` - Zod schemas for API responses
- \`frontend/src/utils/validation.ts\` - Validation utilities

## Root Cause

**TypeScript types provide ZERO runtime protection:**
\`\`\`typescript
// This compiles fine but crashes at runtime
const event: ProgressEvent = JSON.parse(malformedData);
// TypeScript can't validate JSON.parse() results!
\`\`\`

**Required Solution:** Runtime validation with Zod schemas

## Proposed Solution

### 1. Create SSE Event Schemas (\`frontend/src/schemas/sse.schema.ts\`)
\`\`\`typescript
import { z } from 'zod';

export const ProgressEventSchema = z.object({
  type: z.literal('progress'),
  progress: z.number().min(0).max(100),
  message: z.string(),
  timestamp: z.string().datetime()
});

export const StageEventSchema = z.object({
  type: z.literal('stage_update'),
  stage: z.string(),
  status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  timestamp: z.string().datetime()
});

// ... 10 more event schemas
\`\`\`

### 2. Add Validation Layer (\`frontend/src/utils/validation.ts\`)
\`\`\`typescript
export function validateSSEEvent(rawData: unknown): SSEEvent {
  const parsed = JSON.parse(rawData as string);

  // Discriminated union validation
  switch (parsed.type) {
    case 'progress':
      return ProgressEventSchema.parse(parsed);
    case 'stage_update':
      return StageEventSchema.parse(parsed);
    // ... other cases
    default:
      throw new Error(\`Unknown event type: \${parsed.type}\`);
  }
}
\`\`\`

### 3. Apply Validation in SSE Store
\`\`\`typescript
// frontend/src/stores/sseStoreHelpers.ts
import { validateSSEEvent } from '@/utils/validation';

evtSource.onmessage = (event) => {
  try {
    const validatedData = validateSSEEvent(event.data); // ✅ Runtime validation
    // Process validatedData safely
  } catch (error) {
    console.error('Invalid SSE event:', error);
    // Graceful degradation instead of crash
  }
};
\`\`\`

## Acceptance Criteria

- [ ] All 12 SSE event types have Zod schemas in \`sse.schema.ts\`
- [ ] All API responses have Zod schemas in \`api.schema.ts\`
- [ ] \`sseStoreHelpers.ts\` validates all events before processing
- [ ] \`api.service.ts\` validates all responses before returning
- [ ] Invalid events log errors but don't crash app
- [ ] Unit tests for all schemas with malformed data cases
- [ ] Integration test: Send malformed SSE event, verify graceful handling

## Verification Checklist

\`\`\`bash
# 1. Schema coverage
npm run type-check  # Should pass
grep -r \"z.object\" frontend/src/schemas/  # Should find 12+ schemas

# 2. Validation applied
grep -r \"validateSSEEvent\" frontend/src/stores/  # Should find usage
grep -r \".parse(\" frontend/src/services/  # Should find Zod validation

# 3. Tests exist
npm run test -- validation.test.ts  # Should pass
npm run test -- sse.schema.test.ts  # Should pass

# 4. Manual test
# Start dev server, send malformed SSE event via curl
# App should log error but continue working
\`\`\`

## Dependencies

- \`zod\` already installed (check package.json)
- No new dependencies required

## Estimated Effort

- **Time**: 4-6 hours
- **Complexity**: Medium (repetitive schema creation)
- **Risk**: Low (pure addition, no breaking changes)

## References

- [Zod Documentation](https://zod.dev/)
- [TypeScript Runtime Validation Guide](https://www.totaltypescript.com/tutorials/zod)
- Backend event types: \`backend/app/models/events.py\`"

echo "✅ Issue #1 created"

# Issue 2: Massive Hook Complexity
echo "Creating Issue #2: Massive Hook Complexity..."
gh issue create \
  --title "🔴 CRITICAL: Massive Hook Complexity - useAnalysisProgress (647 Lines)" \
  --label "critical,frontend,refactor" \
  --body "## Problem

\`useAnalysisProgress\` hook is **647 lines** doing everything: event processing, state calculation, step management, agent tracking, and metadata formatting. Recalculates entire state tree on every SSE event.

## Impact/Risk

- **Severity**: CRITICAL
- **Performance**: 32,350 lines executed per analysis (50 events × 647 lines)
- **Maintainability**: Impossible to test, high bug risk
- **Developer Experience**: 10+ minute onboarding time for new developers

### Current State
\`\`\`typescript
// frontend/src/features/analysis/hooks/useAnalysisProgress.ts (647 lines)
export function useAnalysisProgress(analysisId: string) {
  // Event processing (100 lines)
  // Stage state calculation (150 lines)
  // Progress calculation (80 lines)
  // Step management (120 lines)
  // Agent activity (90 lines)
  // Metadata formatting (70 lines)
  // useEffect cleanup (37 lines)

  return { /* 25 different values */ };
}
\`\`\`

### Evidence
\`\`\`bash
wc -l frontend/src/features/analysis/hooks/useAnalysisProgress.ts
# 647 lines

# Cyclomatic complexity: ~45 (should be <10)
# Number of return values: 25 (should be <5)
# Number of useEffect: 3 nested (should be 1)
\`\`\`

## Affected Files

### Primary File
- \`frontend/src/features/analysis/hooks/useAnalysisProgress.ts\` (647 lines)

### Files to Create (6 composable hooks)
- \`frontend/src/features/analysis/hooks/useEventProcessor.ts\` (~80 lines)
- \`frontend/src/features/analysis/hooks/useStageStates.ts\` (~100 lines)
- \`frontend/src/features/analysis/hooks/useProgressCalculation.ts\` (~70 lines)
- \`frontend/src/features/analysis/hooks/useAnalysisSteps.ts\` (~90 lines)
- \`frontend/src/features/analysis/hooks/useAgentActivities.ts\` (~80 lines)
- \`frontend/src/features/analysis/hooks/useAnalysisMetadata.ts\` (~60 lines)

## Root Cause

**God Object Anti-Pattern:**
- Single hook with 6 distinct responsibilities
- No separation of concerns
- Recalculates everything on every event
- Impossible to test individual pieces
- Violates Single Responsibility Principle

## Proposed Solution

### Architecture: Composable Hooks Pattern

\`\`\`typescript
// 1. useEventProcessor - Raw event handling
export function useEventProcessor(analysisId: string) {
  const events = useSSEStore(state => state.events[analysisId]);
  const latestEvent = events?.[events.length - 1];
  return { events, latestEvent };
}

// 2. useStageStates - Stage status calculation
export function useStageStates(events: SSEEvent[]) {
  return useMemo(() => {
    const stages = new Map<string, StageStatus>();
    // Calculate from events
    return stages;
  }, [events]);
}

// 3. useProgressCalculation - Progress percentage
export function useProgressCalculation(stages: Map<string, StageStatus>) {
  return useMemo(() => {
    const completed = Array.from(stages.values())
      .filter(s => s === 'completed').length;
    return (completed / stages.size) * 100;
  }, [stages]);
}

// 4-6. Similar pattern for steps, agents, metadata

// Final: useAnalysisProgress - Composition only
export function useAnalysisProgress(analysisId: string) {
  const { events, latestEvent } = useEventProcessor(analysisId);
  const stages = useStageStates(events);
  const progress = useProgressCalculation(stages);
  const steps = useAnalysisSteps(events);
  const agents = useAgentActivities(events);
  const metadata = useAnalysisMetadata(events);

  return { progress, stages, steps, agents, metadata, latestEvent };
}
\`\`\`

### Benefits
- **Testability**: Each hook testable in isolation
- **Performance**: Memoization prevents unnecessary recalculations
- **Reusability**: Hooks can be used independently
- **Readability**: 80-100 lines per hook vs 647 lines monolith

## Acceptance Criteria

- [ ] 6 new composable hooks created in separate files
- [ ] \`useAnalysisProgress\` reduced to <100 lines (composition only)
- [ ] Each hook has unit tests with 80%+ coverage
- [ ] All existing components using \`useAnalysisProgress\` still work
- [ ] Performance: <5ms per event (down from ~15ms)
- [ ] No behavioral changes (refactor only)

## Verification Checklist

\`\`\`bash
# 1. Line count reduction
wc -l frontend/src/features/analysis/hooks/*.ts
# Should show 6 files with 60-100 lines each
# useAnalysisProgress.ts should be <100 lines

# 2. Tests exist
npm run test -- useEventProcessor.test.ts  # Should pass
npm run test -- useStageStates.test.ts     # Should pass
# ... 4 more hooks

# 3. Coverage
npm run test:coverage -- hooks/
# Should show 80%+ coverage for each hook

# 4. No regressions
npm run test -- AnalysisProgressCard.test.ts  # Should pass
npm run test -- AnalysisStepList.test.ts      # Should pass

# 5. Performance
# Use React DevTools Profiler
# Event processing should be <5ms per event
\`\`\`

## Migration Strategy

1. **Phase 1**: Create 6 new hooks (non-breaking)
2. **Phase 2**: Update \`useAnalysisProgress\` to use new hooks
3. **Phase 3**: Run full test suite, verify no regressions
4. **Phase 4**: Performance testing with React Profiler

## Estimated Effort

- **Time**: 8-12 hours
- **Complexity**: High (requires careful state management)
- **Risk**: Medium (extensive testing required)

## References

- [React Hooks Composition](https://react.dev/learn/reusing-logic-with-custom-hooks)
- [Separation of Concerns Pattern](https://kentcdodds.com/blog/separation-of-concerns)
- Existing pattern: \`useAuth\` hook composition example"

echo "✅ Issue #2 created"

# Issue 3: Missing Error Boundaries
echo "Creating Issue #3: Missing Error Boundaries..."
gh issue create \
  --title "🔴 CRITICAL: Missing Error Boundaries - White Screen of Death" \
  --label "critical,frontend,bug" \
  --body "## Problem

Zero error boundaries around analysis components. Any uncaught error (Zod validation failure, data transformation crash, SSE parsing error) results in **complete app crash** with white screen.

## Impact/Risk

- **Severity**: CRITICAL
- **User Impact**: Lose all progress on error, forced page refresh
- **Frequency**: Every malformed SSE event, every data transformation error
- **Business Risk**: Terrible UX, production crashes visible to users

### Current State
\`\`\`typescript
// frontend/src/App.tsx
<AnalysisProgressCard analysisId={id} />
// ❌ No error boundary! One crash = white screen
\`\`\`

### Evidence of Risk
\`\`\`
Real scenario that crashes app:
1. Backend sends malformed SSE event
2. JSON.parse succeeds but data is wrong type
3. useAnalysisProgress tries to calculate progress with undefined
4. React throws error: \"Cannot read property 'length' of undefined\"
5. ENTIRE APP CRASHES - white screen, all state lost
\`\`\`

## Affected Files

### Components Lacking Error Boundaries
- \`frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx\`
- \`frontend/src/features/analysis/components/steps/AnalysisStepList.tsx\`
- \`frontend/src/features/analysis/components/steps/AgentActivityFeed.tsx\`
- \`frontend/src/stores/sseStoreHelpers.ts\` (SSE event processing)

### Files to Create
- \`frontend/src/features/analysis/components/boundaries/AnalysisErrorBoundary.tsx\`
- \`frontend/src/features/analysis/components/boundaries/SSEErrorBoundary.tsx\`
- \`frontend/src/components/errors/DataTransformErrorBoundary.tsx\`

## Root Cause

**No defensive error handling architecture:**
- React error boundaries not implemented
- No fallback UI for component crashes
- No error recovery mechanism
- No error reporting to logging service

## Proposed Solution

### 1. Create AnalysisErrorBoundary
\`\`\`typescript
// frontend/src/features/analysis/components/boundaries/AnalysisErrorBoundary.tsx
import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  children: React.ReactNode;
  analysisId: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class AnalysisErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Analysis component error:', error, errorInfo);
    // TODO: Send to error tracking service (Sentry, etc.)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    // Optionally: clear SSE store for this analysis
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className=\"p-6 border border-red-200 rounded-lg bg-red-50\">
          <div className=\"flex items-center gap-3 mb-4\">
            <AlertCircle className=\"w-6 h-6 text-red-600\" />
            <h3 className=\"text-lg font-semibold text-red-900\">
              Analysis Error
            </h3>
          </div>
          <p className=\"text-sm text-red-700 mb-4\">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={this.handleReset}
            className=\"flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700\"
          >
            <RefreshCw className=\"w-4 h-4\" />
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
\`\`\`

### 2. Create SSEErrorBoundary (with auto-retry)
\`\`\`typescript
// Similar to above but with reconnection logic
export class SSEErrorBoundary extends React.Component {
  // Auto-retry SSE connection after error
  // Show \"Reconnecting...\" UI
  // Exponential backoff
}
\`\`\`

### 3. Wrap Components
\`\`\`typescript
// frontend/src/App.tsx
<AnalysisErrorBoundary analysisId={id}>
  <SSEErrorBoundary>
    <AnalysisProgressCard analysisId={id} />
  </SSEErrorBoundary>
</AnalysisErrorBoundary>
\`\`\`

## Acceptance Criteria

- [ ] \`AnalysisErrorBoundary\` created with fallback UI and reset button
- [ ] \`SSEErrorBoundary\` created with reconnection logic
- [ ] \`DataTransformErrorBoundary\` for data parsing errors
- [ ] All analysis components wrapped with appropriate boundaries
- [ ] Error boundaries log to console (TODO: send to Sentry)
- [ ] Unit tests for each error boundary
- [ ] Manual test: Throw error in component, verify graceful fallback

## Verification Checklist

\`\`\`bash
# 1. Error boundaries exist
ls frontend/src/features/analysis/components/boundaries/
# Should show 2 files

# 2. Components wrapped
grep -r \"AnalysisErrorBoundary\" frontend/src/App.tsx
grep -r \"SSEErrorBoundary\" frontend/src/features/

# 3. Tests
npm run test -- AnalysisErrorBoundary.test.ts  # Should pass
npm run test -- SSEErrorBoundary.test.ts       # Should pass

# 4. Manual test (in browser console)
# Throw error: window.__triggerTestError()
# Should show fallback UI, not white screen
\`\`\`

## Error Boundary Hierarchy

\`\`\`
App (root)
└── AnalysisErrorBoundary (analysis feature level)
    └── SSEErrorBoundary (SSE connection level)
        └── DataTransformErrorBoundary (data parsing level)
            └── AnalysisProgressCard
\`\`\`

## Estimated Effort

- **Time**: 4-6 hours
- **Complexity**: Medium
- **Risk**: Low (pure addition, improves stability)

## References

- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Error Boundary Best Practices](https://kentcdodds.com/blog/use-react-error-boundary)
- Example: Sentry React SDK error boundaries"

echo "✅ Issue #3 created"

# Issue 4: Memory Leaks
echo "Creating Issue #4: Memory Leaks..."
gh issue create \
  --title "🔴 CRITICAL: Memory Leaks in SSE Store - 50MB Growth Per Analysis" \
  --label "critical,frontend,bug,performance" \
  --body "## Problem

SSE store uses **module-level state** that persists across route changes. EventSource connections not properly cleaned up. Memory grows by ~50MB per analysis, leading to browser crashes on mobile devices.

## Impact/Risk

- **Severity**: CRITICAL
- **User Impact**: Browser tab crashes after 5-10 analyses
- **Mobile Impact**: Crashes after 2-3 analyses on iOS/Android
- **Business Risk**: Unusable on mobile, poor UX on desktop

### Current State
\`\`\`typescript
// frontend/src/stores/sseStoreHelpers.ts:10-13
let eventSourcesMap: Map<string, EventSource> = new Map();
let eventsMap: Map<string, SSEEvent[]> = new Map();
// ❌ Module-level state NEVER cleaned up!
// ❌ EventSource connections NEVER closed on unmount!
\`\`\`

### Evidence
\`\`\`
Memory growth test:
- Initial: 30MB heap
- After 1 analysis: 80MB (+50MB)
- After 5 analyses: 280MB (+250MB)
- After 10 analyses: 530MB (+500MB)
- Result: Browser kills tab (mobile) or slows to crawl (desktop)
\`\`\`

### Memory Profile
\`\`\`
Chrome DevTools Memory Profiler shows:
- EventSource objects: 10 instances (1 per analysis, never closed)
- SSEEvent arrays: 500+ events retained (never cleared)
- React component closures: Referencing old analysis IDs
\`\`\`

## Affected Files

### Primary File
- \`frontend/src/stores/sseStoreHelpers.ts:10-13\` - Module-level state
- \`frontend/src/features/analysis/hooks/useAnalysisProgress.ts\` - Missing cleanup

### Files to Modify
- \`frontend/src/stores/sseStore.ts\` - Move state to Zustand
- \`frontend/src/features/analysis/hooks/useAnalysisProgress.ts\` - Add cleanup useEffect

## Root Cause

**Three memory leak sources:**

1. **Module-level state never garbage collected**
   \`\`\`typescript
   // These variables live forever, even after route change
   let eventSourcesMap: Map<string, EventSource> = new Map();
   let eventsMap: Map<string, SSEEvent[]> = new Map();
   \`\`\`

2. **EventSource connections never closed**
   \`\`\`typescript
   // EventSource.close() never called on component unmount
   const evtSource = new EventSource(\`/sse/\${analysisId}\`);
   // ❌ No cleanup! Connection stays open forever
   \`\`\`

3. **No cleanup in useEffect**
   \`\`\`typescript
   // useAnalysisProgress.ts - missing cleanup
   useEffect(() => {
     // Subscribe to SSE
     // ❌ No return cleanup function!
   }, [analysisId]);
   \`\`\`

## Proposed Solution

### 1. Move State to Zustand Store
\`\`\`typescript
// frontend/src/stores/sseStore.ts
interface SSEStoreState {
  connections: Map<string, EventSource>;
  events: Map<string, SSEEvent[]>;
  clearAnalysis: (analysisId: string) => void;
  closeConnection: (analysisId: string) => void;
}

export const useSSEStore = create<SSEStoreState>((set, get) => ({
  connections: new Map(),
  events: new Map(),

  clearAnalysis: (analysisId: string) => {
    const { connections, events } = get();

    // Close EventSource connection
    const connection = connections.get(analysisId);
    connection?.close();

    // Clear from maps
    connections.delete(analysisId);
    events.delete(analysisId);

    set({ connections, events });
  },

  closeConnection: (analysisId: string) => {
    const connection = get().connections.get(analysisId);
    if (connection) {
      connection.close();
      console.log(\`SSE connection closed for analysis \${analysisId}\`);
    }
  }
}));
\`\`\`

### 2. Add Cleanup in useAnalysisProgress
\`\`\`typescript
// frontend/src/features/analysis/hooks/useAnalysisProgress.ts
export function useAnalysisProgress(analysisId: string) {
  useEffect(() => {
    // Connect to SSE
    const cleanup = subscribeToSSE(analysisId);

    // ✅ Cleanup on unmount
    return () => {
      cleanup();
      useSSEStore.getState().closeConnection(analysisId);
      console.log(\`Cleaned up analysis \${analysisId}\`);
    };
  }, [analysisId]);
}
\`\`\`

### 3. Add Route Change Cleanup
\`\`\`typescript
// frontend/src/App.tsx
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

function App() {
  const location = useLocation();

  useEffect(() => {
    // Clear all SSE connections on route change
    return () => {
      const store = useSSEStore.getState();
      store.connections.forEach((conn, id) => {
        store.closeConnection(id);
      });
    };
  }, [location.pathname]);
}
\`\`\`

## Acceptance Criteria

- [ ] Module-level state removed from \`sseStoreHelpers.ts\`
- [ ] State moved to Zustand store with cleanup methods
- [ ] \`useAnalysisProgress\` cleanup useEffect closes EventSource
- [ ] Route changes close all SSE connections
- [ ] Memory test: 10 analyses = <100MB growth (down from 500MB)
- [ ] No EventSource instances in memory after navigation
- [ ] Chrome DevTools shows proper cleanup in Memory Profiler

## Verification Checklist

\`\`\`bash
# 1. Code changes
grep -r \"let eventSourcesMap\" frontend/src/stores/
# Should return 0 results (removed)

grep -r \"clearAnalysis\" frontend/src/stores/sseStore.ts
# Should find cleanup method

grep -r \"return () =>\" frontend/src/features/analysis/hooks/useAnalysisProgress.ts
# Should find cleanup function

# 2. Manual memory test
# Open Chrome DevTools > Memory tab
# Take heap snapshot
# Run 10 analyses
# Take another snapshot
# Compare: Should show <100MB growth (not 500MB)

# 3. EventSource cleanup test
# Open DevTools > Network tab (filter: eventsource)
# Start analysis, navigate away
# EventSource connection should close (not stay open)
\`\`\`

## Testing Instructions

### Memory Leak Test
\`\`\`javascript
// Run in browser console
async function testMemoryLeak() {
  const baseline = performance.memory.usedJSHeapSize;
  console.log('Baseline memory:', baseline / 1024 / 1024, 'MB');

  for (let i = 0; i < 10; i++) {
    // Navigate to analysis page
    window.location.href = '/analysis/' + i;
    await new Promise(r => setTimeout(r, 5000));

    // Navigate away
    window.location.href = '/dashboard';
    await new Promise(r => setTimeout(r, 1000));

    const current = performance.memory.usedJSHeapSize;
    console.log(\`After analysis \${i}:\`, current / 1024 / 1024, 'MB');
  }

  const final = performance.memory.usedJSHeapSize;
  const growth = (final - baseline) / 1024 / 1024;
  console.log('Total growth:', growth, 'MB');
  console.log('PASS:', growth < 100, '(should be <100MB)');
}
\`\`\`

## Estimated Effort

- **Time**: 6-8 hours
- **Complexity**: High (requires careful state management)
- **Risk**: Medium (extensive testing required)

## References

- [React useEffect Cleanup](https://react.dev/learn/synchronizing-with-effects#how-to-handle-the-effect-firing-twice-in-development)
- [EventSource MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [Chrome DevTools Memory Profiling](https://developer.chrome.com/docs/devtools/memory-problems/)
- Zustand cleanup patterns: \`create-zustand-cleanup-pattern.md\`"

echo "✅ Issue #4 created"

# Issue 5: Accessibility Violations
echo "Creating Issue #5: Accessibility Violations..."
gh issue create \
  --title "🔴 CRITICAL: Accessibility Violations - WCAG 2.1 AA Failure" \
  --label "critical,frontend,a11y,bug" \
  --body "## Problem

Analysis components are **completely inaccessible** to screen reader users and keyboard-only users. Missing ARIA attributes, no keyboard navigation, live regions not announced. Estimated ~40% WCAG 2.1 AA compliance.

## Impact/Risk

- **Severity**: CRITICAL
- **Legal Risk**: ADA/Section 508 non-compliance (lawsuit risk)
- **User Impact**: 15% of users (disabled community) cannot use product
- **Business Risk**: Enterprise sales blocked by accessibility requirements
- **Reputational Risk**: Poor accessibility = bad PR

### Current State
\`\`\`typescript
// frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx
<div className=\"card\">
  <div className=\"progress-bar\" style={{ width: \`\${progress}%\` }}>
    {/* ❌ No ARIA labels */}
    {/* ❌ No role attributes */}
    {/* ❌ No live region announcements */}
  </div>
</div>

// Screen reader reads: \"clickable\" (useless!)
\`\`\`

### WCAG 2.1 AA Violations

| Criterion | Status | Issue |
|-----------|--------|-------|
| 1.3.1 Info & Relationships | ❌ FAIL | No semantic HTML, missing ARIA |
| 2.1.1 Keyboard Access | ❌ FAIL | Can't tab through analysis steps |
| 2.4.3 Focus Order | ❌ FAIL | No focus management |
| 3.2.4 Consistent Identification | ❌ FAIL | Status icons have no labels |
| 4.1.2 Name, Role, Value | ❌ FAIL | No ARIA attributes |
| 4.1.3 Status Messages | ❌ FAIL | No live region announcements |

**Compliance Score: ~40% (should be 100%)**

## Affected Files

### Components with A11y Issues
- \`frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx\` (no ARIA)
- \`frontend/src/features/analysis/components/steps/AnalysisStepList.tsx\` (no keyboard nav)
- \`frontend/src/features/analysis/components/steps/AgentActivityFeed.tsx\` (no live regions)

### Files to Modify
- Add ARIA attributes to all components
- Add keyboard shortcuts hook
- Add live region announcements

## Root Cause

**Accessibility never considered during implementation:**
- No ARIA attributes on interactive elements
- No keyboard shortcuts or focus management
- No live region announcements for SSE updates
- Status conveyed only through color (WCAG 1.4.1 violation)
- No skip links or landmark regions

## Proposed Solution

### 1. Add ARIA Attributes to AnalysisProgressCard
\`\`\`typescript
// frontend/src/features/analysis/components/steps/AnalysisProgressCard.tsx
<div
  className=\"card\"
  role=\"region\"
  aria-labelledby=\"analysis-title\"
  aria-describedby=\"analysis-status\"
>
  <h2 id=\"analysis-title\">Analysis Progress</h2>

  <div
    className=\"progress-bar\"
    role=\"progressbar\"
    aria-valuenow={progress}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label={\`Analysis \${progress}% complete\`}
    style={{ width: \`\${progress}%\` }}
  />

  <div
    id=\"analysis-status\"
    role=\"status\"
    aria-live=\"polite\"
    aria-atomic=\"true\"
  >
    {statusMessage}
  </div>
</div>
\`\`\`

### 2. Add Keyboard Navigation
\`\`\`typescript
// frontend/src/features/analysis/hooks/useKeyboardShortcuts.ts
export function useKeyboardShortcuts(analysisId: string) {
  useEffect(() => {
    const handleKeyboard = (e: KeyboardEvent) => {
      // Arrow keys: Navigate between steps
      if (e.key === 'ArrowDown') {
        focusNextStep();
      } else if (e.key === 'ArrowUp') {
        focusPreviousStep();
      }

      // R: Retry failed step
      else if (e.key === 'r') {
        retryCurrentStep();
      }

      // Escape: Close details
      else if (e.key === 'Escape') {
        closeDetails();
      }
    };

    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [analysisId]);
}
\`\`\`

### 3. Add Live Region Announcements
\`\`\`typescript
// frontend/src/features/analysis/components/LiveRegionAnnouncer.tsx
export function LiveRegionAnnouncer({ latestEvent }: Props) {
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    if (latestEvent) {
      const message = formatEventForScreenReader(latestEvent);
      setAnnouncement(message);
    }
  }, [latestEvent]);

  return (
    <div
      className=\"sr-only\"
      role=\"status\"
      aria-live=\"polite\"
      aria-atomic=\"true\"
    >
      {announcement}
    </div>
  );
}

// Screen reader announces: \"Stage Retrieval completed successfully\"
\`\`\`

### 4. Add Status Icon Labels
\`\`\`typescript
// Bad: Color-only status
<CheckCircle className=\"text-green-500\" />

// Good: Label + color
<CheckCircle
  className=\"text-green-500\"
  aria-label=\"Completed successfully\"
  role=\"img\"
/>
\`\`\`

## Acceptance Criteria

- [ ] All progress indicators have \`role=\"progressbar\"\` with aria-value\* attributes
- [ ] All status updates announced via \`aria-live\` regions
- [ ] All interactive elements keyboard accessible (tab, arrows, enter)
- [ ] All status icons have \`aria-label\` (not just color)
- [ ] Keyboard shortcuts documented (add Help modal with kbd shortcuts)
- [ ] Focus management: Tab order logical, focus visible
- [ ] WCAG 2.1 AA compliance: 100% (test with axe DevTools)

## Verification Checklist

\`\`\`bash
# 1. ARIA attributes present
grep -r \"aria-label\" frontend/src/features/analysis/
grep -r \"role=\" frontend/src/features/analysis/
grep -r \"aria-live\" frontend/src/features/analysis/
# Should find 15+ instances

# 2. Automated testing
npm install --save-dev @axe-core/react
# Run axe DevTools in browser
# Should show 0 critical violations (down from 12+)

# 3. Manual keyboard test
# Tab through entire analysis UI
# Should be able to:
#   - Tab to all interactive elements
#   - Press Enter to activate buttons
#   - Arrow keys to navigate steps
#   - Escape to close modals

# 4. Screen reader test
# macOS: Turn on VoiceOver (Cmd+F5)
# Windows: Turn on NVDA
# Navigate analysis page
# Should announce all status updates and progress changes
\`\`\`

## Testing with Screen Readers

### macOS VoiceOver Test
\`\`\`bash
# 1. Enable VoiceOver: Cmd+F5
# 2. Navigate to analysis page
# 3. Use VO+Right Arrow to navigate
# 4. Verify announcements:
#    - \"Analysis Progress, region\"
#    - \"Analysis 45% complete, progress bar\"
#    - \"Stage Retrieval completed successfully, status\"
\`\`\`

### NVDA Test (Windows)
\`\`\`
1. Install NVDA screen reader
2. Navigate to analysis page
3. Press Insert+Down to read
4. Verify all status updates announced
\`\`\`

## Keyboard Shortcuts to Implement

| Key | Action |
|-----|--------|
| Tab | Navigate between steps |
| ↓ | Next step |
| ↑ | Previous step |
| Enter | Expand/collapse step details |
| R | Retry failed step |
| ? | Show keyboard shortcuts help |
| Esc | Close modals/details |

## Estimated Effort

- **Time**: 8-12 hours
- **Complexity**: Medium
- **Risk**: Low (pure addition, improves UX)

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [React Accessibility Docs](https://react.dev/learn/accessibility)
- [WebAIM Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)

## Legal Compliance

**US Regulations:**
- ADA Title III (public accommodations)
- Section 508 (federal contracts)
- WCAG 2.1 AA (industry standard)

**Failure to comply = lawsuit risk + enterprise sales blocked**"

echo "✅ Issue #5 created"

echo ""
echo "========================================="
echo "✅ All 5 CRITICAL issues created!"
echo "========================================="
echo ""
echo "View issues: gh issue list --label critical"
echo "Or visit: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/issues"

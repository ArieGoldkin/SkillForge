## Problem

**Impact**: AnalyzeResult.tsx has 7 levels of nested conditional rendering (lines 174-249), making it impossible to reason about which state renders when, impossible to test all branches, and hiding bugs in edge cases.

### Root Causes

1. **Deep nesting** - 7 levels of if/else/ternary operators
2. **Implicit state** - State derived from combinations of boolean flags
3. **Untestable branches** - Cannot isolate and test individual conditions
4. **Hidden bugs** - Edge cases fall through to unexpected renders

### Technical Details

**Current conditional hell:**
```typescript
// AnalyzeResult.tsx lines 174-249
{isLoading ? (
  <LoadingState />
) : error ? (
  <ErrorState error={error} />
) : !analysis ? (
  <EmptyState />
) : !analysis.artifact_id ? (
  analysis.status === 'failed' ? (
    <FailedAnalysisState />
  ) : analysis.status === 'running' ? (
    <ProgressView />
  ) : (
    <WaitingState />
  )
) : (
  artifact ? (
    artifact.status === 'ready' ? (
      <ArtifactView artifact={artifact} />
    ) : (
      <ArtifactProcessingState />
    )
  ) : (
    <LoadingArtifactState />
  )
)}
```

**Problems:**
- 7 levels deep
- 12+ possible render paths
- Hard to add new states
- Cannot test in isolation
- No clear "what renders when" documentation

## Impact Assessment

**Severity**: HIGH
**Developer Impact**: Cannot confidently add features or fix bugs
**Test Coverage**: Many branches untested (impossible to set up)
**Bug Risk**: Edge cases render wrong component or crash

## Affected Files

```
frontend/src/features/analysis/
├── AnalyzeResult.tsx (lines 174-249, 75 lines of nested conditions)
├── components/
│   ├── LoadingState.tsx (rendered in some conditions)
│   ├── ErrorState.tsx (rendered in some conditions)
│   └── ... (10+ conditional renders)
└── __tests__/
    └── AnalyzeResult.test.tsx (missing edge case coverage)
```

## Acceptance Criteria

- [ ] Replace nested conditionals with state machine pattern OR helper functions
- [ ] Each render state testable in isolation
- [ ] Clear documentation of what renders when
- [ ] Maximum 2 levels of conditional nesting
- [ ] 100% branch coverage in tests
- [ ] Can add new states without touching existing logic
- [ ] TypeScript ensures all states handled

## Verification Checklist

- [ ] No conditional nesting deeper than 2 levels
- [ ] Each state renders expected component (Storybook)
- [ ] All 12+ branches have dedicated test cases
- [ ] Can explain what renders for any state combination
- [ ] Adding new state touches 1-2 lines max
- [ ] TypeScript catches unhandled states
- [ ] No runtime "should never happen" errors
- [ ] All existing tests pass

## Suggested Implementation

### Option 1: State Machine Pattern (Recommended, 3-4 hours)
```typescript
// frontend/src/features/analysis/machines/analysisMachine.ts
import { createMachine } from 'xstate';

export const analysisMachine = createMachine({
  id: 'analysis',
  initial: 'loading',
  states: {
    loading: {
      on: {
        LOADED: 'idle',
        ERROR: 'error',
      },
    },
    idle: {
      on: {
        START_ANALYSIS: 'analyzing',
      },
    },
    analyzing: {
      on: {
        ANALYSIS_COMPLETE: 'generatingArtifact',
        ANALYSIS_FAILED: 'analysisFailed',
      },
    },
    generatingArtifact: {
      on: {
        ARTIFACT_READY: 'completed',
        ARTIFACT_FAILED: 'artifactFailed',
      },
    },
    completed: {},
    error: {},
    analysisFailed: {},
    artifactFailed: {},
  },
});

// Usage in component
import { useMachine } from '@xstate/react';

export const AnalyzeResult = () => {
  const [state, send] = useMachine(analysisMachine);

  // Simple switch - no nesting!
  switch (state.value) {
    case 'loading':
      return <LoadingState />;
    case 'error':
      return <ErrorState />;
    case 'analyzing':
      return <ProgressView />;
    case 'generatingArtifact':
      return <ArtifactProcessingState />;
    case 'completed':
      return <ArtifactView />;
    case 'analysisFailed':
      return <FailedAnalysisState />;
    case 'artifactFailed':
      return <ArtifactErrorState />;
    default:
      return <EmptyState />;
  }
};
```

### Option 2: Helper Function Pattern (Simpler, 2-3 hours)
```typescript
// frontend/src/features/analysis/utils/renderHelpers.ts

type AnalysisRenderState =
  | 'loading'
  | 'error'
  | 'empty'
  | 'analyzing'
  | 'generatingArtifact'
  | 'completed'
  | 'analysisFailed'
  | 'artifactFailed';

export const getAnalysisRenderState = ({
  isLoading,
  error,
  analysis,
  artifact,
}: {
  isLoading: boolean;
  error: Error | null;
  analysis: Analysis | null;
  artifact: Artifact | null;
}): AnalysisRenderState => {
  if (isLoading) return 'loading';
  if (error) return 'error';
  if (!analysis) return 'empty';

  if (!analysis.artifact_id) {
    if (analysis.status === 'failed') return 'analysisFailed';
    if (analysis.status === 'running') return 'analyzing';
    return 'empty';
  }

  if (!artifact) return 'loading'; // Loading artifact
  if (artifact.status === 'failed') return 'artifactFailed';
  if (artifact.status === 'ready') return 'completed';

  return 'generatingArtifact';
};

// Usage in component
export const AnalyzeResult = () => {
  const { isLoading, error, analysis, artifact } = useAnalysisData();

  const renderState = getAnalysisRenderState({
    isLoading,
    error,
    analysis,
    artifact,
  });

  // Single switch statement - clear and testable
  switch (renderState) {
    case 'loading':
      return <LoadingState />;
    case 'error':
      return <ErrorState error={error!} />;
    case 'empty':
      return <EmptyState />;
    case 'analyzing':
      return <ProgressView analysis={analysis!} />;
    case 'generatingArtifact':
      return <ArtifactProcessingState />;
    case 'completed':
      return <ArtifactView artifact={artifact!} />;
    case 'analysisFailed':
      return <FailedAnalysisState analysis={analysis!} />;
    case 'artifactFailed':
      return <ArtifactErrorState artifact={artifact!} />;
  }
};
```

### Option 3: Component Map Pattern (Simplest, 2 hours)
```typescript
// frontend/src/features/analysis/AnalyzeResult.tsx

const RENDER_COMPONENTS: Record<AnalysisRenderState, React.ComponentType<any>> = {
  loading: LoadingState,
  error: ErrorState,
  empty: EmptyState,
  analyzing: ProgressView,
  generatingArtifact: ArtifactProcessingState,
  completed: ArtifactView,
  analysisFailed: FailedAnalysisState,
  artifactFailed: ArtifactErrorState,
};

export const AnalyzeResult = () => {
  const props = useAnalysisData();
  const renderState = getAnalysisRenderState(props);

  const Component = RENDER_COMPONENTS[renderState];

  return <Component {...props} />;
};
```

## Testing Strategy

### Before: Impossible to test all branches
```typescript
// Cannot set up state for nested conditionals
it('renders artifact processing state', () => {
  // How to set: !isLoading AND !error AND analysis exists
  // AND analysis.artifact_id exists AND !artifact loaded yet?
  // Need to mock 5 different conditions in exact combination!
});
```

### After: Each state easily testable
```typescript
describe('getAnalysisRenderState', () => {
  it('returns "loading" when isLoading is true', () => {
    expect(getAnalysisRenderState({
      isLoading: true,
      error: null,
      analysis: null,
      artifact: null,
    })).toBe('loading');
  });

  it('returns "analyzing" when analysis is running', () => {
    expect(getAnalysisRenderState({
      isLoading: false,
      error: null,
      analysis: { status: 'running', artifact_id: null },
      artifact: null,
    })).toBe('analyzing');
  });

  // ... test all 12 branches in isolation
});
```

## State Documentation

Create visual state diagram:
```
┌─────────┐
│ Loading │
└────┬────┘
     │
     ├─→ Error
     ├─→ Empty
     │
     ├─→ Analyzing
     │      ├─→ Analysis Failed
     │      └─→ Generating Artifact
     │             ├─→ Artifact Failed
     │             └─→ Completed
     │
     └─→ (other states)
```

## Benefits

1. **Testability**: Each state tested in isolation
2. **Maintainability**: Add state = add one case to switch
3. **Readability**: Clear what renders when
4. **Type safety**: TypeScript ensures all states handled
5. **Debugging**: Can log current state for support
6. **Documentation**: State machine = visual diagram

## Related Issues

- Connects to missing loading states (#TBD)
- Relates to improved error handling (#TBD)
- May use XState for advanced state management (#TBD)

## References

- XState: https://xstate.js.org/docs/
- State machines in React: https://kentcdodds.com/blog/implementing-a-simple-state-machine-library-in-javascript
- Avoiding conditional hell: https://www.youtube.com/watch?v=WpkDN78P884

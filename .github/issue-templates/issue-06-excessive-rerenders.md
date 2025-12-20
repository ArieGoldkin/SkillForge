## Problem

**Impact**: 50 SSE events = 1,600+ component re-renders, 2 seconds of JavaScript blocking UI, creating a laggy user experience during analysis.

### Root Causes

1. **No React.memo** - All analysis components re-render on every parent update
2. **Global Zustand subscriptions** - Components subscribe to entire store instead of specific slices
3. **Recalculation on every SSE event** - No memoization of computed values
4. **Missing useMemo/useCallback** - Functions and objects recreated on every render

### Technical Details

**Current behavior:**
```
Single SSE event → 32 component re-renders
50 events during analysis = 1,600+ total re-renders
Result: 2+ seconds of blocking JavaScript execution
```

**Affected components (30+ total):**
- `AnalyzeResult.tsx` - Root component
- `ProgressColumn.tsx` - Stage list container
- `AnalysisProgressCard.tsx` - Individual stage cards
- `StepItem.tsx` - Step details
- `StageStatusBadge.tsx` - Status indicators
- All other analysis feature components

## Impact Assessment

**Severity**: HIGH
**User Impact**: Laggy, unresponsive UI during analysis
**Performance Cost**: 2+ seconds of blocked UI per analysis
**Scale**: Affects 100% of analysis workflows

## Affected Files

```
frontend/src/features/analysis/
├── AnalyzeResult.tsx
├── components/
│   ├── ProgressColumn.tsx
│   ├── AnalysisProgressCard.tsx
│   ├── StepItem.tsx
│   ├── StageStatusBadge.tsx
│   └── ... (25+ more components)
└── hooks/
    └── useSSEStream.ts (647 lines, no optimization)
```

## Acceptance Criteria

- [ ] Add `React.memo` to all 30+ analysis components with proper equality checks
- [ ] Convert Zustand subscriptions to selective slices (`useAnalysisStore(state => state.specificField)`)
- [ ] Wrap expensive calculations in `useMemo`
- [ ] Wrap event handlers and callbacks in `useCallback`
- [ ] Reduce re-renders from 1,600+ to <100 per analysis (16x improvement)
- [ ] Measure with React DevTools Profiler before/after
- [ ] Add performance regression tests

## Verification Checklist

- [ ] Run React DevTools Profiler on analysis flow
- [ ] Count re-renders: Should be <100 for 50 SSE events (currently 1,600+)
- [ ] Measure JavaScript blocking time: Should be <200ms (currently 2+ seconds)
- [ ] Verify UI remains responsive during analysis
- [ ] Test with slow network conditions (3G throttling)
- [ ] No visual regressions in component rendering
- [ ] All existing tests pass
- [ ] Add performance benchmark tests

## Suggested Implementation

### Phase 1: Add React.memo (1-2 hours)
```typescript
// Before
export const StepItem = ({ step, stage }: StepItemProps) => { ... }

// After
export const StepItem = React.memo(({ step, stage }: StepItemProps) => {
  // ... component logic
}, (prevProps, nextProps) => {
  return prevProps.step.id === nextProps.step.id &&
         prevProps.step.status === nextProps.step.status;
});
```

### Phase 2: Selective Zustand subscriptions (2-3 hours)
```typescript
// Before
const { analysis, stages } = useAnalysisStore();

// After
const analysis = useAnalysisStore(state => state.analysis);
const stages = useAnalysisStore(state => state.stages);
```

### Phase 3: Add useMemo/useCallback (2-3 hours)
```typescript
const sortedStages = useMemo(() =>
  stages.sort((a, b) => a.order - b.order),
  [stages]
);

const handleStageClick = useCallback((stageId: string) => {
  // ... handler logic
}, [/* dependencies */]);
```

## Related Issues

- Connects to future React Profiler integration (#TBD)
- Relates to state management refactoring (#TBD)

## References

- React.memo: https://react.dev/reference/react/memo
- Zustand selective subscriptions: https://docs.pmnd.rs/zustand/guides/prevent-rerenders-with-use-shallow
- React Performance: https://react.dev/learn/render-and-commit

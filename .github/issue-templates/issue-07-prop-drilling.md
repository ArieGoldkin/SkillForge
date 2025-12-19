## Problem

**Impact**: Props passed through 3-5 component levels, 15+ TypeScript interface definitions, tight coupling preventing isolated testing and rapid iteration.

### Root Causes

1. **Deep prop drilling** - Data flows through 3-5 intermediate components that don't use it
2. **Interface explosion** - 15+ TypeScript interfaces for the same data at different levels
3. **Tight coupling** - Cannot test components in isolation, must mock entire chain
4. **Maintenance burden** - Adding new data field touches 5+ files

### Technical Details

**Current prop drilling chain:**
```
AnalyzeResult
  ↓ (passes analysis, stages, steps)
ProgressColumn
  ↓ (passes stages, steps, handlers)
AnalysisProgressCard
  ↓ (passes stage, steps, handlers)
StepItem
  ↓ (finally uses step data)
```

**Interface proliferation:**
```typescript
// 15+ interfaces for similar data
interface AnalyzeResultProps { ... }
interface ProgressColumnProps { ... }
interface AnalysisProgressCardProps { ... }
interface StepItemProps { ... }
interface StageStatusProps { ... }
// ... 10+ more
```

## Impact Assessment

**Severity**: HIGH
**Developer Impact**: Cannot test components in isolation, slow iteration
**Maintenance Cost**: Every new field touches 5+ files and 5+ interfaces
**Scalability**: Adding features becomes exponentially harder

## Affected Files

```
frontend/src/features/analysis/
├── AnalyzeResult.tsx (root, passes all props down)
├── components/
│   ├── ProgressColumn.tsx (middleman layer 1)
│   ├── AnalysisProgressCard.tsx (middleman layer 2)
│   ├── StepItem.tsx (actual consumer)
│   └── ... (20+ more coupled components)
└── types/
    └── analysis.types.ts (15+ interface definitions)
```

## Acceptance Criteria

- [ ] Create `AnalysisContext` with React Context API
- [ ] Eliminate prop drilling - components access context directly
- [ ] Reduce 15+ interfaces to 3-5 semantic types
- [ ] All components testable in isolation (no prop chain mocking)
- [ ] Adding new data field touches 1-2 files max (currently 5+)
- [ ] Zero breaking changes to existing UI behavior
- [ ] All tests pass with new context approach

## Verification Checklist

- [ ] No props passed through components that don't use them
- [ ] Each component has single-purpose interface (not kitchen sink)
- [ ] Can render StepItem without AnalyzeResult parent
- [ ] Can render AnalysisProgressCard with mock context provider
- [ ] TypeScript inference works correctly with context
- [ ] No runtime errors from missing context providers
- [ ] All existing tests pass
- [ ] Add new context-based unit tests

## Suggested Implementation

### Phase 1: Create AnalysisContext (2-3 hours)
```typescript
// frontend/src/features/analysis/context/AnalysisContext.tsx
interface AnalysisContextValue {
  // Core data
  analysis: Analysis | null;
  stages: Stage[];
  steps: Record<string, Step[]>;

  // Actions
  updateStage: (stageId: string, updates: Partial<Stage>) => void;
  updateStep: (stepId: string, updates: Partial<Step>) => void;

  // Computed state
  isLoading: boolean;
  hasErrors: boolean;
}

export const AnalysisContext = createContext<AnalysisContextValue | null>(null);

export const useAnalysisContext = () => {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysisContext must be used within AnalysisProvider');
  }
  return context;
};
```

### Phase 2: Refactor components to use context (3-4 hours)
```typescript
// Before: 5 levels of prop drilling
<AnalyzeResult analysis={analysis} stages={stages} steps={steps}>
  <ProgressColumn stages={stages} steps={steps}>
    <AnalysisProgressCard stage={stage} steps={steps}>
      <StepItem step={step} />

// After: Direct context access
<AnalysisProvider>
  <AnalyzeResult>
    <ProgressColumn>
      <AnalysisProgressCard>
        <StepItem />  {/* uses useAnalysisContext() internally */}
```

### Phase 3: Simplify interfaces (1-2 hours)
```typescript
// Reduce from 15+ interfaces to semantic types
type AnalysisProviderProps = { children: ReactNode };
type StepItemProps = { stepId: string }; // Just the ID, gets data from context
type StageCardProps = { stageId: string };
```

## Benefits

1. **Testability**: Mock context provider instead of 5-level prop chain
2. **Maintainability**: Add field once in context, all components get it
3. **Performance**: Can optimize context with multiple providers (data vs actions)
4. **Developer Experience**: No more "prop tunneling" through intermediaries

## Related Issues

- Connects to excessive re-renders (#TBD) - can optimize context subscriptions
- Relates to testing improvements (#TBD)

## References

- React Context: https://react.dev/learn/passing-data-deeply-with-context
- Context optimization: https://react.dev/reference/react/useContext#optimizing-re-renders-when-passing-objects-and-functions
- Testing with Context: https://kentcdodds.com/blog/how-to-test-custom-react-hooks

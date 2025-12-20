## Problem

**Impact**: Tests use 24 'as any' and 'as unknown' assertions, bypassing TypeScript's type safety, creating false confidence in test coverage and missing real type regressions.

### Root Causes

1. **Type escape hatches** - Tests use `as any` to bypass type errors instead of fixing root cause
2. **Mock objects incomplete** - Mocks missing required fields, use `as any` to force compatibility
3. **No type factories** - Each test creates ad-hoc mocks, inconsistent across test suite
4. **False confidence** - Tests pass but don't catch type regressions in production code

### Technical Details

**Unsafe assertions found:**
```typescript
// Library.error.test.tsx - 18 instances
const mockError = { message: 'Error' } as any;
const mockResponse = { data: null } as unknown as LibraryResponse;

// downloadMarkdown.test.ts - 6 instances
const mockBlob = {} as any;
URL.createObjectURL = vi.fn(() => 'blob:url') as any;
```

**Why this is dangerous:**
```typescript
// Test passes with 'as any'
const analysis = { id: '123' } as any;
useAnalysis(analysis.status); // No type error in test

// Production breaks because 'status' doesn't exist
// TypeScript would catch this without 'as any'
```

## Impact Assessment

**Severity**: HIGH
**Quality Impact**: Tests don't catch type regressions
**Developer Experience**: False confidence in test coverage
**Production Risk**: Type errors slip through to runtime

## Affected Files

```
frontend/src/features/
├── library/__tests__/
│   ├── Library.error.test.tsx (18 'as any' assertions)
│   ├── Library.loading.test.tsx (type issues)
│   └── Library.success.test.tsx (type issues)
└── artifact/hooks/__tests__/
    └── downloadMarkdown.test.ts (6 'as any' assertions)
```

## Acceptance Criteria

- [ ] Zero 'as any' assertions in test files
- [ ] Zero 'as unknown as Type' casts in test files
- [ ] Create type-safe factory functions for all domain objects
- [ ] All mocks use proper TypeScript types
- [ ] Tests catch type regressions (verify with intentional breaking change)
- [ ] No increase in test setup complexity
- [ ] All tests pass with strict TypeScript checking

## Verification Checklist

- [ ] Run `grep -r "as any" frontend/src/**/*.test.ts*` returns 0 results
- [ ] Run `grep -r "as unknown as" frontend/src/**/*.test.ts*` returns 0 results
- [ ] All test files pass TypeScript strict mode
- [ ] Can catch type regressions (test by removing a field from interface)
- [ ] Factory functions reusable across test suite
- [ ] Test setup code is readable and maintainable
- [ ] No runtime type errors in tests
- [ ] All existing tests pass

## Suggested Implementation

### Phase 1: Create type factories (2-3 hours)
```typescript
// frontend/src/features/library/__tests__/factories.ts

export const createMockAnalysis = (overrides?: Partial<Analysis>): Analysis => ({
  id: 'test-id-123',
  url: 'https://example.com',
  status: 'completed',
  title: 'Test Analysis',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  artifact_id: null,
  stages: [],
  ...overrides,
});

export const createMockLibraryItem = (overrides?: Partial<LibraryItem>): LibraryItem => ({
  id: 'library-item-123',
  analysis: createMockAnalysis(),
  created_at: new Date().toISOString(),
  ...overrides,
});

export const createMockError = (message: string): Error => {
  const error = new Error(message);
  error.name = 'TestError';
  return error;
};
```

### Phase 2: Refactor tests to use factories (3-4 hours)
```typescript
// Before: Unsafe type assertions
const mockError = { message: 'Network error' } as any;
const mockAnalysis = { id: '123', status: 'failed' } as any;

// After: Type-safe factories
import { createMockError, createMockAnalysis } from './factories';

const mockError = createMockError('Network error');
const mockAnalysis = createMockAnalysis({ status: 'failed' });
```

### Phase 3: Type-safe mock utilities (2 hours)
```typescript
// frontend/src/test-utils/mockUtils.ts

type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export const createMock = <T extends object>(
  defaults: T,
  overrides?: DeepPartial<T>
): T => {
  return {
    ...defaults,
    ...overrides,
  } as T;
};

// Usage: Type-safe, no 'as any'
const mockBlob = createMock(new Blob(['test']), {
  size: 1024,
  type: 'text/markdown',
});
```

### Phase 4: Type-safe vi.fn() mocks (1-2 hours)
```typescript
// Before: Unsafe
URL.createObjectURL = vi.fn(() => 'blob:url') as any;

// After: Type-safe
URL.createObjectURL = vi.fn<[Blob], string>(() => 'blob:url');

// Or with helper
const mockCreateObjectURL = vi.fn<typeof URL.createObjectURL>(
  () => 'blob:test-url'
);
global.URL.createObjectURL = mockCreateObjectURL;
```

## Examples of Type Safety Benefits

### Catches Missing Fields
```typescript
// With 'as any' - test passes, production breaks
const analysis = { id: '123' } as any;
expect(analysis.status).toBe('completed'); // Passes but status doesn't exist!

// With factory - TypeScript error at compile time
const analysis = createMockAnalysis({ id: '123' });
// Must include all required fields or get type error
```

### Catches Type Changes
```typescript
// Interface changes: status: string → status: AnalysisStatus enum
interface Analysis {
  status: 'pending' | 'running' | 'completed' | 'failed'; // Now an enum
}

// With 'as any' - tests still pass with invalid values
const analysis = { status: 'invalid-status' } as any; // No error!

// With factory - TypeScript catches invalid value
const analysis = createMockAnalysis({
  status: 'invalid-status', // Type error! Must use valid enum value
});
```

## Benefits

1. **Type safety**: Catch regressions at compile time
2. **Maintainability**: Update factory once, all tests benefit
3. **Readability**: Clear what fields are being tested
4. **Confidence**: Tests actually validate types match production
5. **Refactoring**: Safe to change types, tests break at compile time

## Related Issues

- Connects to overall type safety improvements (#TBD)
- Relates to test coverage expansion (#TBD)

## References

- TypeScript test factories: https://kentcdodds.com/blog/make-your-test-fail
- Vitest typed mocks: https://vitest.dev/guide/mocking.html#typing
- Avoiding 'as any': https://www.totaltypescript.com/dont-use-any

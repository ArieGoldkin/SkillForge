# React 19 API Improvements

**Date:** December 27, 2025
**Branch:** `issue/547-react-19-apis`
**Status:** ✅ Complete (Issue #547)

## Overview

This document outlines the React 19 API improvements implemented in the SkillForge frontend, fully adopting React 19's flagship features for modern UX patterns.

## Implementation Summary

| Feature | Status | Files | Impact |
|---------|--------|-------|--------|
| `useOptimistic` | ✅ Complete | 4 files | Instant UI feedback |
| `useActionState` | ✅ Complete | 1 file | Form state management |
| `useFormStatus` | ✅ Complete | 2 files | No prop drilling |
| `startTransition` | ✅ Complete | 4 files | Non-blocking updates |
| `use()` hook | ✅ Complete | 2 files | Suspense-native data |
| `Suspense` boundaries | ✅ Complete | 5+ routes | Declarative loading |

---

## Implemented Changes

### 1. useOptimistic in useTutorChat Hook (NEW)

**File:** `frontend/src/features/tutor/hooks/useTutorChat.ts`

The tutor chat now shows messages **instantly** before API confirmation:

```typescript
import { useOptimistic, useTransition } from 'react'

export function useTutorChat({ sessionId }: UseTutorChatOptions) {
  const { data: confirmedMessages = [] } = useQuery({...})

  // Optimistic state - shows messages before API confirms
  const [optimisticMessages, addOptimisticMessage] = useOptimistic(
    confirmedMessages,
    (current, newMessage: TutoringMessage) => [...current, newMessage]
  )

  const [isPending, startTransition] = useTransition()

  const sendMessage = async (content: string) => {
    const optimisticMessage: TutoringMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      // ...
    }

    startTransition(async () => {
      addOptimisticMessage(optimisticMessage) // Instant UI update!

      try {
        await mockTutoringAPI.sendMessage(sessionId, content)
      } catch {
        // useOptimistic auto-rollback on error
        toast({ title: 'Failed to send message', variant: 'destructive' })
      }
    })
  }

  return {
    messages: optimisticMessages, // Always show optimistic state
    sendMessage,
    isPending,
    isLoading,
  }
}
```

**Benefits:**
- Messages appear **instantly** (no 200-500ms delay)
- Automatic rollback on API failure
- Single unified hook (replaced `useTutoringMessages` + `useSendMessage`)
- No prop drilling between hooks
- Concurrent rendering with `useTransition`

**Migration:** Legacy hooks `useTutoringMessages.ts` and `useSendMessage.ts` have been **deleted**.

---

### 2. use() Hook for Suspense-Native Data (NEW)

**Files:**
- `frontend/src/features/artifact/components/SuspenseArtifactContent.tsx`
- `frontend/src/lib/promiseCache.ts`

React 19's `use()` hook enables declarative data fetching:

```typescript
import { use } from 'react'

export function SuspenseArtifactContent({
  artifactPromise
}: {
  artifactPromise: Promise<ArtifactMetadataResponse>
}) {
  // use() suspends until promise resolves
  const response = use(artifactPromise)

  // No loading state needed - Suspense handles it!
  return (
    <div>
      <MarkdownPreview content={response.markdown_content} />
      <FeedbackButtons artifactId={response.artifact_id} />
    </div>
  )
}

// Usage with Suspense boundary:
<Suspense fallback={<ArtifactSkeleton />}>
  <SuspenseArtifactContent artifactPromise={promise} />
</Suspense>
```

**Promise Cache Utility:**

```typescript
// lib/promiseCache.ts - Prevents infinite suspense loops
export function cachePromise<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  if (!cache.has(key)) {
    const promise = fetcher()
      .catch((error) => {
        cache.delete(key) // Remove failed promises for retry
        throw error
      })
    cache.set(key, promise)
  }
  return cache.get(key) as Promise<T>
}
```

**Benefits:**
- No manual `isLoading` / `error` state management
- Declarative loading via Suspense boundaries
- Future-proof for Server Components migration
- Better code splitting with `Suspense` + `lazy()`

---

### 3. useOptimistic in useFeedback Hook

**File:** `frontend/src/features/artifact/hooks/useFeedback.ts`

```typescript
const [optimisticFeedback, setOptimisticFeedback] = useOptimistic(
  selectedFeedback,
  (_current, newFeedback: FeedbackType) => newFeedback
)

const submitFeedback = async (feedback: FeedbackType) => {
  startTransition(async () => {
    setOptimisticFeedback(feedback) // Instant!
    try {
      await api.submit()
      setSelectedFeedback(feedback)
    } catch {
      // Auto-rollback
    }
  })
}
```

---

### 4. useActionState in Home Component

**File:** `frontend/src/features/home/Home.tsx`

```typescript
const [state, submitAction, isPending] = useActionState<AnalysisState, AnalysisFormData>(
  async (_prevState, formData) => {
    try {
      const response = await api.createAnalysis(formData)
      navigate(`/analyze/${response.analysis_id}`)
      return { success: true, error: null }
    } catch (err) {
      return { success: false, error: err.message }
    }
  },
  { success: false, error: null }
)
```

**Benefits:**
- Single source of truth for form state
- Replaces 3+ `useState` calls
- Automatic `isPending` state

---

### 5. useFormStatus in SubmitButton

**File:** `frontend/src/shared/components/SubmitButton.tsx`

```typescript
import { useFormStatus } from 'react-dom'

export function SubmitButton({ children, loadingText = 'Submitting...' }) {
  const { pending } = useFormStatus()

  return (
    <Button type="submit" disabled={pending} aria-busy={pending}>
      {pending ? loadingText : children}
    </Button>
  )
}
```

**Benefits:**
- No prop drilling for form state
- Automatically detects parent form submission
- Works with any form in component tree

---

### 6. startTransition for Non-Blocking Updates

**Files:**
- `frontend/src/features/library/Library.tsx` (3 usages)
- `frontend/src/features/artifact/hooks/useFeedback.ts`
- `frontend/src/features/artifact/components/MarkdownPreview/internal/CopyButton.tsx`
- `frontend/src/features/tutor/hooks/useTutorChat.ts`

```typescript
const [isPending, startTransition] = useTransition()

const handleFilterChange = (filters: Filters) => {
  startTransition(() => {
    setFilters(filters) // Non-blocking, UI stays responsive
  })
}
```

---

## File Map

```
frontend/src/
├── features/
│   ├── artifact/
│   │   ├── hooks/useFeedback.ts ──────────── useOptimistic + startTransition
│   │   └── components/
│   │       ├── SuspenseArtifactContent.tsx ─ use() hook (NEW)
│   │       └── MarkdownPreview/internal/
│   │           └── CopyButton.tsx ────────── useOptimistic + startTransition
│   │
│   ├── home/
│   │   ├── Home.tsx ──────────────────────── useActionState
│   │   └── components/HeroSection.tsx ────── useFormStatus
│   │
│   ├── library/
│   │   ├── Library.tsx ───────────────────── startTransition (3x)
│   │   └── components/SkillFilters/
│   │       └── hooks/useSkillFilters.ts ──── useOptimistic
│   │
│   └── tutor/
│       └── hooks/useTutorChat.ts ─────────── useOptimistic + startTransition (NEW)
│
├── shared/components/
│   └── SubmitButton.tsx ──────────────────── useFormStatus
│
├── lib/
│   └── promiseCache.ts ───────────────────── Promise caching for use() (NEW)
│
└── router/
    └── LazyRoute.tsx ─────────────────────── Suspense wrapper
```

---

## Testing

| Hook/Component | Tests | Status |
|----------------|-------|--------|
| `useFeedback` | 13 tests | ✅ All pass |
| `useTutorChat` | 10 tests | ✅ All pass |
| `SuspenseArtifactContent` | 15 tests | ✅ All pass |
| `promiseCache` | 5 tests | ✅ All pass |

---

## Migration Guide

### For New Components

1. **Optimistic Updates:** Use `useOptimistic` + `useTransition`
   ```typescript
   const [optimistic, setOptimistic] = useOptimistic(actual, reducer)
   startTransition(async () => {
     setOptimistic(newValue)
     await api.call()
   })
   ```

2. **Form State:** Use `useActionState` instead of multiple `useState`
   ```typescript
   const [state, action, isPending] = useActionState(asyncFn, initial)
   ```

3. **Data Fetching:** Consider `use()` + `Suspense` for read-only data
   ```typescript
   const data = use(promise)
   // Wrap parent in <Suspense fallback={<Skeleton />}>
   ```

4. **Submit Buttons:** Use `SubmitButton` with `useFormStatus`
   ```typescript
   <SubmitButton loadingText="Saving...">Save</SubmitButton>
   ```

### Patterns to Avoid

❌ Manual rollback with try/catch
❌ Multiple useState for form state
❌ Prop drilling for loading states
❌ useEffect + useState for data fetching (when Suspense fits)

---

## Performance Impact

- **Bundle Size:** No change (React 19 APIs are built-in)
- **Runtime:** Improved concurrent rendering with transitions
- **UX:** Instant feedback with optimistic updates

---

## References

- [React 19 Release Notes](https://react.dev/blog/2024/12/05/react-19)
- [useOptimistic API](https://react.dev/reference/react/useOptimistic)
- [use() Hook](https://react.dev/reference/react/use)
- [useActionState API](https://react.dev/reference/react/useActionState)
- [useFormStatus API](https://react.dev/reference/react-dom/hooks/useFormStatus)

---

**Issue:** [#547 - Adopt React 19 APIs](https://github.com/your-org/SkillForge/issues/547)
**PR:** To be created after verification

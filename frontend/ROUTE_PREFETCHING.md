# Route Prefetching Implementation (Issue #554)

## Overview

Implemented comprehensive route prefetching for the SkillForge frontend using TanStack Router and TanStack Query. This feature improves perceived performance by preloading routes and data when users hover over or focus on navigation links.

## Implementation Details

### 1. Router Configuration (`/src/router.tsx`)

Enhanced the TanStack Router configuration with optimized prefetching settings:

```typescript
export const router = createRouter({
  routeTree,
  defaultPreload: 'intent', // Preload on hover/focus
  defaultPreloadDelay: 50, // Start prefetch after 50ms hover
  defaultPendingMs: 1000, // Show pending UI after 1s
  defaultPendingMinMs: 500, // Keep pending UI for minimum 500ms
  defaultStaleTime: TIME_CONSTANTS.PREFETCH_STALE_TIME, // 5 minutes cache
  defaultErrorComponent: GlobalErrorComponent,
})
```

**Key Benefits:**
- **50ms delay**: Balances responsiveness with unnecessary prefetches
- **5-minute cache**: Reduces redundant API calls for prefetched data
- **Pending UI thresholds**: Prevents loading flashes on fast connections

### 2. usePrefetch Hook (`/src/hooks/usePrefetch.ts`)

Created a comprehensive hook that combines route and data prefetching:

```typescript
const { prefetchAnalysis, prefetchArtifact, prefetchLibrary } = usePrefetch()
```

**Features:**
- **Route prefetching**: Uses TanStack Router's `preloadRoute()`
- **Data prefetching**: Uses TanStack Query's `prefetchQuery()`
- **Silent failures**: Prefetch errors don't block navigation
- **Type-safe targets**: Predefined `PREFETCH_TARGETS` for common routes

**Available Methods:**
- `prefetchAnalysis(analysisId)` - Prefetch analysis detail page
- `prefetchArtifact(artifactId, analysisId?)` - Prefetch artifact page
- `prefetchLibrary()` - Prefetch library page
- `prefetch(target)` - Generic prefetch for custom targets

### 3. Updated Components

#### SkillCard Component (`/src/features/library/components/SkillCard.tsx`)

Added hover and focus prefetching to analysis cards:

```tsx
<Card
  onMouseEnter={() => prefetchAnalysis(id)}
  onFocus={() => prefetchAnalysis(id)}
  // ... other props
/>
```

**Benefits:**
- **Hover prefetch**: Data loads while user decides to click
- **Keyboard navigation**: Focus events trigger prefetch for accessibility
- **Instant navigation**: Route + data ready when user clicks

#### NavigationLinks Component (`/src/shared/components/navigation/NavigationLinks.tsx`)

Added prefetching to the Library navigation link:

```tsx
<NavLink to="/library" onMouseEnter={() => prefetchLibrary()}>
  Library
</NavLink>
```

#### NavLink Component (`/src/shared/components/navigation/NavLink.tsx`)

Enhanced to support `onMouseEnter` and `onFocus` props for prefetch integration.

### 4. Constants (`/src/lib/constants.ts`)

Added prefetch-specific timing constants:

```typescript
export const TIME_CONSTANTS = {
  QUERY_STALE_TIME: 60 * 1000, // 1 minute (standard queries)
  PREFETCH_STALE_TIME: 5 * 60 * 1000, // 5 minutes (prefetched data)
}
```

**Rationale:**
- Longer stale time for prefetched data reduces redundant API calls
- Standard queries remain fresh for active user interactions

### 5. Tests (`/src/hooks/__tests__/usePrefetch.test.tsx`)

Comprehensive test suite covering:
- Target configuration validation
- Query function execution
- Error handling
- Route and query key generation

**Test Coverage:**
- 8 passing tests
- Validates all PREFETCH_TARGETS configurations
- Tests successful and failed prefetch scenarios

## Usage Examples

### Basic Usage

```tsx
import { usePrefetch } from '@hooks/usePrefetch'

function MyComponent() {
  const { prefetchAnalysis } = usePrefetch()

  return (
    <div onMouseEnter={() => prefetchAnalysis('analysis-123')}>
      View Analysis
    </div>
  )
}
```

### Custom Prefetch Target

```tsx
import { usePrefetch, PREFETCH_TARGETS } from '@hooks/usePrefetch'

function CustomComponent() {
  const { prefetch } = usePrefetch()

  const handleHover = () => {
    prefetch({
      route: '/custom-route',
      queryKey: ['custom', 'data'],
      queryFn: async () => fetch('/api/custom').then(r => r.json())
    })
  }

  return <div onMouseEnter={handleHover}>Custom Link</div>
}
```

## Performance Impact

### Expected Improvements

1. **Perceived Load Time**: Near-instant navigation for prefetched routes
2. **API Call Reduction**: 5-minute cache reduces redundant fetches
3. **UX Smoothness**: No loading spinners for prefetched content

### Network Efficiency

- **Smart Prefetching**: Only triggers on user intent (hover/focus)
- **Silent Failures**: Network errors don't impact user experience
- **Cache-First**: Respects existing cached data

## Browser Compatibility

Works on all modern browsers supporting:
- TanStack Router v1.141.2+
- TanStack Query v5.90.12+
- React 19+

## Future Enhancements

### Potential Improvements

1. **Adaptive Prefetching**: Adjust based on network speed
2. **Priority Queuing**: Prefetch critical routes first
3. **Analytics**: Track prefetch hit rate and performance gains
4. **Service Worker Integration**: Cache prefetched resources offline

### Additional Routes

Consider adding prefetching for:
- Tutor sessions (`/tutor/$sessionId`)
- Showcase page (`/showcase`)
- Annotation queue (`/annotation-queue`)

## Testing

Run the test suite:

```bash
# Unit tests
npm run test:run -- src/hooks/__tests__/usePrefetch.test.tsx

# Quality checks
npm run quality:check

# Type checking
npm run typecheck
```

## Related Files

- `/src/router.tsx` - Router configuration
- `/src/hooks/usePrefetch.ts` - Prefetch hook implementation
- `/src/hooks/index.ts` - Hook exports
- `/src/lib/constants.ts` - Timing constants
- `/src/features/library/components/SkillCard.tsx` - Analysis card prefetching
- `/src/shared/components/navigation/NavigationLinks.tsx` - Nav link prefetching
- `/src/shared/components/navigation/NavLink.tsx` - NavLink component updates
- `/src/hooks/__tests__/usePrefetch.test.tsx` - Test suite

## Issue Reference

Implements: **Issue #554** - Route Prefetching for Frontend Performance

---

**Implementation Date**: December 25, 2025
**Status**: Complete, Tested, Production-Ready

---
name: frontend-bundle
description: Frontend bundle analysis and optimization
version: 1.0.0
tags: [frontend, bundle, vite, optimization]
size: atomic
domain: tools
---

# Frontend Bundle Analysis

## Vite Bundle Analyzer

```typescript
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    process.env.ANALYZE && visualizer({
      open: true,
      filename: 'dist/bundle-stats.html',
      gzipSize: true,
      brotliSize: true,
    }),
  ].filter(Boolean),
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'router': ['@tanstack/react-router'],
          'query': ['@tanstack/react-query'],
        },
      },
    },
  },
})
```

```bash
# Run analysis
ANALYZE=true npm run build
```

## Bundle Size Budgets

| Chunk | Target |
|-------|--------|
| Total (gzip) | < 200KB |
| Main entry | < 50KB |
| React vendor | < 45KB |
| Lazy routes | < 30KB each |

## Tree-Shaking

```typescript
// ❌ BAD: Barrel imports
import { Button, Card } from '@/components'

// ✅ GOOD: Direct imports
import { Button } from '@/components/ui/button'

// ❌ BAD: Import entire library
import { motion } from 'framer-motion'

// ✅ GOOD: Import core only
import { motion } from 'framer-motion/m'
```

## Code Splitting

```typescript
// Route-based splitting
const AnalyzeRoute = createFileRoute('/analyze/$id')({
  component: lazy(() => import('./AnalyzeResult')),
  pendingComponent: Skeleton,
})

// Component-based splitting
const HeavyChart = lazy(() => import('./HeavyChart'))

function Dashboard() {
  return (
    <Suspense fallback={<Skeleton />}>
      <HeavyChart />
    </Suspense>
  )
}
```

## React 19 Performance

```typescript
// useTransition for non-urgent updates
const [isPending, startTransition] = useTransition()

startTransition(() => {
  setResults(searchDatabase(query))
})

// useOptimistic for instant feedback
const [optimistic, addOptimistic] = useOptimistic(items)

async function handleAdd(item) {
  addOptimistic(item)  // Instant
  await saveItem(item) // Background
}
```

## Virtualization

```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

// For lists > 100 items
const virtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 80,
  overscan: 5,
})
```

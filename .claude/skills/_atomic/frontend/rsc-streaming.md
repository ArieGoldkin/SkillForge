---
name: rsc-streaming
description: Streaming with Suspense, loading states, and PPR
version: 1.0.0
tags: [react, streaming, suspense, ppr, nextjs]
size: atomic
domain: frontend
---

# Streaming & Suspense

## Basic Streaming

```tsx
import { Suspense } from 'react'

export default function Dashboard() {
  return (
    <div>
      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart />
      </Suspense>

      <Suspense fallback={<InvoicesSkeleton />}>
        <LatestInvoices />
      </Suspense>
    </div>
  )
}
```

## loading.tsx (Route-Level)

```tsx
// app/dashboard/loading.tsx
export default function Loading() {
  return <DashboardSkeleton />
}
```

## Nested Suspense

```tsx
export default function Page() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Header />
      <Suspense fallback={<ContentSkeleton />}>
        <MainContent />
        <Suspense fallback={<SidebarSkeleton />}>
          <Sidebar />
        </Suspense>
      </Suspense>
    </Suspense>
  )
}
```

## Partial Prerendering (PPR)

Mix static shell with dynamic content:

```tsx
// Enable PPR
export const experimental_ppr = true

export default function Page() {
  return (
    <div>
      <StaticHeader />  {/* Prerendered */}

      <Suspense fallback={<Skeleton />}>
        <DynamicContent />  {/* Streamed */}
      </Suspense>

      <StaticFooter />  {/* Prerendered */}
    </div>
  )
}
```

## error.tsx (Error Boundaries)

```tsx
'use client'

export default function Error({
  error,
  reset
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <button onClick={() => reset()}>Try again</button>
    </div>
  )
}
```

## Benefits

- Show content as it's ready
- Non-blocking data fetching
- Better Core Web Vitals (LCP, FCP)
- Progressive loading experience

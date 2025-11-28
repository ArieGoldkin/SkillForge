import { Suspense } from 'react'

import { PageLoader } from './PageLoader'
import { RouteErrorBoundary } from './RouteErrorBoundary'

export function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<PageLoader />}>{children}</Suspense>
    </RouteErrorBoundary>
  )
}

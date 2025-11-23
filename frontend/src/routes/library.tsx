import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load Library component
const Library = lazy(() => import('@features/library').then((m) => ({ default: m.Library })))

export const Route = createFileRoute('/library')({
  component: () => (
    <LazyRoute>
      <Library />
    </LazyRoute>
  ),
})

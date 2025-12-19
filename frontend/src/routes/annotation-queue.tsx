import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load AnnotationQueuePage component
const AnnotationQueuePage = lazy(() =>
  import('@features/annotation-review').then((m) => ({ default: m.AnnotationQueuePage }))
)

export const Route = createFileRoute('/annotation-queue')({
  component: () => (
    <LazyRoute>
      <AnnotationQueuePage />
    </LazyRoute>
  ),
})

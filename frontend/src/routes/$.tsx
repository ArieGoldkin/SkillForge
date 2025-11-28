import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

const NotFound = lazy(() => import('@features/not-found').then((m) => ({ default: m.NotFound })))

export const Route = createFileRoute('/$')({
  component: () => (
    <LazyRoute>
      <NotFound />
    </LazyRoute>
  ),
})

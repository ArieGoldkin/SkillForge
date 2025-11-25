import { lazy } from 'react'

import { createFileRoute } from '@tanstack/react-router'

import { LazyRoute } from '@/router/LazyRoute'

const NotFound = lazy(() => import('@/features/not-found').then((m) => ({ default: m.NotFound })))

export const Route = createFileRoute('/$')({
  component: () => (
    <LazyRoute>
      <NotFound />
    </LazyRoute>
  ),
})

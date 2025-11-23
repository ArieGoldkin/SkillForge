import { lazy } from 'react'

import { LazyRoute } from '@router/LazyRoute'
import { createFileRoute } from '@tanstack/react-router'

// Lazy load Home component
const Home = lazy(() => import('@features/home').then((m) => ({ default: m.Home })))

export const Route = createFileRoute('/')({
  component: () => (
    <LazyRoute>
      <Home />
    </LazyRoute>
  ),
})

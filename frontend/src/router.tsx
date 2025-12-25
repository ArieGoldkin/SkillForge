import { createRouter } from '@tanstack/react-router'

import { TIME_CONSTANTS } from './lib/constants'
import { GlobalErrorComponent } from './router/GlobalErrorComponent'
// Import route tree - TanStack Router will generate this automatically
// The route tree is built from the files in src/routes/
import { routeTree } from './routeTree.gen'

// Create the router instance with type-safe routing
export const router = createRouter({
  routeTree,
  defaultPreload: 'intent', // Preload on hover/focus for better UX
  defaultPreloadDelay: 50, // Start prefetch after 50ms hover (reduced from default 100ms)
  defaultPendingMs: 1000, // Show pending UI after 1s (default)
  defaultPendingMinMs: 500, // Keep pending UI for minimum 500ms to avoid flash
  defaultStaleTime: TIME_CONSTANTS.PREFETCH_STALE_TIME, // Cache prefetched data for 5 minutes
  defaultErrorComponent: GlobalErrorComponent, // Global error handling
})

// Register router for type safety throughout the app
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

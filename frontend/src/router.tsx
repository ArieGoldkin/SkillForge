import { createRouter } from '@tanstack/react-router'

// Import route tree - TanStack Router will generate this automatically
// The route tree is built from the files in src/routes/
import { routeTree } from './routeTree.gen'

// Create the router instance with type-safe routing
export const router = createRouter({
  routeTree,
  defaultPreload: 'intent', // Preload on hover/focus for better UX
})

// Register router for type safety throughout the app
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

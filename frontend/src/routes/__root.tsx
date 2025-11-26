import { useEffect } from 'react'

import { applyTheme, setupSystemThemeListener, useThemeStore } from '@stores/themeStore'
import { createRootRoute, Outlet } from '@tanstack/react-router'

import { Navigation } from '@shared/components/Navigation'

/**
 * Root Layout Component
 *
 * Provides the base layout structure for all routes:
 * - Theme management and application
 * - Navigation header
 * - Route content outlet
 *
 * Theme handling:
 * - Applies theme via data-theme attribute and CSS classes
 * - Listens for system preference changes
 * - Persists theme selection in localStorage
 */
function RootComponent() {
  const theme = useThemeStore((state) => state.theme)

  // Apply theme on mount and when theme changes
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Listen for system theme changes when theme is 'system'
  useEffect(() => {
    if (theme !== 'system') return

    const cleanup = setupSystemThemeListener(() => {
      applyTheme(theme)
    })

    return cleanup
  }, [theme])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navigation />
      <main>
        <Outlet />
      </main>
    </div>
  )
}

// Create root route - this serves as the layout for all routes
export const Route = createRootRoute({
  component: RootComponent,
})

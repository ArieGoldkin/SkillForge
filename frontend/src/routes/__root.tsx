import { useEffect } from 'react'

import { Outlet, createRootRoute } from '@tanstack/react-router'

import { Navigation } from '@shared/components/Navigation'

import { useAppStore } from '@store/useAppStore'

function RootComponent() {
  const theme = useAppStore((state) => state.theme)

  // Apply theme to document
  useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove('light', 'dark')

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      root.classList.add(systemTheme)
    } else {
      root.classList.add(theme)
    }
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

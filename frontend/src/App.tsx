import { useEffect } from 'react'

import { Outlet } from 'react-router-dom'

import { Navigation } from '@shared/components/Navigation'

import { useAppStore } from '@store/useAppStore'

function App() {
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

export default App

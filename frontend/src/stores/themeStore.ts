import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

/**
 * Theme Store
 *
 * Manages theme state with localStorage persistence.
 * Supports light, dark, and system preference detection.
 *
 * Storage key: skillforge-theme
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',

      setTheme: (theme) => set({ theme }),

      toggleTheme: () =>
        set((state) => {
          // Three-state cycle: light → dark → system → light
          const cycle: Record<Theme, Theme> = {
            light: 'dark',
            dark: 'system',
            system: 'light',
          }
          return { theme: cycle[state.theme] }
        }),
    }),
    {
      name: 'skillforge-theme',
    }
  )
)

/**
 * Get the resolved theme (converts 'system' to actual 'light' or 'dark')
 */
export function getResolvedTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

/**
 * Apply theme to document
 * Uses data-theme attribute on documentElement
 */
export function applyTheme(theme: Theme): void {
  const resolvedTheme = getResolvedTheme(theme)
  document.documentElement.dataset.theme = resolvedTheme

  document.documentElement.classList.remove('light', 'dark')
  document.documentElement.classList.add(resolvedTheme)
}

/**
 * Setup system theme preference listener
 * Returns cleanup function
 */
export function setupSystemThemeListener(onChange: () => void): () => void {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

  const handler = () => onChange()

  // Modern browsers
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }

  // Fallback for older browsers
  mediaQuery.addListener(handler)
  return () => mediaQuery.removeListener(handler)
}

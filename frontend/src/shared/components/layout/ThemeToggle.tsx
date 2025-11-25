import { useEffect } from 'react'

import { Moon, Sun, Monitor } from 'lucide-react'

import { Button } from '@/shared/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/shared/components/ui/tooltip'
import {
  applyTheme,
  getResolvedTheme,
  setupSystemThemeListener,
  useThemeStore,
} from '@/stores/themeStore'

/**
 * ThemeToggle Component
 *
 * Interactive theme switcher with three states:
 * - Light: Sun icon
 * - Dark: Moon icon
 * - System: Monitor icon
 *
 * Features:
 * - localStorage persistence via Zustand
 * - System preference detection
 * - Accessible with ARIA labels and tooltips
 * - Smooth transitions between themes
 */
export function ThemeToggle() {
  const { theme, toggleTheme } = useThemeStore()

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

  // Determine which icon to show
  const Icon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor

  // Get tooltip text
  const tooltipText =
    theme === 'light' ? 'Light mode' : theme === 'dark' ? 'Dark mode' : 'System preference'

  // Get resolved theme for aria-pressed state
  const resolvedTheme = getResolvedTheme(theme)
  const isDark = resolvedTheme === 'dark'

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={`Toggle theme (current: ${tooltipText})`}
            aria-pressed={isDark}
            className="transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <Icon className="h-5 w-5 transition-transform duration-200 hover:scale-110" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

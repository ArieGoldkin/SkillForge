import { Moon, Sun, User } from 'lucide-react'

import { useAppStore } from '@store/useAppStore'

export function NavigationActions() {
  const { theme, toggleTheme } = useAppStore()

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={toggleTheme}
        className="rounded-md p-2 transition-colors hover:bg-muted"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun className="h-6 w-6" /> : <Moon className="h-6 w-6" />}
      </button>
      <button className="rounded-md p-2 transition-colors hover:bg-muted" aria-label="User menu">
        <User className="h-6 w-6" />
      </button>
    </div>
  )
}

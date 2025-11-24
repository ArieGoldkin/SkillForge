import { User } from 'lucide-react'

import { ThemeToggle } from '@/shared/components/layout'
import { Button } from '@/shared/components/ui/button'

/**
 * NavigationActions Component
 *
 * Actions displayed in the navigation bar:
 * - Theme toggle (light/dark/system)
 * - User menu button
 */
export function NavigationActions() {
  return (
    <div className="flex items-center gap-2">
      <ThemeToggle />
      <Button
        variant="ghost"
        size="icon"
        aria-label="User menu"
        className="transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <User className="h-5 w-5" />
      </Button>
    </div>
  )
}

import { NavigationActions } from './NavigationActions'
import { NavigationLinks } from './NavigationLinks'

/**
 * Navigation Component
 *
 * Main navigation bar with:
 * - SkillForge branding and links
 * - Theme toggle and user actions
 *
 * Sticky at top, responsive design
 */
export function Navigation() {
  return (
    <nav
      className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <NavigationLinks />
          <NavigationActions />
        </div>
      </div>
    </nav>
  )
}

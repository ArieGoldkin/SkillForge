import { Link } from '@tanstack/react-router'
import { GraduationCap } from 'lucide-react'

/**
 * NavigationLinks Component
 *
 * Primary navigation links:
 * - SkillForge branding (home link)
 * - Main navigation items (Home, Library, About)
 *
 * Responsive: Navigation items hidden on mobile (shown via menu button)
 */
export function NavigationLinks() {
  return (
    <div className="flex items-center gap-6 lg:gap-8">
      <Link
        to="/"
        className="flex items-center gap-2 text-xl font-bold text-primary transition-colors hover:text-primary/80 lg:text-2xl"
        aria-label="SkillForge home"
      >
        <GraduationCap className="h-7 w-7 lg:h-8 lg:w-8" />
        <span>SkillForge</span>
      </Link>

      <div className="hidden gap-4 md:flex lg:gap-6">
        <Link
          to="/"
          className="relative font-medium text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm px-2 py-1"
          activeProps={{
            className: 'text-primary',
          }}
        >
          Home
        </Link>
        <Link
          to="/library"
          className="relative font-medium text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm px-2 py-1"
          activeProps={{
            className: 'text-primary',
          }}
        >
          Library
        </Link>
        <a
          href="#about"
          className="relative font-medium text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm px-2 py-1"
        >
          About
        </a>
      </div>
    </div>
  )
}

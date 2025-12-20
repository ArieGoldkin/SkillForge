import { Link } from '@tanstack/react-router'
import { GraduationCap } from 'lucide-react'

import { ExternalNavLink, NavLink } from './NavLink'

/**
 * NavigationLinks - Primary navigation links for SkillForge.
 * Includes branding and main nav items. Hidden on mobile (shown via menu).
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
        <NavLink to="/">Home</NavLink>
        <NavLink to="/library">Library</NavLink>
        <ExternalNavLink href="#about">About</ExternalNavLink>
        <NavLink to="/showcase" badge="DEV">
          Showcase
        </NavLink>
        <NavLink to="/annotation-queue" badge="ADMIN">
          Review Queue
        </NavLink>
      </div>
    </div>
  )
}

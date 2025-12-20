/**
 * NavLink - Reusable navigation link with consistent styling.
 */

import type { ReactNode } from 'react'

import { Link } from '@tanstack/react-router'

interface NavLinkProps {
  to: string
  children: ReactNode
  badge?: string
}

const linkClass =
  'relative font-medium text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm px-2 py-1'

export function NavLink({ to, children, badge }: NavLinkProps) {
  return (
    <Link to={to} className={linkClass} activeProps={{ className: 'text-primary' }}>
      {children}
      {badge && <span className="ml-1 text-xs align-super opacity-60">{badge}</span>}
    </Link>
  )
}

export function ExternalNavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} className={linkClass}>
      {children}
    </a>
  )
}

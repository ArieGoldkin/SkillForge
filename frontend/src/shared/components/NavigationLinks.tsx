import { Link } from '@tanstack/react-router'
import { GraduationCap } from 'lucide-react'

export function NavigationLinks() {
  return (
    <div className="flex items-center gap-8">
      <Link to="/" className="flex items-center gap-2 text-2xl font-bold text-primary">
        <GraduationCap className="h-8 w-8" />
        <span>SkillForge</span>
      </Link>

      <div className="hidden gap-6 md:flex">
        <Link
          to="/"
          className="nav-link relative font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          Home
        </Link>
        <Link
          to="/library"
          className="nav-link relative font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          Library
        </Link>
        <a
          href="#"
          className="nav-link relative font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          About
        </a>
      </div>
    </div>
  )
}

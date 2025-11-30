import { Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'

interface BackLinkProps {
  analysisId?: string
  artifactId?: string
  className?: string
}

export function BackLink({ analysisId, artifactId, className = 'mb-6' }: BackLinkProps) {
  const linkClass = `inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors ${className}`

  if (analysisId) {
    return (
      <Link
        to="/analyze/$id"
        params={{ id: analysisId }}
        search={{ completed: true, artifactId }}
        className={linkClass}
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Analysis</span>
      </Link>
    )
  }

  return (
    <Link to="/" className={linkClass}>
      <ArrowLeft className="h-4 w-4" />
      <span>Back to Home</span>
    </Link>
  )
}

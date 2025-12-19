import { Link } from '@tanstack/react-router'
import { ArrowRight, FileText } from 'lucide-react'

import { Button } from '@shared/components/ui/button'

import { cn } from '@lib/utils'

interface GuideButtonProps {
  artifactId: string
  analysisId?: string
  traceId?: string
  isCompact?: boolean
}

export function GuideButton({
  artifactId,
  analysisId,
  traceId,
  isCompact = false,
}: GuideButtonProps) {
  return (
    <Link
      to="/artifact/$artifactId"
      params={{ artifactId }}
      search={{ analysisId: analysisId || undefined }}
      state={{ traceId }}
    >
      <Button size={isCompact ? 'default' : 'lg'} className="gap-2">
        <FileText className={cn(isCompact ? 'h-4 w-4' : 'h-5 w-5')} />
        View Guide
        <ArrowRight className="h-4 w-4" />
      </Button>
    </Link>
  )
}

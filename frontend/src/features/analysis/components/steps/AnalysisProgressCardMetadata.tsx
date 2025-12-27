import { FileText, Github, Video } from 'lucide-react'

import { UI_CONSTANTS } from '@/lib/constants'

import { Badge } from '@shared/components/ui/badge'

import { cn } from '@lib/utils'

/**
 * Content type configuration
 */
const CONTENT_TYPE_CONFIG = {
  article: {
    icon: FileText,
    label: 'Article',
    color: UI_CONSTANTS.STATUS_STYLE_INFO,
  },
  video: {
    icon: Video,
    label: 'Video',
    color: UI_CONSTANTS.STATUS_STYLE_ERROR,
  },
  repo: {
    icon: Github,
    label: 'Repository',
    color: UI_CONSTANTS.STATUS_STYLE_WARNING,
  },
} as const

interface AnalysisProgressCardMetadataProps {
  contentType?: 'article' | 'video' | 'repo'
  wordCount?: number
}

/**
 * Metadata section for analysis progress card
 * Shows content type and word count
 */
export function AnalysisProgressCardMetadata({
  contentType,
  wordCount,
}: AnalysisProgressCardMetadataProps) {
  if (!contentType && wordCount === undefined) {
    return null
  }

  const contentTypeConfig = contentType ? CONTENT_TYPE_CONFIG[contentType] : null
  const ContentIcon = contentTypeConfig?.icon

  return (
    <div className="rounded-md bg-muted/50 border border-border p-3 space-y-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        Content Information
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {contentTypeConfig && ContentIcon && (
          <Badge
            variant="outline"
            className={cn('flex items-center gap-1.5 text-xs', contentTypeConfig.color)}
          >
            <ContentIcon className="h-3 w-3" />
            {contentTypeConfig.label}
          </Badge>
        )}
        {wordCount !== undefined && wordCount > 0 && (
          <span className="text-xs text-muted-foreground">{wordCount.toLocaleString()} words</span>
        )}
      </div>
    </div>
  )
}

import { FileText, Github, Video } from 'lucide-react'

import { GoldenDatasetBadge } from '@features/artifact/components/internal/GoldenDatasetBadge'
import { isGoldenDatasetUrl, extractDocumentName } from '@features/artifact/utils/urlHelpers'

import { Badge } from '@shared/components/ui/badge'

import { cn } from '@lib/utils'

interface AnalysisHeaderProps {
  title?: string | null
  url?: string
  contentType?: 'article' | 'video' | 'repo'
  wordCount?: number
}

const CONTENT_TYPE_CONFIG = {
  article: {
    icon: FileText,
    label: 'Article',
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  },
  video: {
    icon: Video,
    label: 'Video',
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
  },
  repo: {
    icon: Github,
    label: 'Repository',
    color: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  },
} as const

export function AnalysisHeader({ title, url, contentType, wordCount }: AnalysisHeaderProps) {
  const isGoldenDataset = url ? isGoldenDatasetUrl(url) : false
  const documentName = isGoldenDataset && url ? extractDocumentName(url) : undefined
  const contentTypeConfig = contentType ? CONTENT_TYPE_CONFIG[contentType] : null
  const ContentIcon = contentTypeConfig?.icon

  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-3xl font-bold">{title || 'Content Analysis'}</h1>
        {contentTypeConfig && ContentIcon && (
          <Badge
            variant="outline"
            className={cn('flex items-center gap-1.5', contentTypeConfig.color)}
          >
            <ContentIcon className="h-3.5 w-3.5" />
            {contentTypeConfig.label}
          </Badge>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        {isGoldenDataset && documentName ? (
          <div className="flex items-center gap-2">
            <GoldenDatasetBadge documentName={documentName} />
            <span>Example content</span>
          </div>
        ) : url ? (
          <p className="truncate max-w-2xl">{url}</p>
        ) : null}
        {wordCount !== undefined && wordCount > 0 && (
          <span className="whitespace-nowrap">{wordCount.toLocaleString()} words</span>
        )}
      </div>
    </div>
  )
}

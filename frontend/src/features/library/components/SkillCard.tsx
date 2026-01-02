import type * as React from 'react'

import { usePrefetch } from '@hooks/usePrefetch'
import { Trash2 } from 'lucide-react'

import { Card, CardContent } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

import { FailedStageDetails } from './SkillCard/FailedStageDetails'
import { SkillCardMetadata } from './SkillCard/SkillCardMetadata'
import { SkillCardProgress } from './SkillCard/SkillCardProgress'
import { SkillCardTags } from './SkillCard/SkillCardTags'
import { SkillCardThumbnail } from './SkillCard/SkillCardThumbnail'
import type { SkillDifficulty, SkillStatus } from './SkillCard/types'

/**
 * Re-export types from types.ts
 */
export type { SkillDifficulty, SkillStatus } from './SkillCard/types'

/**
 * Props for SkillCard component
 */
export interface SkillCardProps {
  id: string
  title: string
  description: string
  difficulty: SkillDifficulty
  duration: number
  tags: string[]
  status: SkillStatus
  thumbnail?: string
  progress?: number
  onSelect: (id: string) => void
  onDelete?: (id: string) => void
  className?: string
  // Error tracking fields (for failed analyses)
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
  onRetry?: (analysisId: string, stage?: string) => void
}

/**
 * Format status label for ARIA
 */
const formatStatus = (status: SkillStatus): string => {
  const labels: Record<SkillStatus, string> = {
    'not-started': 'Not Started',
    'in-progress': 'In Progress',
    completed: 'Completed',
    failed: 'Failed',
  }
  return labels[status]
}

interface DeleteButtonProps {
  id: string
  onDelete: (id: string) => void
}

function DeleteButton({ id, onDelete }: DeleteButtonProps): React.ReactNode {
  return (
    <button
      type="button"
      className="absolute right-3 top-3 z-10 rounded-full bg-background/80 p-2 text-muted-foreground shadow-sm transition hover:text-destructive hover:bg-destructive/10"
      onClick={(event) => {
        event.stopPropagation()
        onDelete(id)
      }}
      aria-label="Delete analysis"
    >
      <Trash2 className="h-4 w-4" />
    </button>
  )
}

function SkillCardBody({
  id,
  title,
  description,
  difficulty,
  duration,
  tags,
  status,
  thumbnail,
  progress,
  onDelete,
  errorCode,
  errorMessage,
  failedAtStage,
  onRetry,
}: SkillCardProps): React.ReactNode {
  const isFailed = status === 'failed'

  return (
    <CardContent className="p-0 relative">
      {onDelete && <DeleteButton id={id} onDelete={onDelete} />}
      <SkillCardThumbnail title={title} thumbnail={thumbnail} />

      <div className="p-6 space-y-4">
        <h3 className="text-lg font-semibold line-clamp-2 group-hover:text-primary transition-colors">
          {title}
        </h3>

        <p className="text-sm text-muted-foreground line-clamp-2">{description}</p>

        <SkillCardMetadata difficulty={difficulty} duration={duration} status={status} />

        <SkillCardProgress status={status} progress={progress} />

        {/* Show error details for failed analyses */}
        {isFailed && (errorCode || errorMessage || failedAtStage) && (
          <FailedStageDetails
            errorCode={errorCode}
            errorMessage={errorMessage}
            failedAtStage={failedAtStage}
            analysisId={id}
            onRetry={onRetry}
            defaultExpanded={false}
          />
        )}

        <SkillCardTags tags={tags} />
      </div>
    </CardContent>
  )
}

/**
 * SkillCard - Individual skill/learning resource card
 */
// eslint-disable-next-line max-lines-per-function
export function SkillCard({
  id,
  title,
  description,
  difficulty,
  duration,
  tags,
  status,
  thumbnail,
  progress,
  onSelect,
  onDelete,
  className,
  errorCode,
  errorMessage,
  failedAtStage,
  onRetry,
}: SkillCardProps): React.ReactNode {
  const { prefetchAnalysis } = usePrefetch()

  const handleClick = () => {
    onSelect(id)
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(id)
    }
  }

  const handleMouseEnter = () => {
    // Prefetch analysis data on hover for instant navigation
    prefetchAnalysis(id)
  }

  const handleFocus = () => {
    // Prefetch on focus for keyboard navigation accessibility
    prefetchAnalysis(id)
  }

  return (
    <Card
      data-testid="analysis-card"
      className={cn(
        'group cursor-pointer transition-all hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={handleMouseEnter}
      onFocus={handleFocus}
      tabIndex={0}
      role="button"
      aria-label={`${title} - ${formatStatus(status)}`}
    >
      <SkillCardBody
        id={id}
        title={title}
        description={description}
        difficulty={difficulty}
        duration={duration}
        tags={tags}
        status={status}
        thumbnail={thumbnail}
        progress={progress}
        onSelect={onSelect}
        onDelete={onDelete}
        errorCode={errorCode}
        errorMessage={errorMessage}
        failedAtStage={failedAtStage}
        onRetry={onRetry}
      />
    </Card>
  )
}

SkillCard.displayName = 'SkillCard'

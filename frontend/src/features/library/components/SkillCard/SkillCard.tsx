/**
 * SkillCard - Main card component for displaying analysis items
 */

import type * as React from 'react'

import { Trash2 } from 'lucide-react'

import { Button } from '@shared/components/ui/button'
import { Card, CardContent, CardHeader } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

import { FailedStageDetails } from './FailedStageDetails'
import { SkillCardMetadata } from './SkillCardMetadata'
import { SkillCardTags } from './SkillCardTags'
import type { SkillDifficulty, SkillStatus } from './types'

export interface SkillCardProps {
  id: string
  title: string
  description: string
  difficulty: SkillDifficulty
  duration: number
  tags: string[]
  status: SkillStatus
  onSelect: (id: string) => void
  // Error tracking fields
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
  onRetry?: (analysisId: string, stage?: string) => void
  onDelete?: (id: string) => void
  className?: string
}

/**
 * SkillCard component
 *
 * Displays analysis information with support for:
 * - Click/keyboard selection
 * - Error display with retry functionality
 * - Delete functionality
 */
export function SkillCard({
  id,
  title,
  description,
  difficulty,
  duration,
  tags,
  status,
  onSelect,
  errorCode,
  errorMessage,
  failedAtStage,
  onRetry,
  onDelete,
  className,
}: SkillCardProps): React.ReactNode {
  const showErrorDetails = status === 'failed' && errorCode

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(id)
    }
  }

  const handleDeleteClick = (event: React.MouseEvent) => {
    event.stopPropagation()
    onDelete?.(id)
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect(id)}
      onKeyDown={handleKeyDown}
      className={cn(
        'cursor-pointer transition-all hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-lg line-clamp-2">{title}</h3>
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              aria-label="Delete analysis"
              onClick={handleDeleteClick}
              className="h-8 w-8 shrink-0"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">{description}</p>
      </CardHeader>

      <CardContent className="space-y-3">
        <SkillCardMetadata difficulty={difficulty} duration={duration} status={status} />
        <SkillCardTags tags={tags} />

        {showErrorDetails && (
          <FailedStageDetails
            analysisId={id}
            errorCode={errorCode}
            errorMessage={errorMessage}
            failedAtStage={failedAtStage}
            onRetry={onRetry}
          />
        )}
      </CardContent>
    </Card>
  )
}

SkillCard.displayName = 'SkillCard'

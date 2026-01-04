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
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
  onRetry?: (analysisId: string, stage?: string) => void
  onDelete?: (id: string) => void
  className?: string
}

interface SkillCardHeaderProps {
  title: string
  description: string
  onDelete?: () => void
}

function SkillCardHeaderContent({ title, description, onDelete }: SkillCardHeaderProps) {
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete?.()
  }

  return (
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
  )
}

export function SkillCard(props: SkillCardProps): React.ReactNode {
  const { id, title, description, difficulty, duration, tags, status, className } = props
  const { onSelect, errorCode, errorMessage, failedAtStage, onRetry, onDelete } = props

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect(id)
    }
  }

  const handleDeleteClick = onDelete
    ? () => {
        onDelete(id)
      }
    : undefined

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
      <SkillCardHeaderContent
        title={title}
        description={description}
        onDelete={handleDeleteClick}
      />
      <CardContent className="space-y-3">
        <SkillCardMetadata difficulty={difficulty} duration={duration} status={status} />
        <SkillCardTags tags={tags} />
        {status === 'failed' && errorCode && (
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

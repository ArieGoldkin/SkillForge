/**
 * SkillCardMetadata - Metadata badges for skill cards
 */

import type * as React from 'react'

import { Clock } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'

import type { SkillDifficulty, SkillStatus } from './types'

/**
 * Props for SkillCardMetadata component
 */
export interface SkillCardMetadataProps {
  difficulty: SkillDifficulty
  duration: number
  status: SkillStatus
}

/**
 * Get badge variant for difficulty level
 */
const getDifficultyVariant = (
  difficulty: SkillDifficulty
): 'success' | 'warning' | 'destructive' => {
  const variants: Record<SkillDifficulty, 'success' | 'warning' | 'destructive'> = {
    beginner: 'success',
    intermediate: 'warning',
    advanced: 'destructive',
  }
  return variants[difficulty]
}

/**
 * Get badge variant for status
 */
const getStatusVariant = (
  status: SkillStatus
): 'default' | 'warning' | 'success' | 'destructive' => {
  const variants: Record<SkillStatus, 'default' | 'warning' | 'success' | 'destructive'> = {
    'not-started': 'default',
    'in-progress': 'warning',
    completed: 'success',
    failed: 'destructive',
  }
  return variants[status]
}

/**
 * Format status label
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

/**
 * Format duration in minutes to human-readable string
 */
const formatDuration = (minutes: number): string => {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
}

/**
 * SkillCardMetadata component
 *
 * Displays difficulty, duration, and status badges.
 */
export function SkillCardMetadata({
  difficulty,
  duration,
  status,
}: SkillCardMetadataProps): React.ReactNode {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge variant={getDifficultyVariant(difficulty)} className="capitalize">
        {difficulty}
      </Badge>
      <Badge variant="outline" className="gap-1">
        <Clock className="h-3 w-3" />
        {formatDuration(duration)}
      </Badge>
      <Badge variant={getStatusVariant(status)}>{formatStatus(status)}</Badge>
    </div>
  )
}

SkillCardMetadata.displayName = 'SkillCardMetadata'

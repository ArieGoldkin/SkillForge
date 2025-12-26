/**
 * SkillCardProgress - Progress bar for skill cards
 */

import type * as React from 'react'

import { Progress } from '@shared/components/ui/progress'

import type { SkillStatus } from './types'

/**
 * Props for SkillCardProgress component
 */
export interface SkillCardProgressProps {
  status: SkillStatus
  progress?: number
}

/**
 * SkillCardProgress component
 *
 * Displays progress for in-progress skills.
 * For failed status, shows a clear failed indicator instead of a progress bar.
 */
export function SkillCardProgress({ status, progress }: SkillCardProgressProps): React.ReactNode {
  if (status === 'failed') {
    return (
      <div className="flex items-center justify-between text-xs text-destructive font-medium">
        <span>Failed</span>
        <span
          aria-label="Failed status"
          className="w-2 h-2 rounded-full bg-destructive inline-block"
        />
      </div>
    )
  }

  if (status !== 'in-progress' || progress === undefined) {
    return null
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">Progress</span>
        <span className="font-medium text-primary">{progress}%</span>
      </div>
      <Progress value={progress} className="h-1.5" />
    </div>
  )
}

SkillCardProgress.displayName = 'SkillCardProgress'

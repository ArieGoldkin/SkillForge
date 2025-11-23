/**
 * SkillCardProgress - Progress bar for skill cards
 */

import * as React from 'react'

import { Progress } from '@/components/ui/progress'

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
 * Displays progress bar for in-progress skills only.
 * Returns null for other statuses.
 */
export const SkillCardProgress: React.FC<SkillCardProgressProps> = ({ status, progress }) => {
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

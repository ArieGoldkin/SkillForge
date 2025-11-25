import type * as React from 'react'

import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Badge } from '@/shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Progress } from '@/shared/components/ui/progress'

/**
 * Analysis stage type representing the current processing state
 */
export type AnalysisStage = 'extracting' | 'processing' | 'analyzing' | 'generating' | 'complete'

/**
 * Props for AnalysisProgressCard component
 *
 * @property stage - Current analysis stage
 * @property progress - Progress percentage (0-100)
 * @property currentStep - Description of current step
 * @property totalSteps - Total number of steps in analysis
 * @property completedSteps - Number of completed steps
 * @property estimatedTimeRemaining - Optional time estimate (e.g., "2-3 minutes")
 */
export interface AnalysisProgressCardProps {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
  className?: string
}

/**
 * Get badge variant and label for each analysis stage
 */
const getStageConfig = (
  stage: AnalysisStage
): { variant: 'default' | 'success' | 'warning' | 'info'; label: string } => {
  const configs: Record<
    AnalysisStage,
    { variant: 'default' | 'success' | 'warning' | 'info'; label: string }
  > = {
    extracting: { variant: 'info', label: 'Extracting' },
    processing: { variant: 'warning', label: 'Processing' },
    analyzing: { variant: 'warning', label: 'Analyzing' },
    generating: { variant: 'info', label: 'Generating' },
    complete: { variant: 'success', label: 'Complete' },
  }
  return configs[stage]
}

/**
 * AnalysisProgressCard - Display current analysis stage with progress visualization
 *
 * Shows overall progress, current step description, and estimated completion time.
 * Uses teal accent for active progress and status badges.
 *
 * @example
 * ```tsx
 * <AnalysisProgressCard
 *   stage="analyzing"
 *   progress={60}
 *   currentStep="Multi-Agent Analysis"
 *   totalSteps={5}
 *   completedSteps={3}
 *   estimatedTimeRemaining="2-3 minutes"
 * />
 * ```
 */
/* eslint-disable max-lines-per-function -- Main component requires complete JSX layout for progress card (header with spinner, progress bar, step info, time estimate, completion message). Already well-structured. */
export const AnalysisProgressCard: React.FC<AnalysisProgressCardProps> = ({
  stage,
  progress,
  currentStep,
  totalSteps,
  completedSteps,
  estimatedTimeRemaining,
  className,
}) => {
  const stageConfig = getStageConfig(stage)
  const isComplete = stage === 'complete'
  const isActive = !isComplete

  return (
    <Card className={cn('animate-in fade-in-50 duration-300', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {isActive && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
            Overall Progress
          </CardTitle>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-primary">{progress}%</span>
            <Badge variant={stageConfig.variant}>{stageConfig.label}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <Progress
            value={progress}
            className="h-2"
            aria-label={`Analysis progress: ${progress}%`}
          />
        </div>

        {/* Current Step */}
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">{currentStep}</p>
          <p className="text-xs text-muted-foreground">
            Step {completedSteps} of {totalSteps}
          </p>
        </div>

        {/* Time Estimate */}
        {estimatedTimeRemaining && !isComplete && (
          <p className="text-sm text-muted-foreground">
            Estimated time remaining: {estimatedTimeRemaining}
          </p>
        )}

        {/* Completion Message */}
        {isComplete && (
          <p className="text-sm text-muted-foreground">
            Analysis complete! Review your results below.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

AnalysisProgressCard.displayName = 'AnalysisProgressCard'

import type * as React from 'react'

import { FileText, Github, Loader2, Video } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

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
 * @property contentType - Optional content type (article, video, repo)
 * @property wordCount - Optional word count
 * @property hasFailedStages - Whether any stages have failed
 * @property failedStagesCount - Number of failed stages
 */
export interface AnalysisProgressCardProps {
  stage: AnalysisStage
  progress: number
  currentStep: string
  totalSteps: number
  completedSteps: number
  estimatedTimeRemaining?: string
  contentType?: 'article' | 'video' | 'repo'
  wordCount?: number
  hasFailedStages?: boolean
  failedStagesCount?: number
  className?: string
}

/**
 * Get badge variant and label for each analysis stage
 * @param stage - Analysis stage
 * @param hasFailures - Whether there are any failed stages
 */
const getStageConfig = (
  stage: AnalysisStage,
  hasFailures: boolean = false
): { variant: 'default' | 'success' | 'warning' | 'info' | 'destructive'; label: string } => {
  const configs: Record<
    AnalysisStage,
    { variant: 'default' | 'success' | 'warning' | 'info' | 'destructive'; label: string }
  > = {
    extracting: { variant: 'info', label: 'Extracting' },
    processing: { variant: 'warning', label: 'Processing' },
    analyzing: { variant: 'warning', label: 'Analyzing' },
    generating: { variant: 'info', label: 'Generating' },
    complete: { variant: 'success', label: 'Complete' },
  }

  // Override complete status if there are failures
  if (stage === 'complete' && hasFailures) {
    return { variant: 'destructive', label: 'Complete with Errors' }
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
/* eslint-disable max-lines-per-function, complexity -- Main component requires complete JSX layout for progress card (header with spinner, progress bar, step info, time estimate, completion message, error summary). Multiple conditional branches for content type, completion states, and error handling. Already well-structured. */
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

export const AnalysisProgressCard: React.FC<AnalysisProgressCardProps> = ({
  stage,
  progress,
  currentStep,
  totalSteps,
  completedSteps,
  estimatedTimeRemaining,
  contentType,
  wordCount,
  hasFailedStages = false,
  failedStagesCount = 0,
  className,
}) => {
  const stageConfig = getStageConfig(stage, hasFailedStages)
  const isComplete = stage === 'complete'
  const isActive = !isComplete
  const contentTypeConfig = contentType ? CONTENT_TYPE_CONFIG[contentType] : null
  const ContentIcon = contentTypeConfig?.icon

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
        {/* Metadata Section */}
        {(contentType || wordCount !== undefined) && (
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
                <span className="text-xs text-muted-foreground">
                  {wordCount.toLocaleString()} words
                </span>
              )}
            </div>
          </div>
        )}
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
        {isComplete && !hasFailedStages && (
          <p className="text-sm text-muted-foreground">
            Analysis complete! Review your results below.
          </p>
        )}

        {/* Error Summary */}
        {isComplete && hasFailedStages && (
          <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <p className="text-sm font-medium text-destructive">
                  {failedStagesCount} {failedStagesCount === 1 ? 'stage' : 'stages'} failed
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  The analysis completed but encountered errors. Check the stages below for details.
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

AnalysisProgressCard.displayName = 'AnalysisProgressCard'

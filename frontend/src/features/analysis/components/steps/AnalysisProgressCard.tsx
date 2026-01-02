import { memo } from 'react'

import { type VariantProps, cva } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'

import { Badge } from '@shared/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'
import { Progress } from '@shared/components/ui/progress'

import { cn } from '@lib/utils'

import { AnalysisProgressCardErrorSummary } from './AnalysisProgressCardErrorSummary'
import { AnalysisProgressCardMetadata } from './AnalysisProgressCardMetadata'

export type AnalysisStage = 'extracting' | 'processing' | 'analyzing' | 'generating' | 'complete'
type AnalysisCardStatus = 'analyzing' | 'complete' | 'complete-with-errors'
type BadgeVariant = 'default' | 'success' | 'warning' | 'info' | 'destructive'

const analysisCardVariants = cva('animate-in fade-in-50 duration-300', {
  variants: {
    status: { analyzing: '', complete: '', 'complete-with-errors': '' },
  },
  defaultVariants: { status: 'analyzing' },
})

export interface AnalysisProgressCardProps extends VariantProps<typeof analysisCardVariants> {
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
  failedStageErrorCodes?: string[]
  className?: string
}

const STAGE_BADGE_CONFIG: Record<AnalysisStage, { variant: BadgeVariant; label: string }> = {
  extracting: { variant: 'info', label: 'Extracting' },
  processing: { variant: 'warning', label: 'Processing' },
  analyzing: { variant: 'warning', label: 'Analyzing' },
  generating: { variant: 'info', label: 'Generating' },
  complete: { variant: 'success', label: 'Complete' },
}

const getStageConfig = (stage: AnalysisStage, hasFailures = false) => {
  if (stage === 'complete' && hasFailures) {
    return { variant: 'destructive' as const, label: 'Completed with Errors' }
  }
  return STAGE_BADGE_CONFIG[stage]
}

/**
 * Display current analysis stage with progress visualization.
 * Issue #433: Refactored to use CVA variants for status styling (2025 best practice)
 */
/* eslint-disable max-lines-per-function -- Component requires complete card layout with multiple conditional sections */
export const AnalysisProgressCard = memo(function AnalysisProgressCard({
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
  failedStageErrorCodes = [],
  className,
}: AnalysisProgressCardProps) {
  const stageConfig = getStageConfig(stage, hasFailedStages)
  const isComplete = stage === 'complete'
  const isActive = !isComplete
  const status: AnalysisCardStatus =
    stage === 'complete' ? (hasFailedStages ? 'complete-with-errors' : 'complete') : 'analyzing'

  return (
    <Card className={cn(analysisCardVariants({ status }), className)}>
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
        <AnalysisProgressCardMetadata contentType={contentType} wordCount={wordCount} />
        <Progress
          value={progress}
          className="h-2"
          aria-label="Analysis progress"
          aria-valuetext={`${progress}% complete - ${currentStep}`}
        />
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">{currentStep}</p>
          <p className="text-xs text-muted-foreground">
            Step {completedSteps} of {totalSteps}
          </p>
        </div>
        {estimatedTimeRemaining && !isComplete && (
          <p className="text-sm text-muted-foreground">
            Estimated time remaining: {estimatedTimeRemaining}
          </p>
        )}
        {isComplete && !hasFailedStages && (
          <p className="text-sm text-muted-foreground">
            Analysis complete! Review your results below.
          </p>
        )}
        {isComplete && hasFailedStages && (
          <AnalysisProgressCardErrorSummary
            failedStagesCount={failedStagesCount}
            failedStageErrorCodes={failedStageErrorCodes}
          />
        )}
      </CardContent>
    </Card>
  )
})

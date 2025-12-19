import type * as React from 'react'
import { useMemo } from 'react'

import type { AgentStageName } from '@app-types/sse'
import { useSSE } from '@hooks/useSSE'

import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

import { cn } from '@lib/utils'

import { CompletionMessage } from './CompletionMessage'
import { ConnectionStatus } from './ConnectionStatus'
import { ALL_STAGES } from './constants'
import { deriveStageStates } from './deriveStageStates'
import { ErrorAlert } from './ErrorAlert'
import { ReconnectingMessage } from './ReconnectingMessage'
import { StageItem } from './StageItem'

/**
 * Props for ProgressTracker component
 */
export interface ProgressTrackerProps {
  /** Analysis ID to connect to SSE stream */
  analysisId: string
  /** Optional CSS class name */
  className?: string
  /** Stages to display (default: ALL_STAGES) */
  stages?: AgentStageName[]
  /** Callback when analysis completes with artifact ID */
  onComplete?: (artifactId: string) => void
  /** Callback when an error occurs */
  onError?: (error: string) => void
}

/**
 * ProgressTracker - Real-time analysis progress visualization
 *
 * @example
 * ```tsx
 * <ProgressTracker analysisId="abc-123" />
 * <ProgressTracker analysisId="abc-123" stages={WORKING_STAGES} />
 * ```
 */
export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  analysisId,
  className,
  stages = ALL_STAGES,
  onComplete,
  onError,
}) => {
  const { events, error, isConnected, isComplete } = useSSE(analysisId)

  const stageStates = useMemo(
    () => deriveStageStates(stages, events, onComplete, onError),
    [stages, events, onComplete, onError]
  )

  const showReconnecting = !isConnected && !isComplete && !error

  return (
    <Card className={cn('animate-in fade-in-50 duration-300', className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">Analysis Progress</CardTitle>
          <ConnectionStatus isConnected={isConnected} />
        </div>
      </CardHeader>
      <CardContent>
        {error && <ErrorAlert message={error.message} />}
        {showReconnecting && <ReconnectingMessage />}
        <div
          className="space-y-0 max-h-[500px] overflow-y-auto"
          role="list"
          aria-label="Analysis stages"
        >
          {stageStates.map((stage, index) => (
            <StageItem key={stage.name} stage={stage} isLast={index === stageStates.length - 1} />
          ))}
        </div>
        {isComplete && <CompletionMessage />}
      </CardContent>
    </Card>
  )
}

ProgressTracker.displayName = 'ProgressTracker'

import type { StageName, SSEEvent } from '@app-types/sse'
import { isCompleteEvent, isErrorEvent, isProgressEvent } from '@app-types/sse'

import { createInitialStages, type StageState } from './constants'
import { normalizeSSEEvent } from './sseNormalizer'

/** Handle progress event updates */
function handleProgressEvent(
  event: SSEEvent,
  stages: StageName[],
  stageStates: StageState[]
): void {
  if (!isProgressEvent(event)) return
  if (!stages.includes(event.stage as StageName)) return

  const stageIndex = stageStates.findIndex((s) => s.name === event.stage)
  if (stageIndex === -1) return

  stageStates[stageIndex] = {
    ...stageStates[stageIndex],
    status: event.status,
    agent: event.details?.agent as string | undefined,
    timestamp: event.timestamp,
  }
}

/** Handle error event updates */
function handleErrorEvent(
  event: SSEEvent,
  stageStates: StageState[],
  onError?: (error: string) => void
): void {
  if (!isErrorEvent(event)) return

  const stageName = event.stage as StageName
  const stageIndex = stageStates.findIndex((s) => s.name === stageName)
  if (stageIndex !== -1) {
    stageStates[stageIndex] = {
      ...stageStates[stageIndex],
      status: 'failed',
      error: event.details?.error,
    }
  }
  if (event.details?.error) {
    onError?.(event.details.error)
  }
}

/**
 * Derive stage states from SSE events
 * Processes raw events to compute current state for each stage
 */
export function deriveStageStates(
  stages: StageName[],
  events: unknown[],
  onComplete?: (artifactId: string) => void,
  onError?: (error: string) => void
): StageState[] {
  const stageStates = createInitialStages(stages)

  for (const rawEvent of events) {
    const event = normalizeSSEEvent(rawEvent)
    if (!event) continue

    handleProgressEvent(event, stages, stageStates)

    if (isCompleteEvent(event) && event.artifact_id) {
      onComplete?.(event.artifact_id)
    }

    handleErrorEvent(event, stageStates, onError)
  }

  return stageStates
}

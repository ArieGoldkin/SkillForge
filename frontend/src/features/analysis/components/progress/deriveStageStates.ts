import type { AgentStageName } from '@app-types/sse'
import { isCompleteEvent, isErrorEvent, isProgressEvent } from '@app-types/sse'

import { createInitialStages, type StageState } from './constants'
import { normalizeSSEEvent } from './sseNormalizer'

/**
 * Derive stage states from SSE events
 * Processes raw events to compute current state for each stage
 */
export function deriveStageStates(
  stages: AgentStageName[],
  events: unknown[],
  onComplete?: (artifactId: string) => void,
  onError?: (error: string) => void
): StageState[] {
  const stageStates = createInitialStages(stages)

  for (const rawEvent of events) {
    const event = normalizeSSEEvent(rawEvent)
    if (!event) continue

    if (isProgressEvent(event) && stages.includes(event.stage as AgentStageName)) {
      const stageIndex = stageStates.findIndex((s) => s.name === event.stage)
      if (stageIndex !== -1) {
        stageStates[stageIndex] = {
          ...stageStates[stageIndex],
          status: event.status,
          agent: event.details?.agent as string | undefined,
          timestamp: event.timestamp,
        }
      }
    }

    if (isCompleteEvent(event) && event.artifact_id) {
      onComplete?.(event.artifact_id)
    }

    if (isErrorEvent(event)) {
      const stageName = event.stage as AgentStageName
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
  }

  return stageStates
}

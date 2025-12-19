/**
 * useActivityFeed - Extract activity feed from SSE events
 *
 * Transforms raw SSE events into agent activity entries for display in the activity feed.
 * Filters for progress and complete events, maps them to AgentActivity objects,
 * and returns them in reverse chronological order.
 *
 * @module features/analysis/hooks/useActivityFeed
 */
import { useMemo } from 'react'

import { isProgressEvent, isCompleteEvent } from '@/schemas/sse'
import type { SSEEvent } from '@/schemas/sse'

import { normalizeStageNameFromBackend, isAgentStage } from './stageConfig'
import { getAgentName, getActionDescription } from './stageHelpers'

/**
 * Individual agent activity entry
 */
export interface AgentActivity {
  id: string
  agentName: string
  action: string
  timestamp: Date
}

/**
 * Transform SSE events into agent activity feed entries
 *
 * Filters events for progress and complete events, extracts agent name and action
 * descriptions, and returns activities in reverse chronological order (newest first).
 *
 * @param events - Raw SSE events from the analysis stream
 * @returns Array of agent activities sorted by timestamp (newest first)
 *
 * @example
 * ```tsx
 * const activities = useActivityFeed(events)
 * // Returns:
 * // [
 * //   { id: 'tech_comparison-5', agentName: 'Tech Comparator', action: 'Comparing technology patterns...', timestamp: Date },
 * //   { id: 'extraction-0', agentName: 'Content Extractor', action: 'Extracted 1500 words from content', timestamp: Date }
 * // ]
 * ```
 */
export function useActivityFeed(events: SSEEvent[]): AgentActivity[] {
  return useMemo(() => {
    return events
      .filter((e) => isProgressEvent(e) || isCompleteEvent(e))
      .map((event, index) => {
        const stage = normalizeStageNameFromBackend(event.stage)
        const isAgent = stage && isAgentStage(stage)

        // Guard against invalid timestamps
        const timestamp = event.timestamp ? new Date(event.timestamp) : new Date()
        const isValidDate = timestamp instanceof Date && !isNaN(timestamp.getTime())

        return {
          id: `${event.stage ?? 'unknown'}-${index}`,
          agentName: isAgent ? getAgentName(stage, event.details) : (event.stage ?? 'Unknown'),
          action: isAgent
            ? getActionDescription(stage, event.status, event.details)
            : (event.status ?? 'Processing'),
          timestamp: isValidDate ? timestamp : new Date(),
        }
      })
      .reverse()
  }, [events])
}

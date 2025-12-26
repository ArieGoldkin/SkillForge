import { useCallback, useEffect, useMemo, useState } from 'react'

import type {
  AnalysisProgressResponse,
  AnalysisStatus,
  AnalysisStatusResponse,
} from '@app-types/api'

import type { SSEEvent } from '@/schemas/sse'

import { analyzeAPI } from '@services/api.service'

export const IDLE_RECHECK_MS = 15000

/**
 * Convert API progress events to SSE event format
 * Allows reusing existing SSE event processing logic for completed analyses
 */
function convertProgressEventsToSSE(progressResponse: AnalysisProgressResponse): SSEEvent[] {
  return progressResponse.events.map((event) => {
    // Ensure progress_data is an object before spreading
    const progressData =
      event.progress_data && typeof event.progress_data === 'object' ? event.progress_data : null

    return {
      type: 'progress' as const,
      analysis_id: progressResponse.analysis_id,
      stage: event.stage as SSEEvent['stage'],
      status: event.status as SSEEvent['status'],
      timestamp: event.timestamp,
      details: progressData || undefined,
      // Map common progress_data fields to top-level SSE fields
      ...(progressData &&
        'analysis_metadata' in progressData && {
          analysis_metadata: progressData.analysis_metadata,
        }),
      ...(progressData &&
        'artifact_id' in progressData && {
          artifact_id: progressData.artifact_id as string,
        }),
      ...(progressData &&
        'trace_id' in progressData && {
          trace_id: progressData.trace_id as string,
        }),
    } as SSEEvent
  })
}

interface SSEState {
  eventsLength: number
  isComplete: boolean
  artifactId?: string
}

interface UseAnalysisStatusParams {
  analysisId?: string
  completedParam?: boolean
  sseState: SSEState
}

interface AnalysisStatusResult {
  resolvedStatus?: AnalysisStatus
  resolvedArtifactId?: string
  shouldConnect: boolean
  loading: boolean
  statusError?: string
  refetch: () => Promise<void>
  progressEvents: SSEEvent[]
}

const useStatusRequest = (analysisId?: string, completedParam?: boolean) => {
  const [statusData, setStatusData] = useState<AnalysisStatusResponse | null>(null)
  const [statusError, setStatusError] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)
  const [progressEvents, setProgressEvents] = useState<SSEEvent[]>([])

  const fetchStatus = useCallback(async () => {
    if (!analysisId) return
    setLoading(true)
    try {
      const data = await analyzeAPI.getAnalysisStatus(analysisId)
      setStatusData(data)
      setStatusError(undefined)

      // If analysis is completed, fetch progress events from database
      // This allows displaying stage progress for already-completed analyses
      if (completedParam || data.status === 'complete') {
        try {
          const progressData = await analyzeAPI.getAnalysisProgress(analysisId)
          const sseEvents = convertProgressEventsToSSE(progressData)
          setProgressEvents(sseEvents)
        } catch (progressError) {
          // Log but don't fail - progress events are nice-to-have
          console.warn('Failed to fetch progress events:', progressError)
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch analysis status'
      setStatusError(message)
    } finally {
      setLoading(false)
    }
  }, [analysisId, completedParam])

  useEffect(() => {
    void fetchStatus()
  }, [fetchStatus])

  return { statusData, statusError, loading, refetch: fetchStatus, progressEvents }
}

const useIdleRecheck = (
  analysisId: string | undefined,
  isComplete: boolean,
  eventsLength: number,
  refetch: () => Promise<void>
) => {
  // biome-ignore lint/correctness/useExhaustiveDependencies: re-fetch when SSE goes idle; eventsLength intentionally included
  useEffect(() => {
    if (!analysisId) return
    if (isComplete) return
    const timer = setTimeout(() => {
      void refetch()
    }, IDLE_RECHECK_MS)
    return () => clearTimeout(timer)
  }, [analysisId, isComplete, eventsLength, refetch])
}

export function useAnalysisStatus({
  analysisId,
  completedParam,
  sseState,
}: UseAnalysisStatusParams): AnalysisStatusResult {
  const { statusData, statusError, loading, refetch, progressEvents } = useStatusRequest(
    analysisId,
    completedParam
  )
  useIdleRecheck(analysisId, sseState.isComplete, sseState.eventsLength, refetch)

  const resolvedStatus: AnalysisStatus | undefined = useMemo(() => {
    if (statusData?.status) return statusData.status
    if (sseState.isComplete) return 'complete'
    return undefined
  }, [statusData, sseState.isComplete])

  const resolvedArtifactId = useMemo(
    () => sseState.artifactId || statusData?.artifact_id || undefined,
    [sseState.artifactId, statusData?.artifact_id]
  )

  // Don't connect SSE if analysis is complete or failed
  const isCompleteOrFailed = useMemo(() => {
    if (!resolvedStatus) return false
    return (
      resolvedStatus === 'complete' ||
      resolvedStatus === 'failed' ||
      resolvedStatus === 'extraction_failed' ||
      resolvedStatus === 'analysis_failed' ||
      resolvedStatus === 'artifact_failed' ||
      resolvedStatus === 'quality_gate_failed' ||
      resolvedStatus === 'cancelled'
    )
  }, [resolvedStatus])

  const shouldConnect = Boolean(analysisId && !completedParam && !isCompleteOrFailed)

  return {
    resolvedStatus,
    resolvedArtifactId,
    shouldConnect,
    loading,
    statusError,
    refetch,
    progressEvents,
  }
}

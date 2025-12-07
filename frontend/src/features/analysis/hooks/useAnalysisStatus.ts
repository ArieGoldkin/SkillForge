import { useCallback, useEffect, useMemo, useState } from 'react'

import type { AnalysisStatus, AnalysisStatusResponse } from '@app-types/api'
import { analyzeAPI } from '@services/api.service'

export const IDLE_RECHECK_MS = 15000

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
}

export function useAnalysisStatus({
  analysisId,
  completedParam,
  sseState,
}: UseAnalysisStatusParams): AnalysisStatusResult {
  const [statusData, setStatusData] = useState<AnalysisStatusResponse | null>(null)
  const [statusError, setStatusError] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const fetchStatus = useCallback(async () => {
    if (!analysisId) return
    setLoading(true)
    try {
      const data = await analyzeAPI.getAnalysisStatus(analysisId)
      setStatusData(data)
      setStatusError(undefined)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch analysis status'
      setStatusError(message)
    } finally {
      setLoading(false)
    }
  }, [analysisId])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  useEffect(() => {
    if (!analysisId) return
    if (sseState.isComplete) return
    const timer = setTimeout(() => {
      fetchStatus()
    }, IDLE_RECHECK_MS)
    return () => clearTimeout(timer)
  }, [analysisId, fetchStatus, sseState.eventsLength, sseState.isComplete])

  const resolvedStatus: AnalysisStatus | undefined = useMemo(() => {
    if (statusData?.status) return statusData.status
    if (sseState.isComplete) return 'complete'
    return undefined
  }, [statusData, sseState.isComplete])

  const resolvedArtifactId = useMemo(
    () => sseState.artifactId || statusData?.artifact_id || undefined,
    [sseState.artifactId, statusData?.artifact_id]
  )

  const shouldConnect = Boolean(
    analysisId && !completedParam && resolvedStatus !== 'complete' && resolvedStatus !== 'failed'
  )

  return {
    resolvedStatus,
    resolvedArtifactId,
    shouldConnect,
    loading,
    statusError,
    refetch: fetchStatus,
  }
}

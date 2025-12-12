import { useEffect, useMemo } from 'react'

import { useSSEStore } from '@stores/sseStore'
import { getRouteApi } from '@tanstack/react-router'

import {
  ActivityColumn,
  AnalysisCompleteCard,
  AnalysisHeader,
  ErrorAlert,
  LoadingState,
  ProgressColumn,
} from './components'
import { CompletedAnalysisView } from './components/states/CompletedAnalysisView'
import { useAnalysisProgress } from './hooks/useAnalysisProgress'
import { useAnalysisStatus } from './hooks/useAnalysisStatus'

const routeApi = getRouteApi('/analyze/$id')

const useSSELifecycle = ({
  analysisId,
  shouldConnect,
  connect,
  disconnect,
  reset,
}: {
  analysisId?: string
  shouldConnect: boolean
  connect: (id: string) => void
  disconnect: () => void
  reset: () => void
}) => {
  useEffect(() => {
    if (shouldConnect && analysisId) {
      reset()
      connect(analysisId)
    } else {
      disconnect()
    }
    return () => disconnect()
  }, [analysisId, shouldConnect, connect, disconnect, reset])
}

// Check if status indicates completion (both 'complete' from SSE and 'completed' from backend)
const isStatusComplete = (status?: string) => status === 'completed' || status === 'complete'

// Check if we're still waiting for SSE events to start
const checkWaitingForFirstEvent = (params: {
  isResolvedComplete: boolean
  isFailed: boolean
  eventsLength: number
  error: Error | null
  isComplete: boolean
  statusLoading: boolean
  resolvedStatus?: string
}) =>
  !params.isResolvedComplete &&
  !params.isFailed &&
  params.eventsLength === 0 &&
  !params.error &&
  !params.isComplete &&
  (params.statusLoading || !params.resolvedStatus)

const useDerivedState = ({
  artifactId,
  urlArtifactId,
  statusState,
  isComplete,
  events,
  hasError,
  error,
  errorMessage,
  completed,
}: {
  artifactId?: string
  urlArtifactId?: string
  statusState: ReturnType<typeof useAnalysisStatus>
  isComplete: boolean
  events: unknown[]
  hasError: boolean
  error: Error | null
  errorMessage?: string | null
  completed?: boolean
}) => {
  const resolvedArtifactId = useMemo(
    () => artifactId || statusState.resolvedArtifactId || urlArtifactId,
    [artifactId, statusState.resolvedArtifactId, urlArtifactId]
  )

  const resolvedStatus = useMemo(
    () => statusState.resolvedStatus || (isComplete ? 'completed' : undefined),
    [isComplete, statusState.resolvedStatus]
  )

  const isResolvedComplete =
    (completed && Boolean(urlArtifactId)) || isStatusComplete(resolvedStatus) || isComplete
  const isFailed = resolvedStatus === 'failed' || hasError
  const effectiveError =
    statusState.statusError || errorMessage || error?.message || 'An error occurred during analysis'
  const waitingForFirstEvent = checkWaitingForFirstEvent({
    isResolvedComplete,
    isFailed,
    eventsLength: events.length,
    error,
    isComplete,
    statusLoading: statusState.loading,
    resolvedStatus: statusState.resolvedStatus,
  })

  return { resolvedArtifactId, isResolvedComplete, isFailed, waitingForFirstEvent, effectiveError }
}

// eslint-disable-next-line max-lines-per-function
export default function AnalyzeResult() {
  const { id } = routeApi.useParams()
  const { completed, artifactId: urlArtifactId } = routeApi.useSearch()
  const { events, isConnected, isComplete, error, connect, disconnect, reset } = useSSEStore()
  const { overallProgress, steps, activities, hasError, errorMessage, artifactId } =
    useAnalysisProgress(events)
  const statusState = useAnalysisStatus({
    analysisId: id,
    completedParam: Boolean(completed),
    sseState: { eventsLength: events.length, isComplete, artifactId },
  })

  useSSELifecycle({
    analysisId: id,
    shouldConnect: statusState.shouldConnect,
    connect,
    disconnect,
    reset,
  })

  const { resolvedArtifactId, isResolvedComplete, isFailed, waitingForFirstEvent, effectiveError } =
    useDerivedState({
      artifactId,
      urlArtifactId,
      statusState,
      isComplete,
      events,
      hasError,
      error,
      errorMessage,
      completed,
    })

  if (completed && urlArtifactId) {
    return <CompletedAnalysisView analysisId={id} artifactId={urlArtifactId} />
  }

  if (isResolvedComplete && resolvedArtifactId) {
    return <CompletedAnalysisView analysisId={id} artifactId={resolvedArtifactId} />
  }

  if (waitingForFirstEvent) {
    return <LoadingState />
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader title="Content Analysis" url={id ? `Analysis ID: ${id}` : ''} />

      {(error || hasError || statusState.statusError || isFailed) && (
        <ErrorAlert message={effectiveError} />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ProgressColumn overallProgress={overallProgress} steps={steps} />
        {isComplete || isResolvedComplete ? (
          <AnalysisCompleteCard
            artifactId={resolvedArtifactId || artifactId}
            analysisId={id}
            variant="column"
          />
        ) : (
          <ActivityColumn activities={activities} isLive={isConnected} />
        )}
      </div>
    </div>
  )
}

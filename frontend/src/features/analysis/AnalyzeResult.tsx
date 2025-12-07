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

  useEffect(() => {
    if (statusState.shouldConnect && id) {
      reset()
      connect(id)
    } else {
      disconnect()
    }
    return () => disconnect()
  }, [id, statusState.shouldConnect, connect, disconnect, reset])

  useEffect(() => {
    if (!statusState.resolvedStatus) return
    if (statusState.resolvedStatus === 'complete' || statusState.resolvedStatus === 'failed') {
      disconnect()
    }
  }, [statusState.resolvedStatus, disconnect])

  // Show completed state if navigating back from artifact page
  const resolvedArtifactId = useMemo(
    () => artifactId || statusState.resolvedArtifactId || urlArtifactId,
    [artifactId, statusState.resolvedArtifactId, urlArtifactId]
  )

  const resolvedStatus = useMemo(
    () => statusState.resolvedStatus || (isComplete ? 'complete' : undefined),
    [isComplete, statusState.resolvedStatus]
  )

  const isResolvedComplete =
    (completed && Boolean(urlArtifactId)) || resolvedStatus === 'complete' || isComplete

  const effectiveError =
    statusState.statusError || errorMessage || error?.message || 'An error occurred during analysis'

  const isFailed = resolvedStatus === 'failed' || hasError

  if (completed && urlArtifactId) {
    return <CompletedAnalysisView analysisId={id} artifactId={urlArtifactId} />
  }

  if (isResolvedComplete && resolvedArtifactId) {
    return <CompletedAnalysisView analysisId={id} artifactId={resolvedArtifactId} />
  }

  const waitingForFirstEvent =
    !isResolvedComplete &&
    !isFailed &&
    !isConnected &&
    events.length === 0 &&
    !error &&
    !isComplete &&
    (statusState.loading || !statusState.resolvedStatus)

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
        {isComplete ? (
          <AnalysisCompleteCard artifactId={artifactId} analysisId={id} variant="column" />
        ) : (
          <ActivityColumn activities={activities} isLive={isConnected} />
        )}
      </div>
    </div>
  )
}

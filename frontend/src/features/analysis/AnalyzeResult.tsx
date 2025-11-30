import { useEffect } from 'react'

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

const routeApi = getRouteApi('/analyze/$id')

export default function AnalyzeResult() {
  const { id } = routeApi.useParams()
  const { completed, artifactId: urlArtifactId } = routeApi.useSearch()
  const { events, isConnected, isComplete, error, connect, disconnect, reset } = useSSEStore()
  const { overallProgress, steps, activities, hasError, errorMessage, artifactId } =
    useAnalysisProgress(events)

  useEffect(() => {
    // Skip SSE connection if viewing completed analysis from URL
    if (id && !completed) {
      reset()
      connect(id)
    }
    return () => disconnect()
  }, [id, completed, connect, disconnect, reset])

  // Show completed state if navigating back from artifact page
  if (completed && urlArtifactId) {
    return <CompletedAnalysisView analysisId={id} artifactId={urlArtifactId} />
  }

  if (!isConnected && events.length === 0 && !error && !isComplete) {
    return <LoadingState />
  }

  const errorMsg = errorMessage || error?.message || 'An error occurred during analysis'

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader title="Content Analysis" url={id ? `Analysis ID: ${id}` : ''} />

      {(error || hasError) && <ErrorAlert message={errorMsg} />}

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

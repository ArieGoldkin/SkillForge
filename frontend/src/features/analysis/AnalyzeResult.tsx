import { useEffect } from 'react'

import { useSSEStore } from '@stores/sseStore'
import { useParams } from '@tanstack/react-router'

import { ActivityColumn, AnalysisHeader, LoadingState, ProgressColumn } from './components'
import { useAnalysisProgress } from './hooks/useAnalysisProgress'

export default function AnalyzeResult() {
  const { id } = useParams({ from: '/analyze/$id' })

  // SSE connection state
  const { events, isConnected, isComplete, error, connect, disconnect, reset } = useSSEStore()

  // Transform SSE events into UI-friendly data
  const { overallProgress, steps, activities, hasError, errorMessage } = useAnalysisProgress(events)

  // Connect to SSE on mount, disconnect on unmount
  useEffect(() => {
    if (id) {
      reset() // Clear previous analysis data
      connect(id)
    }

    return () => {
      disconnect()
    }
  }, [id, connect, disconnect, reset])

  // Show loading state while connecting and no events yet
  if (!isConnected && events.length === 0 && !error && !isComplete) {
    return <LoadingState />
  }

  // Generate title from URL or use placeholder
  const analysisTitle = 'Content Analysis'
  const analysisUrl = id ? `Analysis ID: ${id}` : ''

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader title={analysisTitle} url={analysisUrl} />

      {/* Error state */}
      {(error || hasError) && (
        <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
          <p className="text-destructive font-medium">
            {errorMessage || error?.message || 'An error occurred during analysis'}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ProgressColumn overallProgress={overallProgress} steps={steps} />
        <ActivityColumn activities={activities} isLive={isConnected && !isComplete} />
      </div>
    </div>
  )
}

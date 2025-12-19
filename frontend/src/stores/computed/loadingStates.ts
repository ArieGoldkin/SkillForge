/**
 * Computed Loading States for Issue #399
 *
 * Derives granular loading states from existing SSE events and connection state
 * without external middleware dependencies.
 */

import type { StageName } from '@app-types/sse'
import type { SSEStore } from '@stores/sseStoreHelpers'

import { ALL_STAGES, isWorkflowStage, getStageOrder } from '@features/analysis/config/stageRegistry'

import type { ComputedLoadingStates, LoadingState } from '@/types/loading'

/**
 * Check if we're in a disconnected state
 * Exported for testing
 */
export function isDisconnectedState(state: SSEStore): boolean {
  return !state.isConnected && !state.isComplete && !state.error && !state.connectionStartTime
}

/**
 * Check if we're waiting for first events
 * Exported for testing
 */
export function isWaitingForEventsState(state: SSEStore): boolean {
  return state.isConnected && state.events.length === 0
}

/**
 * Check if we're in timeout warning state
 * Exported for testing
 */
export function isTimeoutWarningState(state: SSEStore): boolean {
  if (!isWaitingForEventsState(state)) return false
  const connectedAt = state.connectionStartTime || Date.now()
  return Date.now() - connectedAt > 30000
}

/**
 * Check if we're in extracting state
 * Exported for testing
 */
export function isExtractingState(state: SSEStore): boolean {
  return state.latestEvent?.stage === 'extraction' && state.latestEvent?.status === 'running'
}

/**
 * Check if we're in analyzing state
 * Exported for testing
 */
export function isAnalyzingState(state: SSEStore): boolean {
  return state.latestEvent
    ? isAnalysisStage(state.latestEvent.stage) && state.latestEvent.status === 'running'
    : false
}

/**
 * Check if we're in generating state
 * Exported for testing
 */
export function isGeneratingState(state: SSEStore): boolean {
  return (
    state.latestEvent?.stage === 'artifact_generation' && state.latestEvent?.status === 'running'
  )
}

/**
 * Check if we're in complete state
 * Exported for testing
 */
export function isCompleteState(state: SSEStore): boolean {
  return state.isComplete && Boolean(state.artifactId)
}

/**
 * Check if we're in error state
 * Exported for testing
 */
export function isErrorState(state: SSEStore): boolean {
  return Boolean(state.error)
}

/**
 * Check if stage is an analysis stage (not extraction or generation)
 * Exported for testing
 */
export function isAnalysisStage(stage: string): boolean {
  // Analysis stages are everything between extraction and artifact generation
  const stageOrder = getStageOrder(stage as StageName)
  return stageOrder >= 4 && stageOrder <= 10 && !isWorkflowStage(stage as StageName)
}

/**
 * Calculate analysis progress based on completed stages
 * Exported for testing
 */
export function calculateAnalysisProgress(state: SSEStore): number {
  if (!state.latestEvent) return 0

  // Find completed stages
  const completedCount = state.events.filter((event) => event.status === 'complete').length

  const totalStages = ALL_STAGES.length

  return Math.round((completedCount / totalStages) * 100)
}

/**
 * Get connection-related loading state
 */
function getConnectionLoadingState(state: SSEStore): LoadingState | null {
  if (isDisconnectedState(state)) {
    return { type: 'disconnected' }
  }

  if (!state.isConnected && state.connectionStartTime && !state.isComplete && !state.error) {
    return { type: 'connecting', startTime: state.connectionStartTime }
  }

  if (isWaitingForEventsState(state)) {
    const connectedAt = state.connectionStartTime || Date.now()
    if (isTimeoutWarningState(state)) {
      return { type: 'timeout_warning', connectedAt }
    }
    return { type: 'waiting_for_events', connectedAt }
  }

  return null
}

/**
 * Get analysis-related loading state
 */
function getAnalysisLoadingState(state: SSEStore): LoadingState | null {
  if (isExtractingState(state)) {
    return {
      type: 'extracting',
      stage: state.latestEvent!.stage,
      wordCount: state.latestEvent!.details?.word_count,
    }
  }

  if (isAnalyzingState(state)) {
    const progress = calculateAnalysisProgress(state)
    return { type: 'analyzing', stage: state.latestEvent!.stage, progress }
  }

  if (isGeneratingState(state)) {
    return { type: 'generating', stage: state.latestEvent!.stage }
  }

  return null
}

/**
 * Get terminal loading state (complete/error)
 */
function getTerminalLoadingState(state: SSEStore): LoadingState | null {
  if (isCompleteState(state)) {
    return {
      type: 'complete',
      artifactId: state.artifactId!,
      traceId: state.traceId,
    }
  }

  if (isErrorState(state)) {
    return {
      type: 'error',
      error: state.error!.message,
      stage: state.latestEvent?.stage,
    }
  }

  return null
}

/**
 * Derive loading state from SSE store state
 * This is the core logic that computes granular loading states from existing data
 */
export function deriveLoadingState(state: SSEStore): LoadingState {
  // Check connection states first
  const connectionState = getConnectionLoadingState(state)
  if (connectionState) return connectionState

  // Check analysis states
  const analysisState = getAnalysisLoadingState(state)
  if (analysisState) return analysisState

  // Check terminal states
  const terminalState = getTerminalLoadingState(state)
  if (terminalState) return terminalState

  // Fallback states
  if (state.isConnected) {
    return { type: 'connected' }
  }

  return { type: 'connecting', startTime: Date.now() }
}

/**
 * Generate human-readable connection message
 * Exported for testing
 */
export function getConnectionMessage(state: SSEStore): string {
  const loadingState = deriveLoadingState(state)

  switch (loadingState.type) {
    case 'connecting':
      return 'Connecting to analysis stream...'
    case 'reconnecting':
      return `Reconnecting to analysis stream... (${loadingState.attempts}/3)`
    case 'timeout_warning':
      return 'Connection timeout - analysis may be taking longer than expected'
    case 'waiting_for_events':
      return 'Preparing analysis...'
    case 'connected':
      return 'Connected'
    case 'disconnected':
      return 'Disconnected'
    case 'extracting':
      return `Extracting content from ${loadingState.wordCount ? `${loadingState.wordCount} words` : 'source'}...`
    case 'analyzing':
      return `Analyzing with Tech Comparison...`
    case 'generating':
      return 'Generating analysis report...'
    case 'complete':
      return 'Analysis complete'
    case 'error':
      return 'Analysis failed'
    default:
      return 'Preparing analysis...'
  }
}

/**
 * Determine if timeout warning should be shown
 * Exported for testing
 */
export function shouldShowTimeoutWarning(state: SSEStore): boolean {
  const loadingState = deriveLoadingState(state)
  return loadingState.type === 'timeout_warning'
}

/**
 * Get current analysis phase for progress display
 * Exported for testing
 */
export function getAnalysisPhase(state: SSEStore): ComputedLoadingStates['analysisPhase'] {
  const loadingState = deriveLoadingState(state)

  switch (loadingState.type) {
    case 'extracting':
      return 'extracting'
    case 'analyzing':
      return 'analyzing'
    case 'generating':
      return 'generating'
    default:
      return null
  }
}

/**
 * Determine if progress UI should be shown
 * Exported for testing
 */
export function shouldShowProgress(state: SSEStore): boolean {
  const loadingState = deriveLoadingState(state)
  return ['extracting', 'analyzing', 'generating'].includes(loadingState.type)
}

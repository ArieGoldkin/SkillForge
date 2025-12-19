/**
 * Loading State Types for Issue #399 - Missing Loading States
 *
 * Defines discriminated union types for granular loading states
 * derived from SSE events and connection state using zustand-computed.
 */

import type { StageName } from '@app-types/sse'

/**
 * Analysis phase during loading states
 */
export type AnalysisPhase = 'extracting' | 'analyzing' | 'generating' | null

/**
 * Granular loading states discriminated union
 * Each state contains the minimal data needed for that specific state
 */
export type LoadingState =
  | { type: 'disconnected' }
  | { type: 'connecting'; startTime: number }
  | { type: 'connected' }
  | { type: 'reconnecting'; attempts: number }
  | { type: 'waiting_for_events'; connectedAt: number }
  | { type: 'timeout_warning'; connectedAt: number }
  | { type: 'extracting'; stage: StageName; wordCount?: number }
  | { type: 'analyzing'; stage: StageName; progress: number }
  | { type: 'generating'; stage: StageName }
  | { type: 'complete'; artifactId: string; traceId?: string }
  | { type: 'error'; error: string; stage?: StageName }

/**
 * Computed loading state properties derived from SSE store
 */
export interface ComputedLoadingStates {
  /** Current loading state */
  loadingState: LoadingState
  /** Human-readable connection status message */
  connectionMessage: string
  /** Whether to show timeout warning */
  showTimeoutWarning: boolean
  /** Current analysis phase (for progress display) */
  analysisPhase: AnalysisPhase
  /** Whether to show progress UI */
  shouldShowProgress: boolean
}

/**
 * Type guards for loading states
 */
export const isConnectingState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'connecting' }> => state.type === 'connecting'

export const isTimeoutWarningState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'timeout_warning' }> => state.type === 'timeout_warning'

export const isExtractingState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'extracting' }> => state.type === 'extracting'

export const isAnalyzingState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'analyzing' }> => state.type === 'analyzing'

export const isGeneratingState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'generating' }> => state.type === 'generating'

export const isCompleteState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'complete' }> => state.type === 'complete'

export const isErrorState = (
  state: LoadingState
): state is Extract<LoadingState, { type: 'error' }> => state.type === 'error'

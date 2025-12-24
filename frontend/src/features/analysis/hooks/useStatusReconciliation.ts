/**
 * useStatusReconciliation - Reconcile SSE state with REST API
 *
 * When SSE shows error but backend may have succeeded, verify via REST API
 * and override the UI state if needed.
 *
 * This is the KEY FIX for Issue #489.
 *
 * @module hooks/useStatusReconciliation
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import {
  selectClearError,
  selectError,
  selectReconcileComplete,
  useSSEStore,
} from '@stores/sseStore'

import { logger } from '@/lib/logger'

import { analyzeAPI } from '@services/api.service'

const VERIFICATION_DELAY_MS = 2000 // Wait 2 seconds before verifying (debounce)

// Known status values from backend - use explicit list instead of .includes()
const COMPLETE_STATUSES = ['complete', 'completed'] as const
const FAILED_STATUSES = ['failed', 'error'] as const

interface UseStatusReconciliationParams {
  analysisId: string | undefined
  enabled?: boolean
}

interface ReconciliationResult {
  isReconciling: boolean
  reconciledStatus: 'complete' | 'failed' | 'running' | null
  reconciledArtifactId: string | null
}

/**
 * Type guard for complete status
 */
function isCompleteStatus(status: string): boolean {
  return COMPLETE_STATUSES.includes(status as (typeof COMPLETE_STATUSES)[number])
}

/**
 * Type guard for failed status
 */
function isFailedStatus(status: string): boolean {
  return FAILED_STATUSES.includes(status as (typeof FAILED_STATUSES)[number])
}

/**
 * Handle successful verification response
 * Extracted to reduce verifyWithREST complexity
 */
interface VerificationHandlers {
  reconcileComplete: () => void
  clearError: () => void
  setReconciledStatus: (status: 'complete' | 'failed' | 'running' | null) => void
  setReconciledArtifactId: (id: string | null) => void
  hasVerifiedRef: React.MutableRefObject<boolean>
}

function handleVerificationResult(
  status: { status: string; artifact_id?: string | null },
  analysisId: string,
  handlers: VerificationHandlers
): void {
  const {
    reconcileComplete,
    clearError,
    setReconciledStatus,
    setReconciledArtifactId,
    hasVerifiedRef,
  } = handlers

  if (isCompleteStatus(status.status)) {
    logger.info('REST API confirms analysis complete - overriding SSE error', {
      analysisId,
      restStatus: status.status,
      artifactId: status.artifact_id,
    })
    reconcileComplete()
    setReconciledStatus('complete')
    setReconciledArtifactId(status.artifact_id || null)
    hasVerifiedRef.current = true
  } else if (isFailedStatus(status.status)) {
    logger.info('REST API confirms analysis failed', { analysisId, status: status.status })
    setReconciledStatus('failed')
    hasVerifiedRef.current = true
  } else {
    logger.info('REST API shows analysis still running - clearing transient error', {
      analysisId,
      status: status.status,
    })
    clearError()
    setReconciledStatus('running')
  }
}

/**
 * Hook to reconcile SSE error state with REST API
 *
 * When SSE shows error, waits 2 seconds then verifies with REST API.
 * If REST shows complete, clears error and sets completion state.
 *
 * Critical fixes from code review:
 * - Uses isMountedRef to prevent state updates after unmount
 * - Uses isReconcilingRef to avoid stale closure in useCallback
 * - Clears timeout when analysisId changes
 * - Uses atomic reconcileComplete action to prevent race conditions
 *
 * @param params.analysisId - The analysis ID to verify
 * @param params.enabled - Whether reconciliation is enabled (default: true)
 * @returns Reconciliation state including status and artifact ID
 *
 * @example
 * ```tsx
 * const { reconciledStatus, reconciledArtifactId } = useStatusReconciliation({
 *   analysisId: 'abc-123',
 *   enabled: hasError,
 * })
 *
 * // Use reconciled values to override SSE state
 * const finalIsComplete = reconciledStatus === 'complete' || sseIsComplete
 * ```
 */
// eslint-disable-next-line max-lines-per-function -- Complex hook with validation and debouncing logic
export function useStatusReconciliation({
  analysisId,
  enabled = true,
}: UseStatusReconciliationParams): ReconciliationResult {
  // Use individual selectors to prevent unnecessary re-renders
  const error = useSSEStore(selectError)
  const isComplete = useSSEStore((state) => state.isComplete)
  const clearError = useSSEStore(selectClearError)
  const reconcileComplete = useSSEStore(selectReconcileComplete)

  // Local state for reconciliation results
  const [isReconciling, setIsReconciling] = useState(false)
  const [reconciledStatus, setReconciledStatus] = useState<
    'complete' | 'failed' | 'running' | null
  >(null)
  const [reconciledArtifactId, setReconciledArtifactId] = useState<string | null>(null)

  // Refs for cleanup and preventing stale closures
  const verificationTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const hasVerifiedRef = useRef(false)
  const isMountedRef = useRef(true) // FIX: Prevent state updates after unmount
  const isReconcilingRef = useRef(false) // FIX: Avoid isReconciling in useCallback deps
  const currentAnalysisIdRef = useRef(analysisId) // FIX: Track current ID for stale response handling

  // Update current analysis ID ref
  useEffect(() => {
    currentAnalysisIdRef.current = analysisId
  }, [analysisId])

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const verifyWithREST = useCallback(async () => {
    // Use ref to check reconciling state (avoids stale closure)
    if (!analysisId || isReconcilingRef.current) return

    isReconcilingRef.current = true
    if (isMountedRef.current) {
      setIsReconciling(true)
    }

    try {
      logger.info('Verifying analysis status via REST API (Issue #489)', {
        analysisId,
        reason: 'sse_error_reconciliation',
      })

      const status = await analyzeAPI.getAnalysisStatus(analysisId)

      // FIX: Check if this response is for the current analysis ID (prevents stale responses)
      if (currentAnalysisIdRef.current !== analysisId) {
        logger.info('Ignoring stale REST API response', {
          requestedId: analysisId,
          currentId: currentAnalysisIdRef.current,
        })
        return
      }

      // FIX: Check if still mounted before updating state
      if (!isMountedRef.current) return

      // Handle the verification result (extracted for reduced complexity)
      handleVerificationResult(status, analysisId, {
        reconcileComplete,
        clearError,
        setReconciledStatus,
        setReconciledArtifactId,
        hasVerifiedRef,
      })
    } catch (apiError) {
      logger.error('Failed to verify status via REST API', {
        analysisId,
        error: apiError instanceof Error ? apiError.message : String(apiError),
      })
      // Don't change state on API error - keep SSE state
    } finally {
      isReconcilingRef.current = false
      // FIX: Only update state if still mounted
      if (isMountedRef.current) {
        setIsReconciling(false)
      }
    }
  }, [analysisId, clearError, reconcileComplete]) // FIX: Removed isReconciling from deps

  // Trigger verification when SSE error is set
  useEffect(() => {
    // Don't verify if disabled, no analysis ID, no error, already complete, or already verified
    if (!enabled || !analysisId || !error || isComplete || hasVerifiedRef.current) {
      return
    }

    // Clear any pending verification
    if (verificationTimeoutRef.current) {
      clearTimeout(verificationTimeoutRef.current)
    }

    // Debounce: Wait before verifying to avoid race conditions
    verificationTimeoutRef.current = setTimeout(() => {
      void verifyWithREST()
    }, VERIFICATION_DELAY_MS)

    return () => {
      if (verificationTimeoutRef.current) {
        clearTimeout(verificationTimeoutRef.current)
      }
    }
  }, [error, analysisId, enabled, isComplete, verifyWithREST])

  // Reset verification flag when analysis ID changes
  // biome-ignore lint/correctness/useExhaustiveDependencies: analysisId changes should reset verification state
  useEffect(() => {
    hasVerifiedRef.current = false
    setReconciledStatus(null)
    setReconciledArtifactId(null)

    // FIX: Clear pending verification when analysis ID changes
    if (verificationTimeoutRef.current) {
      clearTimeout(verificationTimeoutRef.current)
      verificationTimeoutRef.current = null
    }
  }, [analysisId])

  return {
    isReconciling,
    reconciledStatus,
    reconciledArtifactId,
  }
}

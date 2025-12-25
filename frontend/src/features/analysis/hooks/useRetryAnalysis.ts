/**
 * useRetryAnalysis - React hook for retrying failed analyses
 *
 * Calls POST /api/v1/analyze/{id}/retry to:
 * - Clear error state
 * - Increment retry count
 * - Restart analysis from pending status
 * - Return SSE endpoint for progress streaming
 *
 * Returns:
 * - retry: Function to trigger retry
 * - isRetrying: Loading state
 * - error: Error message if retry fails
 * - data: Response with new status and SSE endpoint
 */

import { useState } from 'react'

import type { AnalysisRetryResponse } from '@app-types/api'

import { logger } from '@lib/logger'

import { analyzeAPI } from '@services/api.service'

export interface UseRetryAnalysisResult {
  /** Trigger retry for the analysis */
  retry: () => Promise<AnalysisRetryResponse | null>
  /** Loading state during retry */
  isRetrying: boolean
  /** Error message if retry fails */
  error: string | null
  /** Response data from successful retry */
  data: AnalysisRetryResponse | null
}

/**
 * Hook for retrying failed analyses
 *
 * @param analysisId - Analysis ID to retry
 * @returns Retry function, loading state, error, and response data
 *
 * @example
 * ```tsx
 * const { retry, isRetrying, error } = useRetryAnalysis(analysisId);
 *
 * <RetryButton
 *   onRetry={retry}
 *   isRetrying={isRetrying}
 *   retryError={error}
 * />
 * ```
 */
export function useRetryAnalysis(analysisId: string): UseRetryAnalysisResult {
  const [isRetrying, setIsRetrying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalysisRetryResponse | null>(null)

  const retry = async (): Promise<AnalysisRetryResponse | null> => {
    setIsRetrying(true)
    setError(null)

    try {
      logger.info('retry_analysis_initiated', { analysisId })

      const response = await analyzeAPI.retryAnalysis(analysisId)

      logger.info('retry_analysis_success', {
        analysisId,
        newStatus: response.status,
        retryCount: response.retry_count,
      })

      setData(response)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry analysis'

      logger.error('retry_analysis_failed', {
        analysisId,
        error: errorMessage,
      })

      setError(errorMessage)
      return null
    } finally {
      setIsRetrying(false)
    }
  }

  return {
    retry,
    isRetrying,
    error,
    data,
  }
}

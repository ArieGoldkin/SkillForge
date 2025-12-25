/**
 * useRerunAnalysis - React hook for rerunning completed analyses
 *
 * Calls POST /api/v1/analyze/{id}/rerun to:
 * - Archive previous artifact
 * - Increment rerun count
 * - Skip content extraction (uses existing content)
 * - Restart analysis from analyzing stage
 * - Generate new artifact with latest AI models/prompts
 *
 * Returns:
 * - rerun: Function to trigger rerun
 * - isRerunning: Loading state
 * - error: Error message if rerun fails
 * - data: Response with new status and SSE endpoint
 */

import { useState } from 'react'

import type { AnalysisRerunResponse } from '@app-types/api'

import { logger } from '@lib/logger'

import { analyzeAPI } from '@services/api.service'

export interface UseRerunAnalysisResult {
  /** Trigger rerun for the analysis */
  rerun: () => Promise<AnalysisRerunResponse | null>
  /** Loading state during rerun */
  isRerunning: boolean
  /** Error message if rerun fails */
  error: string | null
  /** Response data from successful rerun */
  data: AnalysisRerunResponse | null
}

/**
 * Hook for rerunning completed analyses with latest AI
 *
 * @param analysisId - Analysis ID to rerun
 * @returns Rerun function, loading state, error, and response data
 *
 * @example
 * ```tsx
 * const { rerun, isRerunning, error } = useRerunAnalysis(analysisId);
 *
 * <RerunButton
 *   onRerun={rerun}
 *   isRerunning={isRerunning}
 *   rerunError={error}
 * />
 * ```
 */
export function useRerunAnalysis(analysisId: string): UseRerunAnalysisResult {
  const [isRerunning, setIsRerunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnalysisRerunResponse | null>(null)

  const rerun = async (): Promise<AnalysisRerunResponse | null> => {
    setIsRerunning(true)
    setError(null)

    try {
      logger.info('rerun_analysis_initiated', { analysisId })

      const response = await analyzeAPI.rerunAnalysis(analysisId)

      logger.info('rerun_analysis_success', {
        analysisId,
        newStatus: response.status,
        rerunCount: response.rerun_count,
        archivedArtifactId: response.archived_artifact_id,
      })

      setData(response)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to rerun analysis'

      logger.error('rerun_analysis_failed', {
        analysisId,
        error: errorMessage,
      })

      setError(errorMessage)
      return null
    } finally {
      setIsRerunning(false)
    }
  }

  return {
    rerun,
    isRerunning,
    error,
    data,
  }
}

import type { Analysis } from '@app-types/api'
import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api-client'
import { AnalysisSchema } from '@/schemas/api'

/**
 * Fetch analysis data by ID
 * Uses ky-based API client with Zod validation (Issue #550, #548)
 */
async function fetchAnalysis(analysisId: string): Promise<Analysis> {
  return api(`api/v1/analyze/${analysisId}`, AnalysisSchema)
}

/**
 * useAnalysis - TanStack Query hook for fetching analysis metadata
 *
 * @param analysisId - The analysis ID to fetch
 * @param options - Optional TanStack Query options
 * @returns Query result with analysis data
 */
export function useAnalysis(analysisId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => fetchAnalysis(analysisId),
    staleTime: 1000 * 60 * 5, // 5 minutes
    enabled: options?.enabled ?? !!analysisId,
  })
}

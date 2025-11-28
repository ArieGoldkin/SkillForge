import type { Analysis } from '@app-types/api'
import { useQuery } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8500'

/**
 * Fetch analysis data by ID
 */
async function fetchAnalysis(analysisId: string): Promise<Analysis> {
  const response = await fetch(`${API_URL}/api/v1/analyze/${analysisId}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch analysis: ${response.status}`)
  }

  return response.json()
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

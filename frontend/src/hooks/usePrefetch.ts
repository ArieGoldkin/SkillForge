import { useCallback } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { TIME_CONSTANTS } from '@lib/constants'

/**
 * API client configuration
 */
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8500'

/**
 * Prefetch target configuration for common route transitions
 */
export interface PrefetchTarget {
  /** Route to prefetch (e.g., '/analyze/$id') */
  route?: string
  /** Query key for data prefetching */
  queryKey?: string[]
  /** Query function to execute */
  queryFn?: () => Promise<unknown>
}

/**
 * Common prefetch targets for the application
 */
export const PREFETCH_TARGETS = {
  /** Library → Analysis detail transition */
  analysisDetail: (analysisId: string): PrefetchTarget => ({
    route: `/analyze/${analysisId}`,
    queryKey: ['analysis', analysisId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/v1/analyze/${analysisId}`)
      if (!response.ok) {
        throw new Error(`Failed to prefetch analysis: ${response.status}`)
      }
      return response.json()
    },
  }),

  /** Analysis → Artifact transition */
  artifactDetail: (artifactId: string, analysisId?: string): PrefetchTarget => ({
    route: `/artifact/${artifactId}${analysisId ? `?analysisId=${analysisId}` : ''}`,
    queryKey: ['artifact', artifactId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/v1/artifacts/${artifactId}`)
      if (!response.ok) {
        throw new Error(`Failed to prefetch artifact: ${response.status}`)
      }
      return response.json()
    },
  }),

  /** Library page transition */
  library: (): PrefetchTarget => ({
    route: '/library',
  }),
} as const

/**
 * usePrefetch - Hook for prefetching routes and data on hover/intent
 *
 * Combines TanStack Router's route prefetching with TanStack Query's data prefetching
 * for seamless navigation experiences.
 *
 * @example
 * ```tsx
 * const { prefetchAnalysis, prefetchArtifact } = usePrefetch()
 *
 * <Card onMouseEnter={() => prefetchAnalysis(analysisId)}>
 *   ...
 * </Card>
 * ```
 *
 * @returns Prefetch utilities for common route transitions
 */
export function usePrefetch() {
  const queryClient = useQueryClient()

  /**
   * Generic prefetch function for any target
   */
  const prefetch = useCallback(
    async (target: PrefetchTarget) => {
      try {
        // Prefetch route if specified
        // Note: Route prefetching is handled automatically by TanStack Router
        // when using defaultPreload: 'intent' in router config
        // We only need to prefetch the data here

        // Prefetch data if specified
        if (target.queryKey && target.queryFn) {
          await queryClient.prefetchQuery({
            queryKey: target.queryKey,
            queryFn: target.queryFn,
            staleTime: TIME_CONSTANTS.PREFETCH_STALE_TIME,
          })
        }
      } catch {
        // Silently fail prefetch - it's a progressive enhancement
        // Don't block user interaction or log errors to console
        // The actual navigation will handle errors properly
        // In dev mode, we could log but it's intentionally suppressed to avoid noise
      }
    },
    [queryClient]
  )

  /**
   * Prefetch analysis detail page
   * Use on hover over analysis cards in library
   */
  const prefetchAnalysis = useCallback(
    (analysisId: string) => {
      return prefetch(PREFETCH_TARGETS.analysisDetail(analysisId))
    },
    [prefetch]
  )

  /**
   * Prefetch artifact detail page
   * Use on hover over artifact links in analysis results
   */
  const prefetchArtifact = useCallback(
    (artifactId: string, analysisId?: string) => {
      return prefetch(PREFETCH_TARGETS.artifactDetail(artifactId, analysisId))
    },
    [prefetch]
  )

  /**
   * Prefetch library page
   * Use on hover over library navigation link
   */
  const prefetchLibrary = useCallback(() => {
    return prefetch(PREFETCH_TARGETS.library())
  }, [prefetch])

  return {
    prefetch,
    prefetchAnalysis,
    prefetchArtifact,
    prefetchLibrary,
  }
}

/**
 * Type export for consumers
 */
export type UsePrefetchReturn = ReturnType<typeof usePrefetch>

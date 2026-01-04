import { useCallback, useMemo, useRef } from 'react'

import type { AnalysisStatus, FilterStatus } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { logger } from '@/lib/logger'
import { analyzeAPI } from '@/services/api.service'

import { normalizeTitle } from '../utils'
import { dedupeByAnalysisId } from '../utils/libraryTransform'
import {
  mapAnalysisStatusToSkillStatus,
  mapAnalysisStatusToFilterStatus,
} from '../utils/statusMapping'

interface SearchResultItem {
  analysis_id: string
  title: string | null
  snippet: string | null
  tags?: string[]
  content_type: string
  status: AnalysisStatus
  // Error tracking fields
  error_code?: string | null
  error_message?: string | null
  failed_at_stage?: string | null
}

interface SearchResultPage {
  items: SearchResultItem[]
  total?: number
}

interface UseLibrarySkillsParams {
  searchResults?: {
    pages: SearchResultPage[]
  }
}

function isFailedStatus(status: AnalysisStatus): boolean {
  return (
    status === 'failed' ||
    status === 'extraction_failed' ||
    status === 'analysis_failed' ||
    status === 'artifact_failed' ||
    status === 'quality_gate_failed'
  )
}

/**
 * Calculate progress percentage from analysis status.
 *
 * For completed analyses: 100%
 * For running/analyzing analyses: Estimated 50-75% based on typical workflow
 * For failed analyses: undefined (no progress to show)
 * For pending analyses: 0% (not started)
 *
 * TODO: Enhance this with actual stage completion data from analysis status API
 * when available for more accurate progress tracking.
 */
function calculateProgress(status: AnalysisStatus): number | undefined {
  if (isFailedStatus(status)) {
    return undefined
  }

  switch (status) {
    case 'complete':
      return 100
    case 'extracting':
      // Early stage - extraction typically fast
      return 20
    case 'analyzing':
      // Mid stage - most time spent here
      return 65
    case 'generating_artifact':
      // Late stage - almost done
      return 85
    case 'pending':
      return 0
    default:
      // Default to showing some progress for unknown states
      return 0
  }
}

function transformItemToSkill(
  item: SearchResultItem & {
    error_code?: string | null
    error_message?: string | null
    failed_at_stage?: string | null
  },
  navigate: ReturnType<typeof useNavigate>,
  onRetry: (analysisId: string, stage?: string) => void
) {
  const tags = item.tags?.length ? item.tags : [item.content_type]
  return {
    id: item.analysis_id,
    title: normalizeTitle(item.title),
    description: item.snippet
      ? item.snippet.replace(/<\/?mark>/g, '')
      : `Analysis of ${item.content_type}`,
    snippet: item.snippet,
    thumbnail: `https://api.dicebear.com/7.x/shapes/svg?seed=${item.analysis_id}`,
    duration: 25,
    difficulty: 'intermediate' as const,
    tags,
    progress: calculateProgress(item.status),
    status: mapAnalysisStatusToSkillStatus(item.status),
    analysisStatus: item.status,
    // Error tracking fields (for failed analyses)
    errorCode: item.error_code,
    errorMessage: item.error_message,
    failedAtStage: item.failed_at_stage,
    onSelect: (id: string) => {
      navigate({ to: '/analyze/$id', params: { id } })
    },
    // Retry handler
    onRetry,
  }
}

function extractAllItems(searchResults?: UseLibrarySkillsParams['searchResults']) {
  const pages = searchResults?.pages ?? []
  return dedupeByAnalysisId(pages.flatMap((page) => page.items))
}

function extractAvailableTags(items: SearchResultItem[]): string[] {
  const tagSet = new Set<string>()
  items.forEach((item) => {
    const tags = item.tags?.length ? item.tags : [item.content_type]
    tags.forEach((tag) => {
      tagSet.add(tag)
    })
  })
  return Array.from(tagSet)
}

function extractAvailableStatuses(items: SearchResultItem[]): FilterStatus[] {
  const filterStatusSet = new Set<FilterStatus>()
  items.forEach((item) => {
    if (item.status) {
      filterStatusSet.add(mapAnalysisStatusToFilterStatus(item.status))
    }
  })
  return Array.from(filterStatusSet)
}

export function useLibrarySkills({ searchResults }: UseLibrarySkillsParams) {
  const navigate = useNavigate()
  // Use ref for synchronous mutex check to prevent race conditions
  const retryingIdsRef = useRef<Set<string>>(new Set())

  const handleRetry = useCallback(
    async (analysisId: string, stage?: string) => {
      // Synchronous check prevents race condition when called rapidly
      if (retryingIdsRef.current.has(analysisId)) {
        return // Already retrying
      }

      // Immediately mark as retrying (synchronous)
      retryingIdsRef.current.add(analysisId)

      try {
        logger.info('Retrying analysis', { analysisId, stage })
        const response = await analyzeAPI.retryAnalysis(analysisId)
        logger.info('Analysis retry initiated', {
          analysisId: response.analysis_id,
          retryCount: response.retry_count,
        })
        // Navigate to analysis page to see progress
        navigate({ to: '/analyze/$id', params: { id: analysisId } })
      } catch (error) {
        logger.error('Failed to retry analysis', {
          analysisId,
          error: error instanceof Error ? error.message : String(error),
        })
        // TODO: Show error toast/notification
        console.error(
          `Failed to retry analysis: ${error instanceof Error ? error.message : String(error)}`
        )
      } finally {
        retryingIdsRef.current.delete(analysisId)
      }
    },
    [navigate]
  )

  const skills = useMemo(() => {
    const items = extractAllItems(searchResults)
    if (!items.length) return []
    return items.map((item) => transformItemToSkill(item, navigate, handleRetry))
  }, [searchResults, navigate, handleRetry])

  const availableTags = useMemo(
    () => extractAvailableTags(extractAllItems(searchResults)),
    [searchResults]
  )

  const availableStatuses = useMemo(
    () => extractAvailableStatuses(extractAllItems(searchResults)),
    [searchResults]
  )

  return { skills, availableTags, availableStatuses }
}

import { useMemo, useState } from 'react'

import type { AnalysisStatus, FilterStatus } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { analyzeAPI } from '@/services/api.service'
import { logger } from '@/lib/logger'

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
  const isFailed = isFailedStatus(item.status)
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
    progress: isFailed ? undefined : 0,
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

export function useLibrarySkills({ searchResults }: UseLibrarySkillsParams) {
  const navigate = useNavigate()
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set())

  const handleRetry = async (analysisId: string, stage?: string) => {
    if (retryingIds.has(analysisId)) {
      return // Already retrying
    }

    setRetryingIds((prev) => new Set(prev).add(analysisId))

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
      alert(`Failed to retry analysis: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setRetryingIds((prev) => {
        const next = new Set(prev)
        next.delete(analysisId)
        return next
      })
    }
  }

  const skills = useMemo(() => {
    const items = extractAllItems(searchResults)
    if (!items.length) return []
    return items.map((item) => transformItemToSkill(item, navigate, handleRetry))
  }, [searchResults, navigate])

  const availableTags = useMemo(() => {
    const tagSet = new Set<string>()
    const items = extractAllItems(searchResults)
    items.forEach((item) => {
      const tags = item.tags?.length ? item.tags : [item.content_type]
      tags.forEach((tag) => {
        tagSet.add(tag)
      })
    })
    return Array.from(tagSet)
  }, [searchResults])

  // Map AnalysisStatus to FilterStatus for filter component compatibility
  const availableStatuses = useMemo<FilterStatus[]>(() => {
    const filterStatusSet = new Set<FilterStatus>()
    const items = extractAllItems(searchResults)
    items.forEach((item) => {
      if (item.status) {
        filterStatusSet.add(mapAnalysisStatusToFilterStatus(item.status))
      }
    })
    return Array.from(filterStatusSet)
  }, [searchResults])

  return { skills, availableTags, availableStatuses }
}

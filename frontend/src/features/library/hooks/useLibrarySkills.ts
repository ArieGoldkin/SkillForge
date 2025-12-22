import { useMemo } from 'react'

import type { AnalysisStatus } from '@app-types/api'
import { useNavigate } from '@tanstack/react-router'

import { normalizeTitle } from '../utils'
import { dedupeByAnalysisId } from '../utils/libraryTransform'
import { mapAnalysisStatusToSkillStatus } from '../utils/statusMapping'

interface SearchResultItem {
  analysis_id: string
  title: string | null
  snippet: string | null
  tags?: string[]
  content_type: string
  status: AnalysisStatus
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

function transformItemToSkill(item: SearchResultItem, navigate: ReturnType<typeof useNavigate>) {
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
    onSelect: (id: string) => {
      navigate({ to: '/analyze/$id', params: { id } })
    },
  }
}

function extractAllItems(searchResults?: UseLibrarySkillsParams['searchResults']) {
  const pages = searchResults?.pages ?? []
  return dedupeByAnalysisId(pages.flatMap((page) => page.items))
}

export function useLibrarySkills({ searchResults }: UseLibrarySkillsParams) {
  const navigate = useNavigate()

  const skills = useMemo(() => {
    const items = extractAllItems(searchResults)
    if (!items.length) return []
    return items.map((item) => transformItemToSkill(item, navigate))
  }, [searchResults, navigate])

  const availableTags = useMemo(() => {
    const tagSet = new Set<string>()
    const items = extractAllItems(searchResults)
    items.forEach((item) => {
      const tags = item.tags?.length ? item.tags : [item.content_type]
      tags.forEach((tag) => tagSet.add(tag))
    })
    return Array.from(tagSet)
  }, [searchResults])

  const availableStatuses = useMemo<AnalysisStatus[]>(() => {
    const statusSet = new Set<AnalysisStatus>()
    const items = extractAllItems(searchResults)
    items.forEach((item) => {
      if (item.status) statusSet.add(item.status)
    })
    return Array.from(statusSet)
  }, [searchResults])

  return { skills, availableTags, availableStatuses }
}

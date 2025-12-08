import type { AnalysisStatus, ContentType, SearchMode } from '@app-types/api'

import type { SkillStatus } from './components/SkillCard/types'
import type { SkillFilters as SkillFiltersType } from './components/SkillFilters'

const CONTENT_TYPE_TAGS: readonly ContentType[] = ['article', 'video', 'repo']

export const normalizeTitle = (rawTitle: string | null): string => {
  if (!rawTitle) return 'Untitled'
  return rawTitle.replace(/^title:\s*/i, '').trim() || 'Untitled'
}

const pickContentType = (filters: SkillFiltersType): ContentType | undefined => {
  const tag = filters.tags.find((candidate): candidate is ContentType =>
    (CONTENT_TYPE_TAGS as readonly string[]).includes(candidate)
  )
  return tag
}

const pickStatus = (filters: SkillFiltersType): AnalysisStatus | undefined => {
  if (!filters.status.length) return undefined
  const status = filters.status[0]
  return status === 'in-progress' ? 'running' : status
}

export const mapFiltersToQuery = (
  filters: SkillFiltersType,
  showCompletedOnly: boolean
): {
  status?: AnalysisStatus
  content_type?: ContentType
  search_mode?: SearchMode
} => {
  if (showCompletedOnly) {
    return { status: 'complete', content_type: pickContentType(filters) }
  }
  return {
    status: pickStatus(filters),
    content_type: pickContentType(filters),
  }
}

export const mapStatusToSkillStatus = (status: AnalysisStatus): SkillStatus => {
  switch (status) {
    case 'complete':
      return 'completed'
    case 'failed':
      return 'failed'
    case 'extracting':
    case 'analyzing':
    case 'running':
    case 'in-progress':
    case 'pending':
      return 'in-progress'
    default:
      return 'not-started'
  }
}

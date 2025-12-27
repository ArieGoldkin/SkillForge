import type { ContentType, FilterStatus, SearchMode } from '@app-types/api'

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

const pickStatus = (filters: SkillFiltersType): FilterStatus | undefined => {
  if (!filters.status.length) return undefined
  // Filter status is FilterStatus[], so just return the first one
  return filters.status[0]
}

export const mapFiltersToQuery = (
  filters: SkillFiltersType,
  showCompletedOnly: boolean
): {
  status?: FilterStatus
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

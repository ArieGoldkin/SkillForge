import type { AnalysisStatus } from '@app-types/api'

import type { SkillStatus } from '../components/SkillCard'
import type { SkillFilters as SkillFiltersType } from '../components/SkillFilters'
import { mapAnalysisStatusToFilterStatus } from '../utils/statusMapping'

interface Skill {
  id: string
  title: string
  description: string
  thumbnail: string
  duration: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  tags: string[]
  progress?: number
  status: SkillStatus
  analysisStatus: AnalysisStatus
  onSelect: (id: string) => void
}

export function useFilteredSkills(skills: Skill[], searchQuery: string, filters: SkillFiltersType) {
  return skills.filter((skill) => {
    if (searchQuery && !skill.title.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (filters.difficulty.length && !filters.difficulty.includes(skill.difficulty)) {
      return false
    }
    // Map AnalysisStatus to FilterStatus for comparison
    if (
      filters.status.length &&
      !filters.status.includes(mapAnalysisStatusToFilterStatus(skill.analysisStatus))
    ) {
      return false
    }
    if (filters.tags.length && !filters.tags.some((tag) => skill.tags.includes(tag))) {
      return false
    }
    return true
  })
}

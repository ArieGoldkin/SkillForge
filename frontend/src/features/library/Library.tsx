import { useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

import { analyzeAPI } from '@services/api.service'
import { mockAnalyses } from '@services/mock.service'

import { ContentGrid } from './components/ContentGrid'
import { FiltersSidebar } from './components/FiltersSidebar'
import { LibraryHeader } from './components/LibraryHeader'
import type { SkillFilters as SkillFiltersType } from './components/SkillFilters'
import { SkillSearch } from './components/SkillSearch'
import { useFilteredSkills, useSkillsData } from './hooks'

export default function Library() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<SkillFiltersType>({
    difficulty: [],
    tags: [],
    status: [],
    durationRange: [0, 1000],
  })

  const { data: analyses, isLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: async () => {
      // Try real API first, fall back to mock data if not available
      const realAnalyses = await analyzeAPI.listAnalyses()
      if (realAnalyses.length > 0) {
        return realAnalyses
      }
      // Fallback to mock data until backend implements list endpoint
      return mockAnalyses
    },
  })

  const skills = useSkillsData(analyses)
  const filteredSkills = useFilteredSkills(skills, searchQuery, filters)

  const handleSelectSkill = (id: string) => {
    navigate({ to: '/analyze/$id', params: { id } })
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <LibraryHeader />
      <div className="mb-6">
        <SkillSearch onSearch={setSearchQuery} placeholder="Search analyses..." />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <FiltersSidebar filters={filters} onChange={setFilters} />
        <ContentGrid
          isLoading={isLoading}
          skills={filteredSkills}
          onSelectSkill={handleSelectSkill}
        />
      </div>
    </div>
  )
}

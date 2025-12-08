import { describe, expect, it } from 'vitest'

import { useFilteredSkills } from '../useFilteredSkills'

const mockSkills = [
  {
    id: '1',
    title: 'React Basics',
    description: 'Learn React',
    thumbnail: '',
    duration: 30,
    difficulty: 'beginner' as const,
    tags: ['React'],
    progress: 0,
    status: 'not-started' as const,
    analysisStatus: 'complete' as const,
    onSelect: () => {},
  },
  {
    id: '2',
    title: 'TypeScript Advanced',
    description: 'Advanced TS',
    thumbnail: '',
    duration: 60,
    difficulty: 'advanced' as const,
    tags: ['TypeScript'],
    progress: 100,
    status: 'completed' as const,
    analysisStatus: 'pending' as const,
    onSelect: () => {},
  },
]

const emptyFilters = {
  difficulty: [],
  status: [],
  tags: [],
  durationRange: [0, 1000] as [number, number],
}

describe('useFilteredSkills', () => {
  it('returns all skills when no filters applied', () => {
    const result = useFilteredSkills(mockSkills, '', emptyFilters)
    expect(result).toHaveLength(2)
  })

  it('filters by search query', () => {
    const result = useFilteredSkills(mockSkills, 'react', emptyFilters)
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe('React Basics')
  })

  it('filters by difficulty', () => {
    const filters = { ...emptyFilters, difficulty: ['advanced' as const] }
    const result = useFilteredSkills(mockSkills, '', filters)
    expect(result).toHaveLength(1)
    expect(result[0].difficulty).toBe('advanced')
  })

  it('filters by status', () => {
    const filters = { ...emptyFilters, status: ['pending' as const] }
    const result = useFilteredSkills(mockSkills, '', filters)
    expect(result).toHaveLength(1)
    expect(result[0].analysisStatus).toBe('pending')
  })

  it('filters by tags', () => {
    const filters = { ...emptyFilters, tags: ['React'] }
    const result = useFilteredSkills(mockSkills, '', filters)
    expect(result).toHaveLength(1)
    expect(result[0].tags).toContain('React')
  })
})

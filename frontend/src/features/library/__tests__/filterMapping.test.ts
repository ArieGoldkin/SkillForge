import { describe, expect, it } from 'vitest'

import type { SkillFilters } from '../components/SkillFilters'
import type { SkillStatus } from '../components/SkillCard/types'
import { mapFiltersToQuery } from '../utils'

describe('mapFiltersToQuery', () => {
  const baseFilters: SkillFilters = {
    difficulty: [],
    status: [],
    tags: [],
    durationRange: [0, 1000],
  }

  it('forces status=complete when showCompletedOnly is true', () => {
    const result = mapFiltersToQuery(baseFilters, true)
    expect(result.status).toBe('complete')
  })

  it('maps first status selection to backend status', () => {
    const filters: SkillFilters = { ...baseFilters, status: ['in-progress' as SkillStatus] }
    const result = mapFiltersToQuery(filters, false)
    expect(result.status).toBe('running')
  })

  it('maps tag selection to content_type', () => {
    const filters: SkillFilters = { ...baseFilters, tags: ['video', 'repo'] }
    const result = mapFiltersToQuery(filters, false)
    expect(result.content_type).toBe('video')
  })

  it('returns undefined when no mappings are set', () => {
    const result = mapFiltersToQuery(baseFilters, false)
    expect(result.status).toBeUndefined()
    expect(result.content_type).toBeUndefined()
  })
})

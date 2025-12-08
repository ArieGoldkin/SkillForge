import { describe, expect, it } from 'vitest'

import { dedupeByAnalysisId } from './libraryTransform'

describe('dedupeByAnalysisId', () => {
  it('removes duplicate analysis_ids while preserving first occurrence order', () => {
    const input = [
      { analysis_id: 'a', title: 'first' },
      { analysis_id: 'b', title: 'second' },
      { analysis_id: 'a', title: 'duplicate first' },
      { analysis_id: 'c', title: 'third' },
    ]

    const result = dedupeByAnalysisId(input)

    expect(result).toEqual([
      { analysis_id: 'a', title: 'first' },
      { analysis_id: 'b', title: 'second' },
      { analysis_id: 'c', title: 'third' },
    ])
  })

  it('returns empty array when given no items', () => {
    expect(dedupeByAnalysisId([])).toEqual([])
  })
})

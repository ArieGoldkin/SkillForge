import { describe, expect, it } from 'vitest'

import { normalizeTitle } from '../Library'

describe('normalizeTitle', () => {
  it('returns Untitled when null', () => {
    expect(normalizeTitle(null)).toBe('Untitled')
  })

  it('strips leading "Title:" prefix case-insensitively', () => {
    expect(normalizeTitle('Title: Example')).toBe('Example')
    expect(normalizeTitle('title:   Example')).toBe('Example')
    expect(normalizeTitle('TITLE:Example')).toBe('Example')
  })

  it('returns Untitled when only prefix is present', () => {
    expect(normalizeTitle('Title:   ')).toBe('Untitled')
  })

  it('returns trimmed title when no prefix', () => {
    expect(normalizeTitle('  My Article  ')).toBe('My Article')
  })
})

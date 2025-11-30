/**
 * Tests for analyze.$id route - Search params validation
 */

import { describe, expect, it } from 'vitest'

// Extract and test the validateSearch logic directly
// This mirrors the function in analyze.$id.tsx
interface AnalyzeSearchParams {
  completed?: boolean
  artifactId?: string
}

function validateSearch(search: Record<string, unknown>): AnalyzeSearchParams {
  return {
    completed: search.completed === 'true' || search.completed === true,
    artifactId: typeof search.artifactId === 'string' ? search.artifactId : undefined,
  }
}

describe('analyze route validateSearch', () => {
  describe('completed parameter', () => {
    it('parses completed="true" string to boolean true', () => {
      const result = validateSearch({ completed: 'true' })
      expect(result.completed).toBe(true)
    })

    it('parses completed=true boolean to boolean true', () => {
      const result = validateSearch({ completed: true })
      expect(result.completed).toBe(true)
    })

    it('returns false for completed="false" string', () => {
      const result = validateSearch({ completed: 'false' })
      expect(result.completed).toBe(false)
    })

    it('returns false for completed=false boolean', () => {
      const result = validateSearch({ completed: false })
      expect(result.completed).toBe(false)
    })

    it('returns false for missing completed parameter', () => {
      const result = validateSearch({})
      expect(result.completed).toBe(false)
    })

    it('returns false for other values', () => {
      expect(validateSearch({ completed: 'yes' }).completed).toBe(false)
      expect(validateSearch({ completed: 1 }).completed).toBe(false)
      expect(validateSearch({ completed: null }).completed).toBe(false)
    })
  })

  describe('artifactId parameter', () => {
    it('returns string for valid artifactId', () => {
      const result = validateSearch({ artifactId: 'abc-123-def' })
      expect(result.artifactId).toBe('abc-123-def')
    })

    it('returns undefined for missing artifactId', () => {
      const result = validateSearch({})
      expect(result.artifactId).toBeUndefined()
    })

    it('returns undefined for non-string artifactId', () => {
      expect(validateSearch({ artifactId: 123 }).artifactId).toBeUndefined()
      expect(validateSearch({ artifactId: null }).artifactId).toBeUndefined()
      expect(validateSearch({ artifactId: true }).artifactId).toBeUndefined()
      expect(validateSearch({ artifactId: {} }).artifactId).toBeUndefined()
    })

    it('handles empty string artifactId', () => {
      const result = validateSearch({ artifactId: '' })
      expect(result.artifactId).toBe('')
    })
  })

  describe('combined parameters', () => {
    it('parses both parameters correctly', () => {
      const result = validateSearch({
        completed: 'true',
        artifactId: 'artifact-uuid-here',
      })

      expect(result.completed).toBe(true)
      expect(result.artifactId).toBe('artifact-uuid-here')
    })

    it('handles extra unknown parameters gracefully', () => {
      const result = validateSearch({
        completed: true,
        artifactId: 'test-id',
        unknownParam: 'should-be-ignored',
        anotherOne: 42,
      })

      expect(result.completed).toBe(true)
      expect(result.artifactId).toBe('test-id')
      expect(result).not.toHaveProperty('unknownParam')
      expect(result).not.toHaveProperty('anotherOne')
    })
  })
})

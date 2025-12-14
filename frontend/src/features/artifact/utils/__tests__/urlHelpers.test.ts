/**
 * Tests for URL helper utilities
 */

import { describe, it, expect } from 'vitest'

import { isGoldenDatasetUrl, extractDocumentName, getSourceUrlDisplay } from '../urlHelpers'

describe('urlHelpers', () => {
  describe('isGoldenDatasetUrl', () => {
    it('returns true for skillforge.dev URLs', () => {
      expect(isGoldenDatasetUrl('https://docs.skillforge.dev/context-engineering')).toBe(true)
      expect(isGoldenDatasetUrl('https://docs.skillforge.dev/rag-survey')).toBe(true)
      expect(isGoldenDatasetUrl('http://docs.skillforge.dev/chain-of-thought')).toBe(true)
    })

    it('returns false for real URLs', () => {
      expect(isGoldenDatasetUrl('https://github.com/example/repo')).toBe(false)
      expect(isGoldenDatasetUrl('https://medium.com/article')).toBe(false)
      expect(isGoldenDatasetUrl('https://example.com')).toBe(false)
    })

    it('returns false for null/undefined', () => {
      expect(isGoldenDatasetUrl(null)).toBe(false)
      expect(isGoldenDatasetUrl(undefined)).toBe(false)
    })

    it('returns false for empty string', () => {
      expect(isGoldenDatasetUrl('')).toBe(false)
    })

    it('handles URLs with query parameters', () => {
      expect(isGoldenDatasetUrl('https://docs.skillforge.dev/example?param=value')).toBe(true)
      expect(isGoldenDatasetUrl('https://example.com?url=docs.skillforge.dev')).toBe(true)
    })
  })

  describe('extractDocumentName', () => {
    it('extracts and formats document name from URL path', () => {
      expect(extractDocumentName('https://docs.skillforge.dev/chain-of-thought')).toBe(
        'Chain Of Thought'
      )
      expect(extractDocumentName('https://docs.skillforge.dev/context-engineering')).toBe(
        'Context Engineering'
      )
      expect(extractDocumentName('https://docs.skillforge.dev/rag-survey')).toBe('Rag Survey')
    })

    it('handles single-word document names', () => {
      expect(extractDocumentName('https://docs.skillforge.dev/example')).toBe('Example')
    })

    it('handles URLs with trailing slashes', () => {
      expect(extractDocumentName('https://docs.skillforge.dev/chain-of-thought/')).toBe(
        'Chain Of Thought'
      )
    })

    it('handles URLs with query parameters', () => {
      expect(extractDocumentName('https://docs.skillforge.dev/chain-of-thought?param=value')).toBe(
        'Chain Of Thought'
      )
    })

    it('returns fallback for invalid URLs', () => {
      expect(extractDocumentName('not-a-url')).toBe('Example Document')
      expect(extractDocumentName('')).toBe('Example Document')
    })

    it('handles root path', () => {
      expect(extractDocumentName('https://docs.skillforge.dev/')).toBe('Example Document')
      expect(extractDocumentName('https://docs.skillforge.dev')).toBe('Example Document')
    })
  })

  describe('getSourceUrlDisplay', () => {
    it('returns golden dataset info for fixture URLs', () => {
      const result = getSourceUrlDisplay('https://docs.skillforge.dev/chain-of-thought')
      expect(result.isGoldenDataset).toBe(true)
      expect(result.badgeText).toBe('📚 Golden Dataset')
      expect(result.displayText).toBe('Chain Of Thought')
    })

    it('returns different document names for different URLs', () => {
      const result1 = getSourceUrlDisplay('https://docs.skillforge.dev/context-engineering')
      expect(result1.isGoldenDataset).toBe(true)
      expect(result1.displayText).toBe('Context Engineering')

      const result2 = getSourceUrlDisplay('https://docs.skillforge.dev/rag-survey')
      expect(result2.isGoldenDataset).toBe(true)
      expect(result2.displayText).toBe('Rag Survey')
    })

    it('returns URL for real sources', () => {
      const url = 'https://github.com/example/repo'
      const result = getSourceUrlDisplay(url)
      expect(result.isGoldenDataset).toBe(false)
      expect(result.displayText).toBe(url)
      expect(result.badgeText).toBeUndefined()
    })

    it('handles various real URL formats', () => {
      const urls = [
        'https://medium.com/article',
        'https://dev.to/some-article',
        'https://www.youtube.com/watch?v=abc123',
      ]

      urls.forEach((url) => {
        const result = getSourceUrlDisplay(url)
        expect(result.isGoldenDataset).toBe(false)
        expect(result.displayText).toBe(url)
      })
    })

    it('handles null URL', () => {
      const result = getSourceUrlDisplay(null)
      expect(result.isGoldenDataset).toBe(false)
      expect(result.displayText).toBe('Unknown source')
      expect(result.badgeText).toBeUndefined()
    })

    it('handles undefined URL', () => {
      const result = getSourceUrlDisplay(undefined)
      expect(result.isGoldenDataset).toBe(false)
      expect(result.displayText).toBe('Unknown source')
      expect(result.badgeText).toBeUndefined()
    })

    it('handles empty string', () => {
      const result = getSourceUrlDisplay('')
      expect(result.isGoldenDataset).toBe(false)
      expect(result.displayText).toBe('Unknown source')
    })
  })
})

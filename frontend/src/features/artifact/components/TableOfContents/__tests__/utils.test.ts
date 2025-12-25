/**
 * Tests for TableOfContents utility functions
 */

import { describe, expect, it } from 'vitest'

import { slugify } from '../../../utils/markdownHeadingParser'

import { extractHeadings } from '../utils'

describe('slugify', () => {
  it('converts text to lowercase slug', () => {
    expect(slugify('Hello World')).toBe('hello-world')
  })

  it('removes special characters', () => {
    expect(slugify('Hello! @World#')).toBe('hello-world')
  })

  it('replaces spaces with hyphens', () => {
    expect(slugify('Multiple   Spaces   Here')).toBe('multiple-spaces-here')
  })

  it('removes leading and trailing hyphens', () => {
    expect(slugify('  Hello World  ')).toBe('hello-world')
  })

  it('handles complex headings', () => {
    expect(slugify('Step 1: Getting Started (Prerequisites)')).toBe(
      'step-1-getting-started-prerequisites'
    )
  })
})

describe('extractHeadings', () => {
  it('extracts h2 headings', () => {
    const markdown = `
## First Heading
Some content
## Second Heading
More content
`
    const headings = extractHeadings(markdown)

    expect(headings).toHaveLength(2)
    expect(headings[0].text).toBe('First Heading')
    expect(headings[0].level).toBe(2)
    expect(headings[0].id).toBe('first-heading')
    expect(headings[1].text).toBe('Second Heading')
    expect(headings[1].level).toBe(2)
  })

  it('extracts h3 headings nested under h2', () => {
    const markdown = `
## Main Section
### Subsection 1
### Subsection 2
## Another Section
### Subsection 3
`
    const headings = extractHeadings(markdown)

    expect(headings).toHaveLength(2)
    expect(headings[0].children).toHaveLength(2)
    expect(headings[0].children?.[0].text).toBe('Subsection 1')
    expect(headings[0].children?.[0].level).toBe(3)
    expect(headings[1].children).toHaveLength(1)
    expect(headings[1].children?.[0].text).toBe('Subsection 3')
  })

  it('ignores h3 headings before first h2', () => {
    const markdown = `
### Orphan Subsection
## Main Section
### Valid Subsection
`
    const headings = extractHeadings(markdown)

    expect(headings).toHaveLength(1)
    expect(headings[0].text).toBe('Main Section')
    expect(headings[0].children).toHaveLength(1)
  })

  it('handles markdown without headings', () => {
    const markdown = 'Just some text without any headings.'
    const headings = extractHeadings(markdown)

    expect(headings).toHaveLength(0)
  })

  it('trims whitespace from heading text', () => {
    const markdown = '##   Heading with spaces   '
    const headings = extractHeadings(markdown)

    expect(headings[0].text).toBe('Heading with spaces')
  })

  it('ignores h1 and h4+ headings', () => {
    const markdown = `
# Title (H1)
## Section (H2)
### Subsection (H3)
#### Detail (H4)
##### Sub-detail (H5)
`
    const headings = extractHeadings(markdown)

    expect(headings).toHaveLength(1)
    expect(headings[0].text).toBe('Section (H2)')
    expect(headings[0].children).toHaveLength(1)
    expect(headings[0].children?.[0].text).toBe('Subsection (H3)')
  })
})

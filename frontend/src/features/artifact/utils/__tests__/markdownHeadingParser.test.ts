/**
 * Tests for markdownHeadingParser utility
 *
 * This shared utility is used by both HeadingIdContext and TableOfContents
 * to ensure consistent heading ID generation across the application.
 */

import { describe, expect, it } from 'vitest'

import { makeUniqueHeadingId, parseMarkdownHeadings, slugify } from '../markdownHeadingParser'

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

  it('handles special characters in headings', () => {
    expect(slugify("What's New?")).toBe('whats-new')
    expect(slugify('C++ Programming')).toBe('c-programming')
    expect(slugify('Node.js & TypeScript')).toBe('nodejs-typescript')
  })

  it('handles empty string', () => {
    expect(slugify('')).toBe('')
  })

  it('handles only special characters', () => {
    const result = slugify('@#$%^&*')
    expect(typeof result).toBe('string')
    expect(result).toBe('')
  })
})

describe('makeUniqueHeadingId', () => {
  it('returns base ID for first occurrence', () => {
    const seenIds = new Map<string, number>()
    const id = makeUniqueHeadingId('details', 0, seenIds)
    expect(id).toBe('details')
    expect(seenIds.get('details')).toBe(1)
  })

  it('adds line number suffix for duplicate IDs', () => {
    const seenIds = new Map<string, number>()
    // First occurrence
    expect(makeUniqueHeadingId('details', 0, seenIds)).toBe('details')
    // Second occurrence on line 5
    expect(makeUniqueHeadingId('details', 5, seenIds)).toBe('details-l5')
    // Third occurrence on line 10
    expect(makeUniqueHeadingId('details', 10, seenIds)).toBe('details-l10')
  })

  it('handles multiple different IDs', () => {
    const seenIds = new Map<string, number>()
    expect(makeUniqueHeadingId('intro', 0, seenIds)).toBe('intro')
    expect(makeUniqueHeadingId('details', 1, seenIds)).toBe('details')
    expect(makeUniqueHeadingId('intro', 2, seenIds)).toBe('intro-l2')
    expect(makeUniqueHeadingId('conclusion', 3, seenIds)).toBe('conclusion')
    expect(makeUniqueHeadingId('details', 4, seenIds)).toBe('details-l4')
  })

  it('mutates the seenIds map correctly', () => {
    const seenIds = new Map<string, number>()
    makeUniqueHeadingId('test', 0, seenIds)
    expect(seenIds.get('test')).toBe(1)
    makeUniqueHeadingId('test', 5, seenIds)
    expect(seenIds.get('test')).toBe(2)
    makeUniqueHeadingId('test', 10, seenIds)
    expect(seenIds.get('test')).toBe(3)
  })
})

describe('parseMarkdownHeadings', () => {
  it('extracts all heading levels (h1-h6)', () => {
    const markdown = `# H1
## H2
### H3
#### H4
##### H5
###### H6
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(6)
    expect(headings[0]).toEqual({
      id: 'h1',
      text: 'H1',
      level: 1,
      lineNumber: 0,
    })
    expect(headings[5]).toEqual({
      id: 'h6',
      text: 'H6',
      level: 6,
      lineNumber: 5,
    })
  })

  it('generates unique IDs for duplicate headings', () => {
    const markdown = `## Details
Some content.

## Details
More content.

## Details
Final content.
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(3)
    expect(headings[0].id).toBe('details')
    expect(headings[1].id).toBe('details-l3')
    expect(headings[2].id).toBe('details-l6')
  })

  it('skips headings inside code blocks (triple backticks)', () => {
    const markdown = `## Real Heading

\`\`\`markdown
## Fake Heading
### Another Fake
\`\`\`

## Another Real Heading
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(2)
    expect(headings[0].text).toBe('Real Heading')
    expect(headings[1].text).toBe('Another Real Heading')
  })

  it('skips headings inside code blocks (triple tildes)', () => {
    const markdown = `## Real Heading

~~~python
## This is a comment
def foo():
    pass
~~~

## Another Real Heading
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(2)
    expect(headings[0].text).toBe('Real Heading')
    expect(headings[1].text).toBe('Another Real Heading')
  })

  it('handles nested code blocks correctly', () => {
    const markdown = `## Start

\`\`\`
Code block 1
## Not a heading
\`\`\`

## Middle

~~~
## Also not a heading
~~~

## End
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(3)
    expect(headings[0].text).toBe('Start')
    expect(headings[1].text).toBe('Middle')
    expect(headings[2].text).toBe('End')
  })

  it('handles empty markdown', () => {
    const headings = parseMarkdownHeadings('')
    expect(headings).toHaveLength(0)
  })

  it('handles markdown with no headings', () => {
    const markdown = `Just some text.
And more text.
No headings here.`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(0)
  })

  it('trims whitespace from heading text', () => {
    const markdown = `##   Heading with spaces
### Another   heading
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings[0].text).toBe('Heading with spaces')
    expect(headings[1].text).toBe('Another   heading')
  })

  it('preserves line numbers correctly', () => {
    const markdown = `Some text
## First Heading
More text
More text
### Second Heading
Even more text
## Third Heading
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings[0].lineNumber).toBe(1)
    expect(headings[1].lineNumber).toBe(4)
    expect(headings[2].lineNumber).toBe(6)
  })

  it('handles headings with inline formatting', () => {
    const markdown = `## **Bold** Heading
### *Italic* Text
#### \`Code\` in heading
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(3)
    expect(headings[0].text).toBe('**Bold** Heading')
    expect(headings[1].text).toBe('*Italic* Text')
    expect(headings[2].text).toBe('`Code` in heading')
  })

  it('handles very long heading text', () => {
    const longText = 'A'.repeat(100)
    const markdown = `## ${longText}
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings[0].text).toBe(longText)
    expect(headings[0].id).toBe(longText.toLowerCase())
  })

  it('handles mixed heading levels', () => {
    const markdown = `# Title
## Section 1
### Subsection 1.1
#### Detail 1.1.1
## Section 2
### Subsection 2.1
`
    const headings = parseMarkdownHeadings(markdown)
    expect(headings).toHaveLength(6)
    expect(headings.map((h) => h.level)).toEqual([1, 2, 3, 4, 2, 3])
  })

  it('returns consistent IDs across multiple parses', () => {
    const markdown = `## Introduction
## Details
## Implementation
## Details
`
    const headings1 = parseMarkdownHeadings(markdown)
    const headings2 = parseMarkdownHeadings(markdown)

    expect(headings1.map((h) => h.id)).toEqual(headings2.map((h) => h.id))
  })
})

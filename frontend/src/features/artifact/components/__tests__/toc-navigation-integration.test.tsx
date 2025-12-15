/**
 * Integration test for TableOfContents navigation with MarkdownPreview
 *
 * This test verifies that:
 * 1. TOC extracts heading IDs correctly
 * 2. MarkdownPreview renders headings with matching IDs
 * 3. Clicking TOC links scrolls to the correct heading
 * 4. IDs are consistent between TOC and rendered headings
 */

import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MarkdownPreview } from '../MarkdownPreview'
import { TableOfContents } from '../TableOfContents'

const sampleMarkdown = `
## Introduction
This is the introduction section with some content.

### Getting Started
First steps here with details.

### Prerequisites
What you need to know before starting.

## Implementation
The main implementation details go here.

### Step 1
First step of implementation.

### Step 2
Second step of implementation.

## Conclusion
Final thoughts and summary.
`

describe('TOC Navigation Integration (Bug Fix Verification)', () => {
  it('generates consistent IDs between TOC and MarkdownPreview', () => {
    const { container } = render(
      <div>
        <TableOfContents content={sampleMarkdown} />
        <MarkdownPreview content={sampleMarkdown} showMetadata={false} />
      </div>
    )

    // Verify h2 headings exist with correct IDs
    expect(container.querySelector('#introduction')).toBeInTheDocument()
    expect(container.querySelector('#implementation')).toBeInTheDocument()
    expect(container.querySelector('#conclusion')).toBeInTheDocument()

    // Verify h3 headings exist with correct IDs
    expect(container.querySelector('#getting-started')).toBeInTheDocument()
    expect(container.querySelector('#prerequisites')).toBeInTheDocument()
    expect(container.querySelector('#step-1')).toBeInTheDocument()
    expect(container.querySelector('#step-2')).toBeInTheDocument()
  })

  it('TOC links correspond to actual heading IDs in the document', () => {
    const { container } = render(
      <div>
        <TableOfContents content={sampleMarkdown} />
        <MarkdownPreview content={sampleMarkdown} showMetadata={false} />
      </div>
    )

    // Get all TOC buttons
    const tocButtons = screen.getAllByRole('button')

    // Filter out the toggle button (mobile)
    const headingButtons = tocButtons.filter((btn) =>
      [
        'Introduction',
        'Implementation',
        'Conclusion',
        'Getting Started',
        'Prerequisites',
        'Step 1',
        'Step 2',
      ].some((heading) => btn.textContent?.includes(heading))
    )

    // For each TOC button, verify a corresponding heading exists in the DOM
    headingButtons.forEach((button) => {
      const headingText = button.textContent?.trim()
      if (!headingText) return

      // Convert heading text to expected ID (same as slugify)
      const expectedId = headingText
        .toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '')

      const headingElement = container.querySelector(`#${expectedId}`)
      expect(headingElement).toBeInTheDocument()
      expect(headingElement?.tagName).toMatch(/^H[23]$/)
    })
  })

  it('scrolls to heading when TOC link is clicked', async () => {
    const user = userEvent.setup()

    // Mock scrollTo and getElementById
    const mockScrollTo = vi.fn()
    const originalScrollTo = window.scrollTo
    window.scrollTo = mockScrollTo

    const { container } = render(
      <div>
        <TableOfContents content={sampleMarkdown} />
        <MarkdownPreview content={sampleMarkdown} showMetadata={false} />
      </div>
    )

    // Mock getBoundingClientRect for the heading element
    const heading = container.querySelector('#introduction')
    if (heading) {
      heading.getBoundingClientRect = vi.fn(() => ({
        top: 500,
        bottom: 600,
        left: 0,
        right: 800,
        width: 800,
        height: 100,
        x: 0,
        y: 500,
        toJSON: () => ({}),
      }))
    }

    // Click the "Introduction" TOC link
    const introButton = screen.getByRole('button', { name: /Introduction/i })
    await user.click(introButton)

    // Verify scrollTo was called
    expect(mockScrollTo).toHaveBeenCalled()

    // Restore original scrollTo
    window.scrollTo = originalScrollTo
  })

  it('handles duplicate heading names with unique IDs', () => {
    const duplicateMarkdown = `
## Overview
First overview section.

### Details
Some details here.

## Implementation
Implementation section.

### Details
More details here.

## Summary
Summary section.

### Details
Final details.
`

    const { container } = render(
      <div>
        <TableOfContents content={duplicateMarkdown} />
        <MarkdownPreview content={duplicateMarkdown} showMetadata={false} />
      </div>
    )

    // First "Details" should have base ID
    expect(container.querySelector('#details')).toBeInTheDocument()

    // Subsequent "Details" should have line-number suffixed IDs
    // (Line numbers are 0-indexed: lines 10 and 16 in the markdown above)
    expect(container.querySelector('#details-l10')).toBeInTheDocument()
    expect(container.querySelector('#details-l16')).toBeInTheDocument()

    // All three "Details" headings should exist
    const detailsHeadings = container.querySelectorAll('h3')
    const detailsTexts = Array.from(detailsHeadings).filter((h3) => h3.textContent === 'Details')
    expect(detailsTexts).toHaveLength(3)
  })

  it('ignores headings inside code blocks', () => {
    const markdownWithCode = `
## Real Heading
This is real content.

\`\`\`markdown
## Fake Heading in Code
This should not appear in TOC
### Another Fake Heading
\`\`\`

## Another Real Heading
More real content.
`

    const { container } = render(
      <div>
        <TableOfContents content={markdownWithCode} />
        <MarkdownPreview content={markdownWithCode} showMetadata={false} />
      </div>
    )

    // Real headings should exist as h2 elements
    expect(container.querySelector('#real-heading')).toBeInTheDocument()
    expect(container.querySelector('#another-real-heading')).toBeInTheDocument()

    // Fake headings should NOT exist as h2 elements (they're in code blocks)
    expect(container.querySelector('#fake-heading-in-code')).not.toBeInTheDocument()
    expect(container.querySelector('#another-fake-heading')).not.toBeInTheDocument()

    // TOC should only show 2 buttons (plus the mobile toggle)
    const headingButtons = screen.getAllByRole('button')
    const realHeadingButtons = headingButtons.filter((btn) =>
      ['Real Heading', 'Another Real Heading'].some((heading) => btn.textContent?.includes(heading))
    )
    expect(realHeadingButtons).toHaveLength(2)
  })
})

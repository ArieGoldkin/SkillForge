/**
 * Tests for TableOfContents component
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TableOfContents } from '../TableOfContents'

const sampleMarkdown = `
## Introduction
This is the introduction section.

### Getting Started
First steps here.

### Prerequisites
What you need to know.

## Implementation
The main implementation details.

### Step 1
First step.

### Step 2
Second step.

## Conclusion
Final thoughts.
`

describe('TableOfContents', () => {
  it('renders table of contents with headings', () => {
    render(<TableOfContents content={sampleMarkdown} />)

    // Check that the component renders
    expect(screen.getByTestId('table-of-contents')).toBeInTheDocument()

    // Check that h2 headings are present
    expect(screen.getByRole('button', { name: /Introduction/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Implementation/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Conclusion/i })).toBeInTheDocument()

    // Check that h3 headings are present
    expect(screen.getByRole('button', { name: /Getting Started/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Prerequisites/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Step 1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Step 2/i })).toBeInTheDocument()
  })

  it('does not render when content has no headings', () => {
    const noHeadingsContent = 'Just some plain text without any headings.'
    const { container } = render(<TableOfContents content={noHeadingsContent} />)

    expect(container.firstChild).toBeNull()
  })

  it('renders toggle button on mobile', () => {
    render(<TableOfContents content={sampleMarkdown} />)

    expect(screen.getByRole('button', { name: /Table of Contents/i })).toBeInTheDocument()
  })

  it('has proper accessibility attributes', () => {
    render(<TableOfContents content={sampleMarkdown} />)

    const nav = screen.getByTestId('table-of-contents')
    expect(nav).toHaveAttribute('aria-label', 'Table of contents')
  })
})

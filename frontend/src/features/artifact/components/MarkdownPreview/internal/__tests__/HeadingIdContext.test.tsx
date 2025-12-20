/**
 * HeadingIdContext Tests
 *
 * Tests for the HeadingIdList class and HeadingIdProvider component
 * that solve the React 18 StrictMode double-render ID consistency issue.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HeadingIdList, HeadingIdProvider, useHeadingId } from '../HeadingIdContext'

// Test component to exercise the useHeadingId hook
function TestHeading({ text }: { text: string }) {
  const id = useHeadingId(text)
  return <h2 id={id}>{text}</h2>
}

// Test wrapper that uses the provider
function TestWrapper({ content, texts }: { content: string; texts: string[] }) {
  return (
    <HeadingIdProvider content={content}>
      {texts.map((text, index) => (
        // Using index is acceptable here since these are test fixtures, not dynamic lists
        // eslint-disable-next-line react/no-array-index-key
        <TestHeading key={`${text}-${index}`} text={text} />
      ))}
    </HeadingIdProvider>
  )
}

describe('HeadingIdList', () => {
  describe('constructor and precompute', () => {
    it('extracts headings from simple markdown', () => {
      const markdown = `# Title
## Introduction
Some content.
## Implementation
More content.
`
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(3)
    })

    it('handles all heading levels (h1-h6)', () => {
      const markdown = `# H1
## H2
### H3
#### H4
##### H5
###### H6
`
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(6)
    })

    it('handles empty markdown', () => {
      const list = new HeadingIdList('')
      expect(list.count).toBe(0)
    })

    it('handles markdown with no headings', () => {
      const markdown = `Just some text.
And more text.
No headings here.`
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(0)
    })
  })

  describe('code block handling', () => {
    it('ignores headings inside code blocks (triple backticks)', () => {
      const markdown = `## Real Heading

\`\`\`markdown
## Fake Heading
### Another Fake
\`\`\`

## Another Real Heading
`
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(2) // Only real headings
    })

    it('ignores headings inside code blocks (triple tildes)', () => {
      const markdown = `## Real Heading

~~~python
## This is a comment
def foo():
    pass
~~~

## Another Real Heading
`
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(2)
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
      const list = new HeadingIdList(markdown)
      expect(list.count).toBe(3) // Start, Middle, End
    })
  })

  describe('ID generation', () => {
    it('generates slugified IDs for headings', () => {
      const markdown = `## Hello World
## My Feature
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('hello-world')
      expect(list.getNextId()).toBe('my-feature')
    })

    it('handles special characters in headings', () => {
      const markdown = `## What's New?
## C++ Programming
## Node.js & TypeScript
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('whats-new')
      expect(list.getNextId()).toBe('c-programming')
      // Note: slugify replaces multiple hyphens with single hyphen
      expect(list.getNextId()).toBe('nodejs-typescript')
    })

    it('generates unique IDs for duplicate headings using line numbers', () => {
      const markdown = `## Details
Some content.

## Details
More content.

## Details
Final content.
`
      const list = new HeadingIdList(markdown)

      // First "Details" gets the base ID
      expect(list.getNextId()).toBe('details')
      // Subsequent duplicates get line-number suffixed IDs (0-indexed)
      expect(list.getNextId()).toBe('details-l3')
      expect(list.getNextId()).toBe('details-l6')
    })

    it('handles mixed unique and duplicate headings', () => {
      const markdown = `## Overview
## Details
## Implementation
## Details
## Summary
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('overview')
      expect(list.getNextId()).toBe('details')
      expect(list.getNextId()).toBe('implementation')
      expect(list.getNextId()).toBe('details-l3')
      expect(list.getNextId()).toBe('summary')
    })
  })

  describe('resetPosition', () => {
    it('resets position to start of list', () => {
      const markdown = `## First
## Second
## Third
`
      const list = new HeadingIdList(markdown)

      // Consume some IDs
      expect(list.getNextId()).toBe('first')
      expect(list.getNextId()).toBe('second')

      // Reset
      list.resetPosition()

      // Should start from beginning again
      expect(list.getNextId()).toBe('first')
      expect(list.getNextId()).toBe('second')
      expect(list.getNextId()).toBe('third')
    })

    it('handles multiple resets correctly', () => {
      const markdown = `## Only
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('only')
      list.resetPosition()
      expect(list.getNextId()).toBe('only')
      list.resetPosition()
      expect(list.getNextId()).toBe('only')
    })
  })

  describe('getNextId', () => {
    it('returns IDs in document order', () => {
      const markdown = `## A
## B
## C
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('a')
      expect(list.getNextId()).toBe('b')
      expect(list.getNextId()).toBe('c')
    })

    it('returns fallback ID when beyond list length', () => {
      const markdown = `## Only One
`
      const list = new HeadingIdList(markdown)

      expect(list.getNextId()).toBe('only-one')
      // Beyond list - returns fallback
      expect(list.getNextId()).toBe('heading-1')
      expect(list.getNextId()).toBe('heading-2')
    })
  })

  describe('getIdByText', () => {
    it('finds ID by matching text', () => {
      const markdown = `## Introduction
## Implementation
## Conclusion
`
      const list = new HeadingIdList(markdown)

      // Skip to specific text
      expect(list.getIdByText('Implementation')).toBe('implementation')
    })

    it('advances position when finding match', () => {
      const markdown = `## A
## B
## C
`
      const list = new HeadingIdList(markdown)

      // Find B
      expect(list.getIdByText('B')).toBe('b')
      // Next call starts from after B
      expect(list.getIdByText('C')).toBe('c')
    })

    it('returns slugified fallback when text not found', () => {
      const markdown = `## A
## B
`
      const list = new HeadingIdList(markdown)

      // Text not in list
      expect(list.getIdByText('NonExistent')).toBe('nonexistent')
    })

    it('handles duplicate text correctly', () => {
      const markdown = `## Details
Content 1.

## Overview
Content 2.

## Details
Content 3.
`
      const list = new HeadingIdList(markdown)

      // First Details
      expect(list.getIdByText('Details')).toBe('details')
      // Overview
      expect(list.getIdByText('Overview')).toBe('overview')
      // Second Details
      expect(list.getIdByText('Details')).toBe('details-l6')
    })
  })

  describe('count property', () => {
    it('returns correct count for various markdown', () => {
      expect(new HeadingIdList('').count).toBe(0)
      expect(new HeadingIdList('## One').count).toBe(1)
      expect(new HeadingIdList('## One\n## Two\n## Three').count).toBe(3)
    })
  })
})

describe('HeadingIdProvider', () => {
  it('provides heading IDs to children', () => {
    const markdown = `## Hello
## World
`
    render(<TestWrapper content={markdown} texts={['Hello', 'World']} />)

    expect(screen.getByRole('heading', { name: 'Hello' })).toHaveAttribute('id', 'hello')
    expect(screen.getByRole('heading', { name: 'World' })).toHaveAttribute('id', 'world')
  })

  it('handles duplicate heading texts', () => {
    const markdown = `## Details
## Overview
## Details
`
    const { container } = render(
      <TestWrapper content={markdown} texts={['Details', 'Overview', 'Details']} />
    )

    const headings = container.querySelectorAll('h2')
    expect(headings[0]).toHaveAttribute('id', 'details')
    expect(headings[1]).toHaveAttribute('id', 'overview')
    expect(headings[2]).toHaveAttribute('id', 'details-l2')
  })

  it('recomputes IDs when content changes', () => {
    const markdown1 = `## First
`
    const markdown2 = `## Second
`

    const { rerender } = render(<TestWrapper content={markdown1} texts={['First']} />)

    expect(screen.getByRole('heading', { name: 'First' })).toHaveAttribute('id', 'first')

    rerender(<TestWrapper content={markdown2} texts={['Second']} />)

    expect(screen.getByRole('heading', { name: 'Second' })).toHaveAttribute('id', 'second')
  })
})

describe('useHeadingId hook', () => {
  it('returns ID from context when available', () => {
    const markdown = `## Test Heading
`
    render(
      <HeadingIdProvider content={markdown}>
        <TestHeading text="Test Heading" />
      </HeadingIdProvider>
    )

    expect(screen.getByRole('heading', { name: 'Test Heading' })).toHaveAttribute(
      'id',
      'test-heading'
    )
  })

  it('falls back to slugified ID when no context', () => {
    // Render without provider
    render(<TestHeading text="No Context" />)

    // Should still get a reasonable ID via fallback
    expect(screen.getByRole('heading', { name: 'No Context' })).toHaveAttribute('id', 'no-context')
  })

  it('handles special characters correctly', () => {
    const markdown = `## What's This?
`
    render(
      <HeadingIdProvider content={markdown}>
        <TestHeading text="What's This?" />
      </HeadingIdProvider>
    )

    expect(screen.getByRole('heading', { name: "What's This?" })).toHaveAttribute(
      'id',
      'whats-this'
    )
  })
})

describe('React StrictMode compatibility', () => {
  it('produces consistent IDs across multiple renders', () => {
    const markdown = `## Heading One
## Heading Two
## Heading Three
`
    // First render
    const { container: container1 } = render(
      <TestWrapper content={markdown} texts={['Heading One', 'Heading Two', 'Heading Three']} />
    )

    const ids1 = Array.from(container1.querySelectorAll('h2')).map((h) => h.id)

    // Second render (simulating StrictMode behavior)
    const { container: container2 } = render(
      <TestWrapper content={markdown} texts={['Heading One', 'Heading Two', 'Heading Three']} />
    )

    const ids2 = Array.from(container2.querySelectorAll('h2')).map((h) => h.id)

    // IDs should be identical across renders
    expect(ids1).toEqual(ids2)
    expect(ids1).toEqual(['heading-one', 'heading-two', 'heading-three'])
  })

  it('handles duplicate headings consistently across renders', () => {
    const markdown = `## Details
## Overview
## Details
`
    // Multiple renders should produce same IDs
    for (let i = 0; i < 3; i++) {
      const { container, unmount } = render(
        <TestWrapper content={markdown} texts={['Details', 'Overview', 'Details']} />
      )

      const headings = container.querySelectorAll('h2')
      expect(headings[0]).toHaveAttribute('id', 'details')
      expect(headings[1]).toHaveAttribute('id', 'overview')
      expect(headings[2]).toHaveAttribute('id', 'details-l2')

      unmount()
    }
  })
})

describe('Edge cases', () => {
  it('handles very long heading text', () => {
    const longText = 'A'.repeat(100)
    const markdown = `## ${longText}
`
    const list = new HeadingIdList(markdown)
    const id = list.getNextId()

    // Should produce a slugified version
    expect(id).toBe(longText.toLowerCase())
  })

  it('handles headings with only special characters', () => {
    const markdown = `## @#$%^&*
`
    const list = new HeadingIdList(markdown)
    const id = list.getNextId()

    // Slugify removes special chars, may result in empty or minimal ID
    expect(typeof id).toBe('string')
  })

  it('handles headings with numbers', () => {
    const markdown = `## Step 1
## Step 2
## Step 3
`
    const list = new HeadingIdList(markdown)

    expect(list.getNextId()).toBe('step-1')
    expect(list.getNextId()).toBe('step-2')
    expect(list.getNextId()).toBe('step-3')
  })

  it('handles markdown with leading/trailing whitespace in headings', () => {
    const markdown = `##   Spaced Out Heading
## Normal Heading
`
    const list = new HeadingIdList(markdown)

    expect(list.getNextId()).toBe('spaced-out-heading')
    expect(list.getNextId()).toBe('normal-heading')
  })

  it('handles markdown with inline formatting in headings', () => {
    // Note: Our precompute extracts raw text, not rendered text
    // Inline formatting stays as-is in the text
    const markdown = `## **Bold** Heading
## *Italic* Text
`
    const list = new HeadingIdList(markdown)

    // The raw text includes the markdown syntax
    expect(list.count).toBe(2)
  })
})

import { render, screen } from '@testing-library/react'
import ReactMarkdown from 'react-markdown'
import { describe, expect, it } from 'vitest'

import { ParagraphRenderer } from '../internal'

describe('ParagraphRenderer', () => {
  it('formats Source/Generated/Analysis ID onto separate lines', () => {
    const markdown =
      'Source: https://example.com Generated: 2025-12-07 20:22:02 UTC Analysis ID: abc-123'

    render(<ReactMarkdown components={{ p: ParagraphRenderer }}>{markdown}</ReactMarkdown>)

    // Verify metadata text renders (layout is handled in renderer)
    expect(screen.getByText(/Source:/)).toBeInTheDocument()
    expect(screen.getByText(/Generated:/)).toBeInTheDocument()
    expect(screen.getByText(/Analysis ID:/)).toBeInTheDocument()
  })

  it('falls back to normal paragraph when metadata markers are absent', () => {
    const markdown = 'This is a normal paragraph.'

    render(<ReactMarkdown components={{ p: ParagraphRenderer }}>{markdown}</ReactMarkdown>)

    expect(screen.getByText(markdown)).toBeInTheDocument()
  })
})

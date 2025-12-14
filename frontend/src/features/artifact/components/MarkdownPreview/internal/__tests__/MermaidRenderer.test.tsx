import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { MermaidRenderer } from '../MermaidRenderer'

// Mock mermaid library
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({
      svg: '<svg data-testid="mermaid-svg">Mock SVG</svg>',
    }),
  },
}))

describe('MermaidRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render mermaid diagram container', () => {
    const code = 'graph TD; A-->B;'
    render(<MermaidRenderer code={code} />)

    const container = screen.getByTestId('mermaid-diagram')
    expect(container).toBeInTheDocument()
    expect(container).toHaveClass('mermaid-container')
  })

  it('should render SVG content from mermaid', async () => {
    const code = 'graph TD; A-->B;'
    render(<MermaidRenderer code={code} />)

    await waitFor(() => {
      const container = screen.getByTestId('mermaid-diagram')
      expect(container.innerHTML).toContain('svg')
    })
  })

  it('should apply custom className', () => {
    const code = 'graph TD; A-->B;'
    const customClass = 'custom-class'
    render(<MermaidRenderer code={code} className={customClass} />)

    const container = screen.getByTestId('mermaid-diagram')
    expect(container).toHaveClass(customClass)
  })

  it('should not render if code is empty', () => {
    const code = ''
    render(<MermaidRenderer code={code} />)

    const container = screen.getByTestId('mermaid-diagram')
    expect(container.innerHTML).toBe('')
  })
})

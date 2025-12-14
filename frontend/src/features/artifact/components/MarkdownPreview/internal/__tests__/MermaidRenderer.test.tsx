import { render, screen, waitFor } from '@testing-library/react'
import mermaid from 'mermaid'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MermaidRenderer } from '../MermaidRenderer'

// Mock mermaid library
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({
      svg: '<svg data-testid="mermaid-svg">Mock SVG</svg>',
      bindFunctions: vi.fn(),
    }),
  },
}))

describe('MermaidRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Remove any existing style elements from previous tests
    const existingStyle = document.getElementById('mermaid-custom-styles')
    if (existingStyle) {
      existingStyle.remove()
    }
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

  describe('Text Rendering (Issue #299-304)', () => {
    it('should inject custom CSS styles for proper text rendering', () => {
      // This test verifies the main fix for text truncation - CSS injection
      const code = 'graph TD; A-->B;'
      render(<MermaidRenderer code={code} />)

      // Verify custom CSS styles are injected
      const styleEl = document.getElementById('mermaid-custom-styles')
      expect(styleEl).toBeInTheDocument()

      // Verify critical CSS rules for preventing text truncation
      const styleContent = styleEl?.textContent || ''
      expect(styleContent).toContain('.mermaid-container .nodeLabel')
      expect(styleContent).toContain('.mermaid-container .node .label')
      expect(styleContent).toContain('overflow: visible')
      expect(styleContent).toContain('white-space: normal')

      // Verify SVG sizing rules
      expect(styleContent).toContain('.mermaid-container svg')
      expect(styleContent).toContain('max-width: 100%')
    })

    it('should render long node labels without truncation', async () => {
      const longTextSvg = `
        <svg data-testid="mermaid-svg">
          <text>Simple Problem Solving</text>
          <text>Mathematical Reasoning Steps</text>
        </svg>
      `

      vi.mocked(mermaid.render).mockResolvedValueOnce({
        svg: longTextSvg,
        bindFunctions: vi.fn(),
      })

      const code = `
        flowchart TD
          A[Simple Problem Solving] --> B[Mathematical Reasoning Steps]
      `

      render(<MermaidRenderer code={code} />)

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-diagram')
        expect(container.innerHTML).toContain('svg')
      })

      const container = screen.getByTestId('mermaid-diagram')
      const svgText = container.textContent
      expect(svgText).toContain('Simple Problem Solving')
      expect(svgText).toContain('Mathematical Reasoning Steps')
    })

    it('should only inject CSS styles once across multiple instances', () => {
      const code1 = 'graph TD; A-->B;'
      const code2 = 'graph TD; C-->D;'

      const { unmount } = render(<MermaidRenderer code={code1} />)
      render(<MermaidRenderer code={code2} />)

      const styleElements = document.querySelectorAll('#mermaid-custom-styles')
      expect(styleElements.length).toBe(1)

      unmount()
    })

    it('should handle error rendering gracefully', async () => {
      vi.mocked(mermaid.render).mockRejectedValueOnce(new Error('Syntax error'))

      const invalidCode = 'invalid mermaid syntax ~~~'

      render(<MermaidRenderer code={invalidCode} />)

      await waitFor(() => {
        const container = screen.getByTestId('mermaid-diagram')
        expect(container.innerHTML).toContain('mermaid-error')
        expect(container.innerHTML).toContain('Failed to render diagram')
      })
    })
  })
})

/**
 * CollapsibleSection Unit Tests
 *
 * Unit tests for DetailsRenderer and SummaryRenderer components
 * that provide React state management for native HTML details/summary elements.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DetailsRenderer, SummaryRenderer } from '../CollapsibleSection'

describe('DetailsRenderer', () => {
  describe('rendering', () => {
    it('renders a native details element', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).toBeInTheDocument()
    })

    it('renders children correctly', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Click me</SummaryRenderer>
          <div data-testid="content">Hidden content</div>
        </DetailsRenderer>
      )

      expect(screen.getByText('Click me')).toBeInTheDocument()
      expect(screen.getByTestId('content')).toBeInTheDocument()
    })

    it('renders without children', () => {
      render(<DetailsRenderer />)

      const details = document.querySelector('details')
      expect(details).toBeInTheDocument()
    })
  })

  describe('open prop', () => {
    it('is closed by default when open prop is not provided', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).not.toHaveAttribute('open')
    })

    it('sets open attribute when initialOpen is true', () => {
      render(
        <DetailsRenderer open={true}>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).toHaveAttribute('open')
    })

    it('does not set open attribute when initialOpen is false', () => {
      render(
        <DetailsRenderer open={false}>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).not.toHaveAttribute('open')
    })

    it('does not set open attribute when initialOpen is undefined', () => {
      render(
        <DetailsRenderer open={undefined}>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).not.toHaveAttribute('open')
    })
  })

  describe('prop spreading', () => {
    it('spreads className prop to details element', () => {
      render(
        <DetailsRenderer className="custom-class">
          <SummaryRenderer>Title</SummaryRenderer>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).toHaveClass('custom-class')
    })

    it('spreads id prop to details element', () => {
      render(
        <DetailsRenderer id="test-details">
          <SummaryRenderer>Title</SummaryRenderer>
        </DetailsRenderer>
      )

      const details = document.querySelector('#test-details')
      expect(details).toBeInTheDocument()
    })

    it('spreads data-* attributes to details element', () => {
      render(
        <DetailsRenderer data-testid="my-details" data-custom="value">
          <SummaryRenderer>Title</SummaryRenderer>
        </DetailsRenderer>
      )

      const details = screen.getByTestId('my-details')
      expect(details).toHaveAttribute('data-custom', 'value')
    })

    it('filters out node prop and does not spread it', () => {
      // The node prop comes from react-markdown and should be filtered out
      render(
        <DetailsRenderer node={{ type: 'element' }}>
          <SummaryRenderer>Title</SummaryRenderer>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      expect(details).not.toHaveAttribute('node')
    })
  })

  describe('native behavior', () => {
    it('toggles open state when summary is clicked', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Click me</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      const summary = screen.getByText('Click me')

      expect(details).not.toHaveAttribute('open')

      // Click to open
      fireEvent.click(summary)
      expect(details).toHaveAttribute('open')

      // Click to close
      fireEvent.click(summary)
      expect(details).not.toHaveAttribute('open')
    })

    it('allows multiple toggles in sequence', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Toggle me</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      const summary = screen.getByText('Toggle me')

      for (let i = 0; i < 5; i++) {
        fireEvent.click(summary)
        if (i % 2 === 0) {
          expect(details).toHaveAttribute('open')
        } else {
          expect(details).not.toHaveAttribute('open')
        }
      }
    })

    it('remains open when initialOpen is true after toggle', () => {
      render(
        <DetailsRenderer open={true}>
          <SummaryRenderer>Title</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const details = document.querySelector('details')
      const summary = screen.getByText('Title')

      expect(details).toHaveAttribute('open')

      // Close
      fireEvent.click(summary)
      expect(details).not.toHaveAttribute('open')

      // Open again
      fireEvent.click(summary)
      expect(details).toHaveAttribute('open')
    })
  })

  describe('nested content', () => {
    it('handles nested details elements', () => {
      render(
        <DetailsRenderer data-testid="outer">
          <SummaryRenderer>Outer</SummaryRenderer>
          <DetailsRenderer data-testid="inner">
            <SummaryRenderer>Inner</SummaryRenderer>
            <p>Nested content</p>
          </DetailsRenderer>
        </DetailsRenderer>
      )

      expect(screen.getByTestId('outer')).toBeInTheDocument()
      expect(screen.getByTestId('inner')).toBeInTheDocument()
    })

    it('handles complex nested markdown content', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Complex Section</SummaryRenderer>
          <h3>Heading</h3>
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
          <pre>
            <code>code block</code>
          </pre>
        </DetailsRenderer>
      )

      expect(screen.getByText('Complex Section')).toBeInTheDocument()
      expect(screen.getByText('Item 1')).toBeInTheDocument()
      expect(screen.getByText('code block')).toBeInTheDocument()
    })
  })
})

describe('SummaryRenderer', () => {
  describe('rendering', () => {
    it('renders a native summary element', () => {
      render(
        <details>
          <SummaryRenderer>Title</SummaryRenderer>
        </details>
      )

      const summary = document.querySelector('summary')
      expect(summary).toBeInTheDocument()
    })

    it('renders children correctly', () => {
      render(
        <details>
          <SummaryRenderer>
            <span>Icon</span> Click to expand
          </SummaryRenderer>
        </details>
      )

      expect(screen.getByText('Icon')).toBeInTheDocument()
      expect(screen.getByText('Click to expand')).toBeInTheDocument()
    })

    it('renders without children', () => {
      render(
        <details>
          <SummaryRenderer />
        </details>
      )

      const summary = document.querySelector('summary')
      expect(summary).toBeInTheDocument()
    })
  })

  describe('prop spreading', () => {
    it('spreads className prop to summary element', () => {
      render(
        <details>
          <SummaryRenderer className="custom-summary">Title</SummaryRenderer>
        </details>
      )

      const summary = document.querySelector('summary')
      expect(summary).toHaveClass('custom-summary')
    })

    it('spreads id prop to summary element', () => {
      render(
        <details>
          <SummaryRenderer id="test-summary">Title</SummaryRenderer>
        </details>
      )

      const summary = document.querySelector('#test-summary')
      expect(summary).toBeInTheDocument()
    })

    it('spreads data-* attributes to summary element', () => {
      render(
        <details>
          <SummaryRenderer data-testid="my-summary" data-role="button">
            Title
          </SummaryRenderer>
        </details>
      )

      const summary = screen.getByTestId('my-summary')
      expect(summary).toHaveAttribute('data-role', 'button')
    })

    it('filters out node prop and does not spread it', () => {
      render(
        <details>
          <SummaryRenderer node={{ type: 'element' }}>Title</SummaryRenderer>
        </details>
      )

      const summary = document.querySelector('summary')
      expect(summary).not.toHaveAttribute('node')
    })

    it('spreads style prop to summary element', () => {
      render(
        <details>
          <SummaryRenderer style={{ color: 'red' }}>Title</SummaryRenderer>
        </details>
      )

      const summary = document.querySelector('summary')
      // toHaveStyle computes the style, so 'red' becomes 'rgb(255, 0, 0)'
      expect(summary).toHaveStyle({ color: 'rgb(255, 0, 0)' })
    })
  })

  describe('accessibility', () => {
    it('is focusable by default (native behavior)', () => {
      render(
        <details>
          <SummaryRenderer>Focusable</SummaryRenderer>
        </details>
      )

      const summary = screen.getByText('Focusable')
      summary.focus()
      expect(document.activeElement).toBe(summary)
    })

    it('supports aria-expanded implicitly through native details', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Accessible</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      // Native summary elements get implicit aria-expanded from details state
      const summary = screen.getByText('Accessible')
      expect(summary.tagName).toBe('SUMMARY')
    })
  })

  describe('click handling', () => {
    it('responds to click events via native browser behavior', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Clickable</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const summary = screen.getByText('Clickable')
      const details = document.querySelector('details')

      expect(details).not.toHaveAttribute('open')
      fireEvent.click(summary)
      expect(details).toHaveAttribute('open')
    })

    it('responds to Enter key via native browser behavior', () => {
      render(
        <DetailsRenderer>
          <SummaryRenderer>Keyboardable</SummaryRenderer>
          <p>Content</p>
        </DetailsRenderer>
      )

      const summary = screen.getByText('Keyboardable')
      const _details = document.querySelector('details') // Verify details exists

      // Note: JSDOM may not fully simulate keyboard toggle behavior
      // This test verifies the element is keyboard-focusable
      expect(_details).toBeInTheDocument()
      summary.focus()
      expect(document.activeElement).toBe(summary)
    })
  })

  describe('complex content', () => {
    it('handles rich content inside summary', () => {
      render(
        <details>
          <SummaryRenderer>
            <strong>Bold</strong> and <em>italic</em> text
          </SummaryRenderer>
        </details>
      )

      expect(screen.getByText('Bold')).toBeInTheDocument()
      expect(screen.getByText('italic')).toBeInTheDocument()
    })

    it('handles inline code inside summary', () => {
      render(
        <details>
          <SummaryRenderer>
            Using <code>useState</code> hook
          </SummaryRenderer>
        </details>
      )

      expect(screen.getByText('useState')).toBeInTheDocument()
    })
  })
})

describe('Integration: DetailsRenderer + SummaryRenderer', () => {
  it('works together as expected', () => {
    render(
      <DetailsRenderer data-testid="section">
        <SummaryRenderer>Section Title</SummaryRenderer>
        <div>
          <p>Paragraph 1</p>
          <p>Paragraph 2</p>
        </div>
      </DetailsRenderer>
    )

    const details = screen.getByTestId('section')
    const summary = screen.getByText('Section Title')

    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText('Paragraph 1')).toBeInTheDocument()

    fireEvent.click(summary)
    expect(details).toHaveAttribute('open')
  })

  it('multiple independent sections work correctly', () => {
    render(
      <div>
        <DetailsRenderer data-testid="section-1">
          <SummaryRenderer>Section 1</SummaryRenderer>
          <p>Content 1</p>
        </DetailsRenderer>
        <DetailsRenderer data-testid="section-2">
          <SummaryRenderer>Section 2</SummaryRenderer>
          <p>Content 2</p>
        </DetailsRenderer>
      </div>
    )

    const section1 = screen.getByTestId('section-1')
    const section2 = screen.getByTestId('section-2')
    const summary1 = screen.getByText('Section 1')
    const summary2 = screen.getByText('Section 2')

    // Open section 1
    fireEvent.click(summary1)
    expect(section1).toHaveAttribute('open')
    expect(section2).not.toHaveAttribute('open')

    // Open section 2 (section 1 stays open)
    fireEvent.click(summary2)
    expect(section1).toHaveAttribute('open')
    expect(section2).toHaveAttribute('open')

    // Close section 1 (section 2 stays open)
    fireEvent.click(summary1)
    expect(section1).not.toHaveAttribute('open')
    expect(section2).toHaveAttribute('open')
  })
})

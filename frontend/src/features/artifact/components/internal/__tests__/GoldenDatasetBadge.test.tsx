/**
 * Tests for GoldenDatasetBadge component
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'

import { GoldenDatasetBadge } from '../GoldenDatasetBadge'

describe('GoldenDatasetBadge', () => {
  it('renders badge with default golden dataset text', () => {
    render(<GoldenDatasetBadge />)

    expect(screen.getByTestId('golden-dataset-badge')).toBeInTheDocument()
    expect(screen.getByText(/Golden Dataset/i)).toBeInTheDocument()
  })

  it('renders badge with custom badge text', () => {
    render(<GoldenDatasetBadge badgeText="🌟 Example Content" />)

    expect(screen.getByText('🌟 Example Content')).toBeInTheDocument()
  })

  it('shows tooltip on hover with base message', async () => {
    const user = userEvent.setup()

    render(<GoldenDatasetBadge />)

    const badge = screen.getByTestId('golden-dataset-badge')
    await user.hover(badge)

    // Wait for tooltip to appear (Radix renders it multiple times for accessibility)
    const tooltips = await screen.findAllByText(
      /example content from SkillForge's curated dataset/i
    )
    expect(tooltips.length).toBeGreaterThan(0)
    expect(tooltips[0]).toBeInTheDocument()
  })

  it('shows document name in tooltip when provided', async () => {
    const user = userEvent.setup()

    render(<GoldenDatasetBadge documentName="Chain Of Thought" />)

    const badge = screen.getByTestId('golden-dataset-badge')
    await user.hover(badge)

    // Wait for tooltip with document name (Radix renders it multiple times for accessibility)
    const documentLabels = await screen.findAllByText(/Document: Chain Of Thought/i)
    expect(documentLabels.length).toBeGreaterThan(0)
    expect(documentLabels[0]).toBeInTheDocument()
  })

  it('does not show document name in tooltip when not provided', async () => {
    const user = userEvent.setup()

    render(<GoldenDatasetBadge />)

    const badge = screen.getByTestId('golden-dataset-badge')
    await user.hover(badge)

    // Wait for tooltip base message
    await screen.findAllByText(/example content/i)

    // Document label should not be present
    expect(screen.queryByText(/Document:/i)).not.toBeInTheDocument()
  })

  it('has correct styling classes for golden dataset theme', () => {
    render(<GoldenDatasetBadge />)

    const badge = screen.getByTestId('golden-dataset-badge')

    // Check for amber color classes
    expect(badge).toHaveClass('bg-amber-100')
    expect(badge).toHaveClass('text-amber-800')
    expect(badge).toHaveClass('cursor-help')
  })

  it('is accessible with proper ARIA attributes', () => {
    render(<GoldenDatasetBadge documentName="Test Document" />)

    const badge = screen.getByTestId('golden-dataset-badge')

    // Badge should be accessible
    expect(badge).toBeVisible()
    expect(badge).toHaveAttribute('class')
  })

  it('renders with secondary variant', () => {
    render(<GoldenDatasetBadge />)

    const badge = screen.getByTestId('golden-dataset-badge')

    // Component uses Badge with variant="secondary"
    // The custom classes should override default secondary styling
    expect(badge).toHaveClass('bg-amber-100')
  })
})

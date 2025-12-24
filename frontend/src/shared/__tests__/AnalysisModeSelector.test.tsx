/**
 * AnalysisModeSelector Unit Tests
 *
 * Tests for the accessible analysis mode selector component.
 * Verifies WCAG 2.1 compliance for radiogroup pattern.
 *
 * Issue #502: Analysis Mode Selector implementation
 */

import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AnalysisModeSelector, type AnalysisMode } from '../AnalysisModeSelector'

describe('AnalysisModeSelector', () => {
  const defaultProps = {
    value: 'standard' as AnalysisMode,
    onChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders all three mode options', () => {
      render(<AnalysisModeSelector {...defaultProps} />)

      expect(screen.getByText('Quick')).toBeInTheDocument()
      expect(screen.getByText('Standard')).toBeInTheDocument()
      expect(screen.getByText('Deep Dive')).toBeInTheDocument()
    })

    it('renders with correct test ID', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      expect(screen.getByTestId('analysis-mode-selector')).toBeInTheDocument()
    })

    it('displays the label "Analysis Depth"', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      expect(screen.getByText('Analysis Depth')).toBeInTheDocument()
    })

    it('shows time, agent count, and cost for each mode', () => {
      render(<AnalysisModeSelector {...defaultProps} />)

      // Quick mode details
      expect(screen.getByText(/~10s.*4 agents.*\$0.002/)).toBeInTheDocument()
      // Standard mode details
      expect(screen.getByText(/~30s.*8 agents.*\$0.035/)).toBeInTheDocument()
      // Deep Dive mode details
      expect(screen.getByText(/~60s.*12 agents.*\$0.055/)).toBeInTheDocument()
    })
  })

  describe('Selection Behavior', () => {
    it('marks the selected mode as active', () => {
      render(<AnalysisModeSelector value="quick" onChange={vi.fn()} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      expect(quickButton).toHaveAttribute('aria-checked', 'true')
      expect(quickButton).toHaveClass('analysis-mode-option--active')
    })

    it('calls onChange when a mode is clicked', async () => {
      const onChange = vi.fn()
      const user = userEvent.setup()
      render(<AnalysisModeSelector value="standard" onChange={onChange} />)

      const deepDiveButton = screen.getByRole('radio', { name: /Deep Dive/i })
      await user.click(deepDiveButton)

      expect(onChange).toHaveBeenCalledWith('deep_dive')
    })

    it('does not mark unselected modes as active', () => {
      render(<AnalysisModeSelector value="standard" onChange={vi.fn()} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      const deepDiveButton = screen.getByRole('radio', { name: /Deep Dive/i })

      expect(quickButton).toHaveAttribute('aria-checked', 'false')
      expect(deepDiveButton).toHaveAttribute('aria-checked', 'false')
      expect(quickButton).not.toHaveClass('analysis-mode-option--active')
      expect(deepDiveButton).not.toHaveClass('analysis-mode-option--active')
    })
  })

  describe('Accessibility (WCAG 2.1 Radiogroup Pattern)', () => {
    it('has correct radiogroup role on container', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      expect(screen.getByRole('radiogroup')).toBeInTheDocument()
    })

    it('has radio role on each option', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      const radios = screen.getAllByRole('radio')
      expect(radios).toHaveLength(3)
    })

    it('associates radiogroup with label via aria-labelledby', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      const radiogroup = screen.getByRole('radiogroup')
      expect(radiogroup).toHaveAttribute('aria-labelledby', 'analysis-mode-label')
    })

    it('has aria-describedby with hint text', () => {
      render(<AnalysisModeSelector {...defaultProps} />)
      const radiogroup = screen.getByRole('radiogroup')
      expect(radiogroup).toHaveAttribute('aria-describedby', 'analysis-mode-hint')
    })

    it('only selected option is focusable (roving tabindex)', () => {
      render(<AnalysisModeSelector value="standard" onChange={vi.fn()} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      const standardButton = screen.getByRole('radio', { name: /Standard/i })
      const deepDiveButton = screen.getByRole('radio', { name: /Deep Dive/i })

      // Only selected option has tabIndex 0
      expect(quickButton).toHaveAttribute('tabIndex', '-1')
      expect(standardButton).toHaveAttribute('tabIndex', '0')
      expect(deepDiveButton).toHaveAttribute('tabIndex', '-1')
    })

    it('icons are hidden from screen readers', () => {
      const { container } = render(<AnalysisModeSelector {...defaultProps} />)
      const icons = container.querySelectorAll('.analysis-mode-icon')
      expect(icons).toHaveLength(3)
      icons.forEach((icon) => {
        expect(icon).toHaveAttribute('aria-hidden', 'true')
      })
    })
  })

  describe('Keyboard Navigation', () => {
    it('navigates forward with ArrowRight', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="quick" onChange={onChange} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      fireEvent.keyDown(quickButton, { key: 'ArrowRight' })

      expect(onChange).toHaveBeenCalledWith('standard')
    })

    it('navigates forward with ArrowDown', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="quick" onChange={onChange} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      fireEvent.keyDown(quickButton, { key: 'ArrowDown' })

      expect(onChange).toHaveBeenCalledWith('standard')
    })

    it('navigates backward with ArrowLeft', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="standard" onChange={onChange} />)

      const standardButton = screen.getByRole('radio', { name: /Standard/i })
      fireEvent.keyDown(standardButton, { key: 'ArrowLeft' })

      expect(onChange).toHaveBeenCalledWith('quick')
    })

    it('navigates backward with ArrowUp', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="standard" onChange={onChange} />)

      const standardButton = screen.getByRole('radio', { name: /Standard/i })
      fireEvent.keyDown(standardButton, { key: 'ArrowUp' })

      expect(onChange).toHaveBeenCalledWith('quick')
    })

    it('wraps around from last to first with ArrowRight', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="deep_dive" onChange={onChange} />)

      const deepDiveButton = screen.getByRole('radio', { name: /Deep Dive/i })
      fireEvent.keyDown(deepDiveButton, { key: 'ArrowRight' })

      expect(onChange).toHaveBeenCalledWith('quick')
    })

    it('wraps around from first to last with ArrowLeft', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="quick" onChange={onChange} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      fireEvent.keyDown(quickButton, { key: 'ArrowLeft' })

      expect(onChange).toHaveBeenCalledWith('deep_dive')
    })

    it('jumps to first option with Home key', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="deep_dive" onChange={onChange} />)

      const deepDiveButton = screen.getByRole('radio', { name: /Deep Dive/i })
      fireEvent.keyDown(deepDiveButton, { key: 'Home' })

      expect(onChange).toHaveBeenCalledWith('quick')
    })

    it('jumps to last option with End key', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="quick" onChange={onChange} />)

      const quickButton = screen.getByRole('radio', { name: /Quick/i })
      fireEvent.keyDown(quickButton, { key: 'End' })

      expect(onChange).toHaveBeenCalledWith('deep_dive')
    })

    it('activates current option with Space key', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="standard" onChange={onChange} />)

      const standardButton = screen.getByRole('radio', { name: /Standard/i })
      fireEvent.keyDown(standardButton, { key: ' ' })

      expect(onChange).toHaveBeenCalledWith('standard')
    })

    it('activates current option with Enter key', async () => {
      const onChange = vi.fn()
      render(<AnalysisModeSelector value="standard" onChange={onChange} />)

      const standardButton = screen.getByRole('radio', { name: /Standard/i })
      fireEvent.keyDown(standardButton, { key: 'Enter' })

      expect(onChange).toHaveBeenCalledWith('standard')
    })
  })

  describe('Custom Label ID', () => {
    it('accepts custom labelId prop', () => {
      render(<AnalysisModeSelector {...defaultProps} labelId="custom-label-id" />)
      const label = document.getElementById('custom-label-id')
      expect(label).toBeInTheDocument()
      expect(label).toHaveTextContent('Analysis Depth')
    })
  })
})

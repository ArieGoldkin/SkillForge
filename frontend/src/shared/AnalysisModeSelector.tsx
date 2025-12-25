/**
 * Analysis Mode Selector Component
 * Allows users to select analysis depth (quick, standard, deep dive)
 *
 * Accessibility (WCAG 2.1 compliant):
 * - Uses radiogroup pattern with proper ARIA roles
 * - Arrow key navigation between options
 * - Visible focus indicators
 * - Screen reader announcements
 */

import { useCallback, useRef, type KeyboardEvent } from 'react'

import { Zap, Target, Microscope } from 'lucide-react'

import type { AnalysisMode } from '@/types/api'

import './AnalysisModeSelector.css'

interface AnalysisModeSelectorProps {
  value: AnalysisMode
  onChange: (mode: AnalysisMode) => void
  /** Optional ID for aria-labelledby on the radiogroup */
  labelId?: string
}

const ANALYSIS_MODES: {
  value: AnalysisMode
  label: string
  description: string
  icon: React.ComponentType<{ size?: number }>
  color: 'green' | 'teal' | 'purple'
}[] = [
  {
    value: 'quick',
    label: 'Quick',
    description: '~10s • 4 agents • $0.002',
    icon: Zap,
    color: 'green',
  },
  {
    value: 'standard',
    label: 'Standard',
    description: '~30s • 8 agents • $0.035',
    icon: Target,
    color: 'teal',
  },
  {
    value: 'deep_dive',
    label: 'Deep Dive',
    description: '~60s • 12 agents • $0.055',
    icon: Microscope,
    color: 'purple',
  },
]

const LABEL_ID = 'analysis-mode-label'

// eslint-disable-next-line max-lines-per-function -- Complex accessibility pattern requires keyboard navigation, ARIA roles, and roving tabindex
export function AnalysisModeSelector({
  value,
  onChange,
  labelId = LABEL_ID,
}: AnalysisModeSelectorProps) {
  const optionRefs = useRef<(HTMLButtonElement | null)[]>([])

  // Handle keyboard navigation (WCAG 2.1 radio group pattern)
  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
      const { key } = event
      let nextIndex: number | null = null

      switch (key) {
        case 'ArrowRight':
        case 'ArrowDown':
          event.preventDefault()
          nextIndex = (currentIndex + 1) % ANALYSIS_MODES.length
          break
        case 'ArrowLeft':
        case 'ArrowUp':
          event.preventDefault()
          nextIndex = (currentIndex - 1 + ANALYSIS_MODES.length) % ANALYSIS_MODES.length
          break
        case 'Home':
          event.preventDefault()
          nextIndex = 0
          break
        case 'End':
          event.preventDefault()
          nextIndex = ANALYSIS_MODES.length - 1
          break
        case ' ':
        case 'Enter':
          event.preventDefault()
          onChange(ANALYSIS_MODES[currentIndex].value)
          return
        default:
          return
      }

      if (nextIndex !== null) {
        // Move focus and select the new option
        optionRefs.current[nextIndex]?.focus()
        onChange(ANALYSIS_MODES[nextIndex].value)
      }
    },
    [onChange]
  )

  return (
    <div className="analysis-mode-selector" data-testid="analysis-mode-selector">
      <div id={labelId} className="analysis-mode-label">
        Analysis Depth
      </div>
      <div
        className="analysis-mode-options"
        role="radiogroup"
        aria-labelledby={labelId}
        aria-describedby="analysis-mode-hint"
      >
        <span id="analysis-mode-hint" className="visually-hidden">
          Use arrow keys to navigate between options
        </span>
        {ANALYSIS_MODES.map((mode, index) => {
          const Icon = mode.icon
          const isSelected = value === mode.value
          return (
            <button
              key={mode.value}
              ref={(el) => {
                optionRefs.current[index] = el
              }}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-describedby={`mode-desc-${mode.value}`}
              tabIndex={isSelected ? 0 : -1}
              className={`analysis-mode-option analysis-mode-option--${mode.color}${isSelected ? ' analysis-mode-option--active' : ''}`}
              onClick={() => onChange(mode.value)}
              onKeyDown={(e) => handleKeyDown(e, index)}
            >
              <span className="analysis-mode-icon" aria-hidden="true">
                <Icon size={28} />
              </span>
              <span className="analysis-mode-text">
                <strong>{mode.label}</strong>
                <small id={`mode-desc-${mode.value}`}>{mode.description}</small>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

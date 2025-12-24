/**
 * Analysis Mode Selector Component
 * Allows users to select analysis depth (quick, standard, deep dive)
 */

import { Zap, Target, Microscope } from 'lucide-react'
import './AnalysisModeSelector.css'

export type AnalysisMode = 'quick' | 'standard' | 'deep_dive'

interface AnalysisModeSelectorProps {
  value: AnalysisMode
  onChange: (mode: AnalysisMode) => void
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

export function AnalysisModeSelector({ value, onChange }: AnalysisModeSelectorProps) {
  return (
    <div className="analysis-mode-selector" data-testid="analysis-mode-selector">
      <div className="analysis-mode-label">Analysis Depth</div>
      <div className="analysis-mode-options">
        {ANALYSIS_MODES.map((mode) => {
          const Icon = mode.icon
          return (
            <button
              key={mode.value}
              type="button"
              className={`analysis-mode-option analysis-mode-option--${mode.color}${value === mode.value ? ' analysis-mode-option--active' : ''}`}
              onClick={() => onChange(mode.value)}
              aria-pressed={value === mode.value}
            >
              <span className="analysis-mode-icon">
                <Icon size={28} />
              </span>
              <span className="analysis-mode-text">
                <strong>{mode.label}</strong>
                <small>{mode.description}</small>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

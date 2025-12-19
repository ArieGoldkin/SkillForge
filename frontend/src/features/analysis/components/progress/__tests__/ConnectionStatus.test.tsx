import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { LoadingState } from '@types/loading'

import { ConnectionStatus } from '../ConnectionStatus'

describe('ConnectionStatus', () => {
  const renderComponent = (loadingState: LoadingState) => {
    return render(<ConnectionStatus loadingState={loadingState} />)
  }

  it('displays connecting state', () => {
    renderComponent({ type: 'connecting', startTime: Date.now() })

    expect(screen.getByText('Connecting...')).toBeInTheDocument()
    // Should have spinner icon
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('displays connected state', () => {
    renderComponent({ type: 'connected' })

    expect(screen.getByText('Connected')).toBeInTheDocument()
    // Should have wifi icon (not spinner)
    const wifiIcon = document.querySelector('svg') // Lucide icons are SVG
    expect(wifiIcon).toBeInTheDocument()
    expect(wifiIcon?.parentElement).not.toHaveClass('animate-spin')
  })

  it('displays reconnecting state with attempts', () => {
    renderComponent({ type: 'reconnecting', attempts: 2 })

    expect(screen.getByText('Reconnecting... (2/3)')).toBeInTheDocument()
    // Should have spinner
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('displays timeout warning state', () => {
    renderComponent({ type: 'timeout_warning', connectedAt: Date.now() })

    expect(screen.getByText('Connection timeout')).toBeInTheDocument()
    // Should have alert triangle icon
    const alertIcon = document.querySelector('svg') // AlertTriangle icon
    expect(alertIcon).toBeInTheDocument()
  })

  it('displays disconnected state', () => {
    renderComponent({ type: 'disconnected' })

    expect(screen.getByText('Disconnected')).toBeInTheDocument()
    // Should have wifi-off icon
    const wifiOffIcon = document.querySelector('svg')
    expect(wifiOffIcon).toBeInTheDocument()
  })

  it('applies correct styling for connected state', () => {
    renderComponent({ type: 'connected' })

    const container = screen.getByText('Connected').parentElement
    expect(container).toHaveClass('text-status-success') // semantic status color
  })

  it('applies correct styling for timeout warning', () => {
    renderComponent({ type: 'timeout_warning', connectedAt: Date.now() })

    const container = screen.getByText('Connection timeout').parentElement
    expect(container).toHaveClass('text-orange-600')
  })

  it('applies correct styling for disconnected state', () => {
    renderComponent({ type: 'disconnected' })

    const container = screen.getByText('Disconnected').parentElement
    expect(container).toHaveClass('text-muted-foreground')
  })
})

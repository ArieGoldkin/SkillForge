/**
 * Tests for ErrorBoundary component
 *
 * Validates:
 * - Error catching and fallback rendering
 * - Reset functionality
 * - Custom fallback support (ReactNode and render prop)
 * - Error callback firing
 * - Default fallback UI
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import { ErrorBoundary } from '../ErrorBoundary'

// Component that throws an error
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>Rendered successfully</div>
}

// Suppress console.error during tests since error boundaries log errors
const originalError = console.error
beforeEach(() => {
  console.error = vi.fn()
})
afterEach(() => {
  console.error = originalError
})

describe('ErrorBoundary', () => {
  describe('error catching', () => {
    it('catches errors and renders default fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Something went wrong')).toBeInTheDocument()
      expect(screen.getByText('Try Again')).toBeInTheDocument()
      expect(screen.getByText('Refresh Page')).toBeInTheDocument()
    })

    it('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </ErrorBoundary>
      )

      expect(screen.getByText('Rendered successfully')).toBeInTheDocument()
      expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
    })

    it('shows error message in dev mode', () => {
      // import.meta.env.DEV is true in test environment
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Test error message')).toBeInTheDocument()
    })
  })

  describe('custom fallback', () => {
    it('renders custom ReactNode fallback', () => {
      render(
        <ErrorBoundary fallback={<div>Custom error UI</div>}>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Custom error UI')).toBeInTheDocument()
      expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
    })

    it('renders render prop fallback with error and reset function', () => {
      render(
        <ErrorBoundary
          fallback={({ error, resetError }) => (
            <div>
              <span data-testid="error-message">{error.message}</span>
              <button type="button" onClick={resetError}>
                Custom Reset
              </button>
            </div>
          )}
        >
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(screen.getByTestId('error-message')).toHaveTextContent('Test error message')
      expect(screen.getByText('Custom Reset')).toBeInTheDocument()
    })
  })

  describe('reset functionality', () => {
    it('clears error state when reset is called', () => {
      // Use a component that can toggle throwing
      let shouldThrow = true
      function ToggleThrowComponent() {
        if (shouldThrow) {
          throw new Error('Toggle error')
        }
        return <div>No error</div>
      }

      const { rerender } = render(
        <ErrorBoundary
          fallback={({ resetError }) => (
            <button
              type="button"
              onClick={() => {
                shouldThrow = false
                resetError()
              }}
            >
              Reset
            </button>
          )}
        >
          <ToggleThrowComponent />
        </ErrorBoundary>
      )

      // Initially shows error state
      expect(screen.getByText('Reset')).toBeInTheDocument()

      // Click reset and re-render
      fireEvent.click(screen.getByText('Reset'))
      rerender(
        <ErrorBoundary
          fallback={({ resetError }) => (
            <button
              type="button"
              onClick={() => {
                shouldThrow = false
                resetError()
              }}
            >
              Reset
            </button>
          )}
        >
          <ToggleThrowComponent />
        </ErrorBoundary>
      )

      // Now shows successful render
      expect(screen.getByText('No error')).toBeInTheDocument()
    })
  })

  describe('error callback', () => {
    it('calls onError callback when error is caught', () => {
      const onError = vi.fn()

      render(
        <ErrorBoundary onError={onError}>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(onError).toHaveBeenCalledTimes(1)
      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      )
      expect(onError.mock.calls[0][0].message).toBe('Test error message')
    })

    it('includes boundary name in console log', () => {
      render(
        <ErrorBoundary name="TestBoundary">
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(console.error).toHaveBeenCalledWith(
        '[TestBoundary] Caught error:',
        expect.any(Error),
        expect.any(Object)
      )
    })
  })

  describe('default fallback UI', () => {
    it('has Try Again button that triggers reset', () => {
      let shouldThrow = true
      function ToggleComponent() {
        if (shouldThrow) throw new Error('Error')
        return <div>Success</div>
      }

      const { rerender } = render(
        <ErrorBoundary>
          <ToggleComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Something went wrong')).toBeInTheDocument()

      // Click Try Again
      shouldThrow = false
      fireEvent.click(screen.getByText('Try Again'))

      rerender(
        <ErrorBoundary>
          <ToggleComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Success')).toBeInTheDocument()
    })

    it('has Refresh Page button', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent />
        </ErrorBoundary>
      )

      expect(screen.getByText('Refresh Page')).toBeInTheDocument()
    })
  })

  describe('nested error boundaries', () => {
    it('inner boundary catches errors before outer', () => {
      render(
        <ErrorBoundary fallback={<div>Outer caught</div>}>
          <div>
            <ErrorBoundary fallback={<div>Inner caught</div>}>
              <ThrowingComponent />
            </ErrorBoundary>
          </div>
        </ErrorBoundary>
      )

      expect(screen.getByText('Inner caught')).toBeInTheDocument()
      expect(screen.queryByText('Outer caught')).not.toBeInTheDocument()
    })
  })
})

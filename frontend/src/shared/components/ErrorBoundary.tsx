/* eslint-disable react-refresh/only-export-components -- DefaultErrorFallback is intentionally internal */
import { Component, type ErrorInfo, type ReactNode } from 'react'

import { AlertCircle, RefreshCw } from 'lucide-react'

import { Button } from '@shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

export interface ErrorFallbackProps {
  error: Error
  resetError: () => void
}

interface ErrorBoundaryProps {
  children: ReactNode
  /** Custom fallback UI - can be a ReactNode or render function */
  fallback?: ReactNode | ((props: ErrorFallbackProps) => ReactNode)
  /** Callback fired when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  /** Optional name for logging purposes */
  name?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

/**
 * Reusable error boundary component that catches React render errors.
 *
 * Features:
 * - Prevents white screen of death by catching errors in child tree
 * - Supports custom fallback UI via ReactNode or render prop
 * - Reset functionality to retry rendering
 * - Optional error callback for logging/monitoring
 *
 * @example
 * // With default fallback
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * @example
 * // With custom fallback component
 * <ErrorBoundary fallback={<CustomErrorUI />}>
 *   <MyComponent />
 * </ErrorBoundary>
 *
 * @example
 * // With render prop for reset functionality
 * <ErrorBoundary fallback={({ error, resetError }) => (
 *   <div>
 *     <p>Error: {error.message}</p>
 *     <button onClick={resetError}>Try Again</button>
 *   </div>
 * )}>
 *   <MyComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { onError, name } = this.props
    const prefix = name ? `[${name}]` : '[ErrorBoundary]'

    console.error(`${prefix} Caught error:`, error, errorInfo)

    if (onError) {
      onError(error, errorInfo)
    }
  }

  resetError = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    const { hasError, error } = this.state
    const { children, fallback } = this.props

    if (hasError && error) {
      // Render prop pattern - call fallback function with error and reset
      if (typeof fallback === 'function') {
        return fallback({ error, resetError: this.resetError })
      }

      // Static fallback - render as-is
      if (fallback) {
        return fallback
      }

      // Default fallback UI
      return <DefaultErrorFallback error={error} resetError={this.resetError} />
    }

    return children
  }
}

/**
 * Default fallback UI when no custom fallback is provided
 */
function DefaultErrorFallback({ error, resetError }: ErrorFallbackProps) {
  const isDev = import.meta.env.DEV

  return (
    <div className="flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Something went wrong
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            An error occurred while rendering this component. You can try again or refresh the page.
          </p>
          {isDev && error.message && (
            <div className="rounded-md bg-muted p-3">
              <p className="font-mono text-xs text-muted-foreground">{error.message}</p>
            </div>
          )}
          <div className="flex gap-2">
            <Button variant="teal" size="sm" onClick={resetError}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              Refresh Page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

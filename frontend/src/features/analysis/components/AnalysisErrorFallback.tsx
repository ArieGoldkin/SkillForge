import { useNavigate } from '@tanstack/react-router'
import { AlertTriangle, Home, RefreshCw } from 'lucide-react'

import type { ErrorFallbackProps } from '@shared/components'
import { Button } from '@shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@shared/components/ui/card'

interface AnalysisErrorFallbackProps extends ErrorFallbackProps {
  /** Section name for context (e.g., "Progress", "Activity") */
  section?: string
}

/**
 * Analysis-specific error fallback UI.
 *
 * Displays when a render error occurs in analysis components.
 * Provides retry and navigation options to recover gracefully.
 */
export function AnalysisErrorFallback({
  error,
  resetError,
  section = 'Analysis',
}: AnalysisErrorFallbackProps) {
  const navigate = useNavigate()
  const isDev = import.meta.env.DEV

  const handleGoToLibrary = () => {
    navigate({ to: '/library' })
  }

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-sm border-destructive/30">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base text-destructive">
            <AlertTriangle className="h-5 w-5" />
            {section} Error
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Something went wrong while loading this section. Your analysis progress is safe - you
            can try again or return to your library.
          </p>

          {isDev && error.message && (
            <div className="rounded-md bg-muted/50 p-3 border border-muted">
              <p className="font-mono text-xs text-muted-foreground break-words">{error.message}</p>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Button variant="teal" size="sm" onClick={resetError} className="w-full">
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
            <Button variant="outline" size="sm" onClick={handleGoToLibrary} className="w-full">
              <Home className="mr-2 h-4 w-4" />
              Return to Library
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

AnalysisErrorFallback.displayName = 'AnalysisErrorFallback'

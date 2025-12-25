/**
 * ErrorDetails - Display error information for failed analyses
 */

import { AlertCircle } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@shared/components/ui/alert'

export interface ErrorDetailsProps {
  errorCode?: string | null
  errorMessage?: string | null
  failedAtStage?: string | null
}

export function ErrorDetails({ errorCode, errorMessage, failedAtStage }: ErrorDetailsProps) {
  if (!errorMessage && !errorCode && !failedAtStage) {
    return null
  }

  return (
    <Alert variant="destructive" className="bg-destructive/10">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Error Details</AlertTitle>
      <AlertDescription className="mt-2 space-y-1">
        {errorCode && (
          <div className="flex gap-2">
            <span className="font-medium">Code:</span>
            <code className="rounded bg-destructive/20 px-1.5 py-0.5 text-xs font-mono">
              {errorCode}
            </code>
          </div>
        )}
        {failedAtStage && (
          <div className="flex gap-2">
            <span className="font-medium">Failed at:</span>
            <span className="text-sm">{failedAtStage}</span>
          </div>
        )}
        {errorMessage && (
          <div className="mt-2 text-sm">
            <span className="font-medium">Message:</span>
            <p className="mt-1 text-muted-foreground">{errorMessage}</p>
          </div>
        )}
      </AlertDescription>
    </Alert>
  )
}

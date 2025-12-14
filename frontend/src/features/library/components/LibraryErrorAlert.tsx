import { AlertCircle, RefreshCw } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@shared/components/ui/alert'
import { Button } from '@shared/components/ui/button'

interface LibraryErrorAlertProps {
  error: Error | null
  onRetry: () => void
  isRetrying: boolean
}

export function LibraryErrorAlert({ error, onRetry, isRetrying }: LibraryErrorAlertProps) {
  return (
    <Alert variant="destructive" className="mb-6">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Failed to load library</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>
          {error instanceof Error
            ? error.message
            : 'Unable to connect to the server. Please check your connection.'}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          disabled={isRetrying}
          className="ml-4"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRetrying ? 'animate-spin' : ''}`} />
          Retry
        </Button>
      </AlertDescription>
    </Alert>
  )
}

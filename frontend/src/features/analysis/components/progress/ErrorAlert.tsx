import type * as React from 'react'

import { XCircle } from 'lucide-react'

interface ErrorAlertProps {
  message: string
}

/**
 * Error alert for SSE connection failures
 */
export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message }) => (
  <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
    <div className="flex items-start gap-2">
      <XCircle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-destructive">Connection Error</p>
        <p className="text-xs text-destructive/80 mt-1">{message}</p>
      </div>
    </div>
  </div>
)

ErrorAlert.displayName = 'ErrorAlert'

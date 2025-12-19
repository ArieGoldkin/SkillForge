import type * as React from 'react'

import { AlertTriangle, X } from 'lucide-react'

import { Alert, AlertDescription } from '@shared/components/ui/alert'
import { Button } from '@shared/components/ui/button'

interface TimeoutWarningBannerProps {
  /** Whether to show the timeout warning */
  showTimeoutWarning: boolean
  /** Callback when user dismisses the warning */
  onDismiss: () => void
}

/**
 * Timeout warning banner for long-running connections
 *
 * Shows after 30 seconds of waiting for analysis to start.
 * Provides reassurance that analysis is still in progress and allows dismissal.
 *
 * Issue #399: Prevents user confusion during long analysis setup times
 */
export const TimeoutWarningBanner: React.FC<TimeoutWarningBannerProps> = ({
  showTimeoutWarning,
  onDismiss,
}) => {
  if (!showTimeoutWarning) {
    return null
  }

  return (
    <Alert className="border-orange-200 bg-orange-50 text-orange-800">
      <AlertTriangle className="h-4 w-4" />
      <AlertDescription className="flex items-center justify-between">
        <span>
          This analysis is taking longer than expected. Your content may be quite large or complex.
          Please continue waiting - results will appear soon.
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="ml-4 h-6 w-6 p-0 text-orange-600 hover:text-orange-800 hover:bg-orange-100"
          aria-label="Dismiss timeout warning"
        >
          <X className="h-3 w-3" />
        </Button>
      </AlertDescription>
    </Alert>
  )
}

TimeoutWarningBanner.displayName = 'TimeoutWarningBanner'

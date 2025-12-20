import type * as React from 'react'

import { CheckCircle2 } from 'lucide-react'

/**
 * Success message shown when analysis completes
 */
export const CompletionMessage: React.FC = () => (
  <div className="mt-4 p-3 bg-status-success/10 border border-status-success/20 rounded-md">
    <div className="flex items-center gap-2">
      <CheckCircle2 className="h-4 w-4 text-status-success" />
      <p className="text-sm font-medium text-status-success">Analysis Complete</p>
    </div>
  </div>
)

CompletionMessage.displayName = 'CompletionMessage'

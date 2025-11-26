import type * as React from 'react'

import { CheckCircle2 } from 'lucide-react'

/**
 * Success message shown when analysis completes
 */
export const CompletionMessage: React.FC = () => (
  <div className="mt-4 p-3 bg-[oklch(0.6959_0.1491_162.4796)]/10 border border-[oklch(0.6959_0.1491_162.4796)]/20 rounded-md">
    <div className="flex items-center gap-2">
      <CheckCircle2 className="h-4 w-4 text-[oklch(0.6959_0.1491_162.4796)]" />
      <p className="text-sm font-medium text-[oklch(0.6959_0.1491_162.4796)]">Analysis Complete</p>
    </div>
  </div>
)

CompletionMessage.displayName = 'CompletionMessage'

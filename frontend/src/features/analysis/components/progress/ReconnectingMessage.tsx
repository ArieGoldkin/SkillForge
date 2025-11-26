import type * as React from 'react'

import { Loader2 } from 'lucide-react'

/**
 * Message shown when reconnecting to SSE stream
 */
export const ReconnectingMessage: React.FC = () => (
  <div className="mb-4 p-2 bg-muted rounded-md">
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>Reconnecting to analysis stream...</span>
    </div>
  </div>
)

ReconnectingMessage.displayName = 'ReconnectingMessage'

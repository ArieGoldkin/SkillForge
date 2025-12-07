/**
 * Loading state for the preview modal
 */

import { Loader2 } from 'lucide-react'

export function ModalLoadingState() {
  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 p-8">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Loading preview...</p>
    </div>
  )
}

ModalLoadingState.displayName = 'ModalLoadingState'

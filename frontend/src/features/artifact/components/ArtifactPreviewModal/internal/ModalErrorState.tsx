/**
 * Error state for the preview modal
 */

import { AlertCircle } from 'lucide-react'

interface ModalErrorStateProps {
  message: string
}

export function ModalErrorState({ message }: ModalErrorStateProps) {
  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertCircle className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <p className="font-medium text-foreground">Failed to load preview</p>
        <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}

ModalErrorState.displayName = 'ModalErrorState'

import { FileText, Loader2 } from 'lucide-react'

import { BackLink } from './BackLink'

interface StateProps {
  analysisId?: string
}

export function ArtifactLoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <Loader2 className="h-10 w-10 animate-spin mb-4" />
      <p className="text-lg">Loading implementation guide...</p>
    </div>
  )
}

interface ErrorStateProps extends StateProps {
  message: string
}

export function ArtifactErrorState({ message, analysisId }: ErrorStateProps) {
  return (
    <div className="p-6 bg-destructive/10 border border-destructive/20 rounded-lg">
      <p className="text-destructive font-medium">{message}</p>
      <BackLink analysisId={analysisId} className="mt-4" />
    </div>
  )
}

export function ArtifactEmptyState({ analysisId }: StateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <FileText className="h-12 w-12 mb-4 opacity-50" />
      <p className="text-lg mb-2">No artifact available</p>
      <p className="text-sm mb-6">The analysis may still be in progress.</p>
      <BackLink analysisId={analysisId} className="" />
    </div>
  )
}

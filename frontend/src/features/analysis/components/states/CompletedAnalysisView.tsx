import { AnalysisHeader } from '../steps/AnalysisHeader'

import { AnalysisCompleteCard } from './AnalysisCompleteCard'
import { CompletedProgressColumn } from './CompletedProgressColumn'

interface CompletedAnalysisViewProps {
  analysisId?: string
  artifactId: string
}

export function CompletedAnalysisView({ analysisId, artifactId }: CompletedAnalysisViewProps) {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <AnalysisHeader
        title="Content Analysis"
        url={analysisId ? `Analysis ID: ${analysisId}` : ''}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <CompletedProgressColumn />
        <AnalysisCompleteCard artifactId={artifactId} analysisId={analysisId} variant="column" />
      </div>
    </div>
  )
}

import { Download } from 'lucide-react'

import { TeachMeButton } from '@features/analysis/components/states/internal'

import { Button } from '@shared/components/ui/button'

interface ArtifactHeaderProps {
  showDownload: boolean
  onDownload: () => void
  /** @deprecated analysisId is now retrieved from Zustand store (Issue #396) */
  analysisId?: string
}

export function ArtifactHeader({ showDownload, onDownload }: ArtifactHeaderProps) {
  return (
    <header className="mb-8 flex items-start justify-between">
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Implementation Guide</h1>
        <p className="text-muted-foreground">Generated artifact from content analysis</p>
      </div>

      <div className="flex items-center gap-2">
        {/* TeachMeButton now gets analysisId from Zustand store (Issue #396) */}
        <TeachMeButton isCompact variant="outline" />
        {showDownload && (
          <Button
            variant="outline"
            size="sm"
            onClick={onDownload}
            className="gap-2"
            data-testid="download-button"
          >
            <Download className="h-4 w-4" />
            Download
          </Button>
        )}
      </div>
    </header>
  )
}

import { GoldenDatasetBadge } from '@features/artifact/components/internal/GoldenDatasetBadge'
import { isGoldenDatasetUrl, extractDocumentName } from '@features/artifact/utils/urlHelpers'

interface AnalysisHeaderProps {
  title: string | null
  url: string
}

export function AnalysisHeader({ title, url }: AnalysisHeaderProps) {
  const isGoldenDataset = isGoldenDatasetUrl(url)
  const documentName = isGoldenDataset ? extractDocumentName(url) : undefined

  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold mb-2">{title || 'Analysis'}</h1>
      {isGoldenDataset ? (
        <div className="flex items-center gap-2">
          <GoldenDatasetBadge documentName={documentName} />
          <span className="text-sm text-muted-foreground">Example content</span>
        </div>
      ) : (
        <p className="text-muted-foreground">{url}</p>
      )}
    </div>
  )
}

/**
 * ArtifactPage - Dedicated page for viewing the generated implementation guide
 *
 * Route: /artifact/:artifactId?analysisId=xxx
 */

import { getRouteApi } from '@tanstack/react-router'

import { MarkdownPreview } from './components'
import {
  ArtifactEmptyState,
  ArtifactErrorState,
  ArtifactHeader,
  ArtifactLoadingState,
  BackLink,
} from './components/internal'
import { useArtifact } from './hooks'

export default function ArtifactPage() {
  const routeApi = getRouteApi('/artifact/$artifactId')

  const { artifactId } = routeApi.useParams()
  const { analysisId } = routeApi.useSearch()
  const { content, isLoading, error, download } = useArtifact(artifactId)

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <BackLink analysisId={analysisId} artifactId={artifactId} />
        <ArtifactHeader showDownload={!!content} onDownload={download} analysisId={analysisId} />

        {isLoading && <ArtifactLoadingState />}
        {error && !isLoading && (
          <ArtifactErrorState message={error.message} analysisId={analysisId} />
        )}
        {!artifactId && !isLoading && !error && <ArtifactEmptyState analysisId={analysisId} />}
        {content && <MarkdownPreview content={content} showMetadata={false} />}
      </div>
    </div>
  )
}

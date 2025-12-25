/**
 * ArtifactPage - Dedicated page for viewing the generated implementation guide
 *
 * Route: /artifact/:artifactId?analysisId=xxx
 */

import { getRouteApi, useLocation } from '@tanstack/react-router'

import {
  ArtifactSkeleton,
  FeedbackButtons,
  MarkdownPreview,
  QualityWarningBanner,
  TableOfContents,
} from './components'
import {
  ArtifactEmptyState,
  ArtifactErrorState,
  ArtifactHeader,
  BackLink,
} from './components/internal'
import { useArtifact } from './hooks'

interface ArtifactContentProps {
  content: string
  artifactId: string
  traceId: string | null
  qualityWarnings: string[]
  qualityPassed: boolean | null
  qualityScore: number | null
}

function ArtifactContent({
  content,
  artifactId,
  traceId,
  qualityWarnings,
  qualityPassed,
  qualityScore,
}: ArtifactContentProps) {
  const showQualityBanner = qualityWarnings.length > 0 || qualityPassed === false

  return (
    <div className="lg:grid lg:grid-cols-[250px_1fr] lg:gap-8 xl:grid-cols-[280px_1fr] xl:gap-12">
      <aside className="lg:sticky lg:top-8 lg:self-start lg:max-h-[calc(100vh-4rem)] lg:overflow-y-auto">
        <TableOfContents content={content} className="mb-6 lg:mb-0" />
      </aside>

      <main className="min-w-0">
        {showQualityBanner && (
          <div className="mb-6">
            <QualityWarningBanner
              warnings={qualityWarnings}
              avgScore={qualityScore ?? undefined}
              passed={qualityPassed ?? undefined}
            />
          </div>
        )}

        <MarkdownPreview content={content} showMetadata={false} />

        <div className="mt-8 pt-6 border-t border-border">
          <FeedbackButtons artifactId={artifactId} traceId={traceId} />
        </div>
      </main>
    </div>
  )
}

export default function ArtifactPage() {
  const routeApi = getRouteApi('/artifact/$artifactId')
  const { artifactId } = routeApi.useParams()
  const { analysisId } = routeApi.useSearch()
  const location = useLocation()
  const locationStateTraceId = (location.state as { traceId?: string } | undefined)?.traceId

  const {
    content,
    traceId: apiTraceId,
    qualityWarnings,
    qualityPassed,
    qualityScore,
    isLoading,
    error,
    download,
  } = useArtifact(artifactId)

  const traceId = apiTraceId ?? locationStateTraceId ?? null

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto lg:max-w-none">
          <BackLink analysisId={analysisId} artifactId={artifactId} />
          <ArtifactHeader showDownload={!!content} onDownload={download} analysisId={analysisId} />

          {isLoading && <ArtifactSkeleton />}
          {error && !isLoading && (
            <ArtifactErrorState message={error.message} analysisId={analysisId} />
          )}
          {!artifactId && !isLoading && !error && <ArtifactEmptyState analysisId={analysisId} />}

          {content && artifactId && (
            <ArtifactContent
              content={content}
              artifactId={artifactId}
              traceId={traceId}
              qualityWarnings={qualityWarnings}
              qualityPassed={qualityPassed}
              qualityScore={qualityScore}
            />
          )}
        </div>
      </div>
    </div>
  )
}

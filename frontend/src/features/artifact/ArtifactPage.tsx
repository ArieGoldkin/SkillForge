/**
 * ArtifactPage - Dedicated page for viewing the generated implementation guide
 *
 * Route: /artifact/:artifactId?analysisId=xxx
 */

import { getRouteApi } from '@tanstack/react-router'

import { FeedbackButtons, MarkdownPreview, TableOfContents } from './components'
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
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto lg:max-w-none">
          <BackLink analysisId={analysisId} artifactId={artifactId} />
          <ArtifactHeader showDownload={!!content} onDownload={download} analysisId={analysisId} />

          {isLoading && <ArtifactLoadingState />}
          {error && !isLoading && (
            <ArtifactErrorState message={error.message} analysisId={analysisId} />
          )}
          {!artifactId && !isLoading && !error && <ArtifactEmptyState analysisId={analysisId} />}

          {content && (
            <div className="lg:grid lg:grid-cols-[250px_1fr] lg:gap-8 xl:grid-cols-[280px_1fr] xl:gap-12">
              {/* Sticky TOC Sidebar - Desktop only, mobile shows collapsible version at top */}
              <aside className="lg:sticky lg:top-8 lg:self-start lg:max-h-[calc(100vh-4rem)] lg:overflow-y-auto">
                <TableOfContents content={content} className="mb-6 lg:mb-0" />
              </aside>

              {/* Main Content */}
              <main className="min-w-0">
                <MarkdownPreview content={content} showMetadata={false} />
                {/* Feedback section at the bottom of the artifact */}
                {artifactId && (
                  <div className="mt-8 pt-6 border-t border-border">
                    <FeedbackButtons artifactId={artifactId} traceId={null} />
                  </div>
                )}
              </main>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

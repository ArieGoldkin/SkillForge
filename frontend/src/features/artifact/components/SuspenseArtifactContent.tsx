/**
 * SuspenseArtifactContent - React 19 Suspense-native artifact rendering
 *
 * This component demonstrates React 19's `use()` hook for promise unwrapping.
 * Instead of manual loading states with useQuery, we leverage Suspense boundaries
 * to handle loading declaratively.
 *
 * ## React 19 Pattern
 *
 * The `use()` hook is a new primitive that can:
 * 1. Unwrap promises (suspends until resolved)
 * 2. Read from context conditionally (unlike useContext)
 *
 * This component focuses on promise unwrapping for data fetching.
 *
 * ## Usage Example
 *
 * ```tsx
 * import { Suspense } from 'react'
 * import { cachePromise } from '@lib/promiseCache'
 * import { fetchArtifact } from './api'
 *
 * function ArtifactPage({ artifactId }: { artifactId: string }) {
 *   // Create a stable promise (cached to prevent re-fetching on re-render)
 *   const artifactPromise = cachePromise(
 *     `artifact-${artifactId}`,
 *     () => fetchArtifact(artifactId)
 *   )
 *
 *   return (
 *     <Suspense fallback={<ArtifactSkeleton />}>
 *       <SuspenseArtifactContent artifactPromise={artifactPromise} />
 *     </Suspense>
 *   )
 * }
 * ```
 *
 * ## Benefits over useQuery
 *
 * - No manual loading/error state management
 * - Declarative loading UI via Suspense boundaries
 * - Better code splitting (Suspense + lazy())
 * - Composable error boundaries
 * - Works with Server Components (future Next.js migration)
 *
 * ## Limitations
 *
 * - Requires promise caching to prevent re-fetches
 * - Error handling requires Error Boundaries
 * - No built-in refetch/mutation logic (use TanStack Query for that)
 *
 * @see https://react.dev/reference/react/use
 * @see https://react.dev/reference/react/Suspense
 */

import { use } from 'react'

import type { ArtifactMetadataResponse } from '@app-types/api'

import { FeedbackButtons, MarkdownPreview, QualityWarningBanner, TableOfContents } from '.'

/**
 * Artifact data shape returned from API
 * Extracted from ArtifactMetadataResponse for clarity
 */
export interface ArtifactData {
  artifactId: string
  content: string
  traceId: string | null
  qualityWarnings: string[]
  qualityPassed: boolean | null
  qualityScore: number | null
}

/**
 * Props for SuspenseArtifactContent
 *
 * IMPORTANT: The promise must be stable across renders.
 * Use `cachePromise()` from @lib/promiseCache to ensure stability.
 */
export interface SuspenseArtifactContentProps {
  /**
   * Stable promise that resolves to artifact metadata
   * Use `cachePromise()` to prevent re-fetching on re-render
   */
  artifactPromise: Promise<ArtifactMetadataResponse>

  /**
   * Optional trace ID from navigation state
   * Falls back to API response trace_id if not provided
   */
  fallbackTraceId?: string | null
}

/**
 * Transform API response to component-friendly data structure
 */
function transformArtifactData(
  response: ArtifactMetadataResponse,
  fallbackTraceId?: string | null
): ArtifactData {
  const qualityMetadata = response.artifact_metadata
  const content = response.markdown_content ?? ''
  const traceId = response.trace_id ?? fallbackTraceId ?? null

  return {
    artifactId: response.artifact_id,
    content,
    traceId,
    qualityWarnings: qualityMetadata?.quality_warnings ?? [],
    qualityPassed: qualityMetadata?.quality_passed ?? null,
    qualityScore: qualityMetadata?.quality_gate_avg_score ?? null,
  }
}

/**
 * React 19 Suspense-native artifact content renderer
 *
 * This component uses the `use()` hook to unwrap the artifact promise.
 * It will suspend rendering until the promise resolves, triggering the
 * nearest Suspense boundary's fallback.
 *
 * CRITICAL: The artifactPromise must be stable across renders.
 * Creating a new promise on each render will cause infinite suspense loops.
 * Always use `cachePromise()` from @lib/promiseCache.
 *
 * @example
 * ```tsx
 * const promise = cachePromise('artifact-123', () => fetchArtifact('123'))
 *
 * <Suspense fallback={<ArtifactSkeleton />}>
 *   <SuspenseArtifactContent artifactPromise={promise} />
 * </Suspense>
 * ```
 */
export function SuspenseArtifactContent({
  artifactPromise,
  fallbackTraceId,
}: SuspenseArtifactContentProps) {
  /**
   * React 19's use() hook unwraps the promise
   *
   * - Suspends if promise is pending (shows Suspense fallback)
   * - Returns data if promise is fulfilled
   * - Throws error if promise is rejected (caught by Error Boundary)
   *
   * IMPORTANT: This hook can be called conditionally (unlike useEffect/useState)
   * but the promise must be stable to prevent infinite suspense.
   */
  const response = use(artifactPromise)

  // Transform API response to component data
  const { artifactId, content, traceId, qualityWarnings, qualityPassed, qualityScore } =
    transformArtifactData(response, fallbackTraceId)

  // Determine if quality banner should be shown
  const showQualityBanner = qualityWarnings.length > 0 || qualityPassed === false

  // No loading state needed - Suspense handles it!
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

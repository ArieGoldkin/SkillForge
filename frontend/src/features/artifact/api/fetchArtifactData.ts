/**
 * Artifact Data Fetcher - Standalone function for use with React 19's use() hook
 *
 * This file exports a pure async function (not a hook) that fetches artifact data.
 * Use with `cachePromise()` to create stable promises for the use() hook.
 *
 * @example
 * ```tsx
 * import { cachePromise } from '@lib/promiseCache'
 * import { fetchArtifactData } from './api/fetchArtifactData'
 *
 * const promise = cachePromise(
 *   `artifact-${id}`,
 *   () => fetchArtifactData(id)
 * )
 *
 * // In component with use():
 * const data = use(promise)
 * ```
 */

import type { ArtifactMetadataResponse } from '@app-types/api'

import { analyzeAPI } from '@services/api.service'

/**
 * Fetch artifact metadata from API
 *
 * @param artifactId - Artifact ID to fetch
 * @returns Promise that resolves to artifact metadata
 * @throws Error if artifact not found or API request fails
 */
export async function fetchArtifactData(artifactId: string): Promise<ArtifactMetadataResponse> {
  const metadata = await analyzeAPI.getArtifactById(artifactId)

  if (!metadata) {
    throw new Error('Failed to load artifact metadata')
  }

  return metadata
}

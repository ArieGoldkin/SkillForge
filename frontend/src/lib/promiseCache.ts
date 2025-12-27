/**
 * Promise Cache Utility for React 19's use() Hook
 *
 * React 19's `use()` hook suspends rendering until a promise resolves.
 * To prevent duplicate fetches when a component re-renders or re-mounts,
 * we cache promises by key.
 *
 * IMPORTANT: React 19's use() works with the SAME promise instance.
 * If you create a new promise on each render, the component will
 * re-suspend and re-fetch. This cache ensures promise stability.
 *
 * @example
 * ```tsx
 * // In parent component:
 * const artifactPromise = cachePromise(
 *   `artifact-${id}`,
 *   () => fetchArtifact(id)
 * )
 *
 * // Pass to Suspense boundary:
 * <Suspense fallback={<Loading />}>
 *   <ArtifactContent artifactPromise={artifactPromise} />
 * </Suspense>
 *
 * // In ArtifactContent:
 * const artifact = use(artifactPromise) // Suspends until resolved
 * ```
 *
 * @see https://react.dev/reference/react/use
 */

/**
 * Global promise cache
 * Maps cache keys to active promises
 */
const cache = new Map<string, Promise<unknown>>()

/**
 * Cache a promise to prevent duplicate fetches with React 19's use() hook
 *
 * If a promise with the given key already exists, returns the cached promise.
 * Otherwise, executes the fetcher function and caches the result.
 *
 * @param key - Unique cache key (e.g., "artifact-123")
 * @param fetcher - Async function that returns the data
 * @returns Cached or new promise
 *
 * @example
 * ```tsx
 * const dataPromise = cachePromise('user-123', () => fetchUser(123))
 * const user = use(dataPromise) // React 19's use() hook
 * ```
 */
export function cachePromise<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  if (!cache.has(key)) {
    const promise = fetcher()
      .then((data) => {
        // Promise resolved successfully, keep in cache
        return data
      })
      .catch((error) => {
        // Promise rejected, remove from cache to allow retry
        cache.delete(key)
        throw error
      })

    cache.set(key, promise)
  }

  return cache.get(key) as Promise<T>
}

/**
 * Invalidate a cached promise to force a fresh fetch
 *
 * Useful after mutations or when you know the data has changed.
 *
 * @param key - Cache key to invalidate
 *
 * @example
 * ```tsx
 * // After updating an artifact:
 * await updateArtifact(id, newContent)
 * invalidateCache(`artifact-${id}`)
 *
 * // Next render will fetch fresh data:
 * const promise = cachePromise(`artifact-${id}`, () => fetchArtifact(id))
 * ```
 */
export function invalidateCache(key: string): void {
  cache.delete(key)
}

/**
 * Clear all cached promises
 *
 * Useful for logout, environment switches, or testing.
 *
 * @example
 * ```tsx
 * function logout() {
 *   clearCache()
 *   navigate('/login')
 * }
 * ```
 */
export function clearCache(): void {
  cache.clear()
}

/**
 * Get cache statistics for debugging
 *
 * @returns Object with cache size and active keys
 *
 * @example
 * ```tsx
 * console.log(getCacheStats())
 * // { size: 3, keys: ['artifact-123', 'user-456', 'analysis-789'] }
 * ```
 */
export function getCacheStats(): { size: number; keys: string[] } {
  return {
    size: cache.size,
    keys: Array.from(cache.keys()),
  }
}

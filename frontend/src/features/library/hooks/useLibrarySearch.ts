import type { LibraryListResponse, LibrarySearchParams } from '@app-types/api'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'

import { analyzeAPI } from '@services/api.service'

/**
 * Hook for searching library with full-text, semantic, or hybrid search
 *
 * @param params - Search parameters (query, content_type, status, search_mode, limit, offset)
 * @returns React Query result with library search results
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useLibrarySearch({
 *   query: 'React hooks',
 *   search_mode: 'hybrid',
 *   limit: 20
 * })
 * ```
 */
export function useLibrarySearch(params: LibrarySearchParams) {
  return useQuery<LibraryListResponse>({
    queryKey: ['library', params],
    queryFn: () => analyzeAPI.searchLibrary(params),
    staleTime: 30 * 1000, // 30 seconds
    placeholderData: (previousData) => previousData, // Keep previous data while loading
    retry: false, // Don't retry on failure - let user manually retry
  })
}

/**
 * Infinite version of library search using offset pagination.
 *
 * Pages are accumulated; getNextPageParam is derived from offset+limit < total.
 */
export function useLibrarySearchInfinite(params: LibrarySearchParams) {
  return useInfiniteQuery({
    queryKey: ['library', 'infinite', params],
    queryFn: ({ pageParam }) => {
      const nextOffset = typeof pageParam === 'number' ? pageParam : (params.offset ?? 0)
      return analyzeAPI.searchLibrary({ ...params, offset: nextOffset })
    },
    initialPageParam: params.offset ?? 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, page) => sum + page.items.length, 0)
      const pageSize = params.limit ?? lastPage.limit ?? 0

      // If the last page returned fewer than a full page, we reached the end
      if (pageSize === 0 || lastPage.items.length < pageSize) {
        return undefined
      }

      // Otherwise assume there may be more and request the next offset
      const nextOffset = loaded

      return nextOffset
    },
    staleTime: 30 * 1000,
    refetchOnWindowFocus: false,
    retry: false, // Don't retry on failure - show error immediately with retry button
  })
}

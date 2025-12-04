import type { LibraryListResponse, LibrarySearchParams } from '@app-types/api'
import { useQuery } from '@tanstack/react-query'

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
  })
}

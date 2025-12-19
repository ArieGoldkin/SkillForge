/**
 * TanStack Query Mock Factories
 *
 * Provides type-safe factory functions for creating mock query results
 * in tests, eliminating the need for `{} as any` anti-patterns.
 *
 * @module test-utils/factories/queryResultFactory
 */

import type { UseInfiniteQueryResult, InfiniteData } from '@tanstack/react-query'
import { vi } from 'vitest'

/**
 * Create a type-safe mock for TanStack Query infinite query result
 *
 * Provides sensible defaults for all required properties while allowing
 * partial overrides for specific test scenarios.
 *
 * @example
 * ```typescript
 * const mockQuery = createMockInfiniteQueryResult<ApiResponse>({
 *   data: { pages: [mockData], pageParams: [undefined] },
 *   isSuccess: true,
 *   isLoading: false
 * })
 * ```
 *
 * @param overrides - Partial query result properties to override defaults
 * @returns Fully typed UseInfiniteQueryResult mock
 */
// eslint-disable-next-line complexity -- Factory needs all properties for type safety
export function createMockInfiniteQueryResult<TData = unknown, TError = Error>(
  overrides: Partial<UseInfiniteQueryResult<InfiniteData<TData>, TError>> = {}
): UseInfiniteQueryResult<InfiniteData<TData>, TError> {
  // Default InfiniteData structure
  const defaultData: InfiniteData<TData> = {
    pages: [],
    pageParams: [],
  }

  // Build the mock result with all required properties
  const mockResult = {
    // Data properties
    data: overrides.data ?? defaultData,
    dataUpdatedAt: overrides.dataUpdatedAt ?? 0,
    error: overrides.error ?? null,
    errorUpdateCount: overrides.errorUpdateCount ?? 0,
    errorUpdatedAt: overrides.errorUpdatedAt ?? 0,
    failureCount: overrides.failureCount ?? 0,
    failureReason: overrides.failureReason ?? null,

    // Status booleans
    isError: overrides.isError ?? false,
    isFetched: overrides.isFetched ?? true,
    isFetchedAfterMount: overrides.isFetchedAfterMount ?? true,
    isFetching: overrides.isFetching ?? false,
    isInitialLoading: overrides.isInitialLoading ?? false,
    isLoading: overrides.isLoading ?? false,
    isLoadingError: overrides.isLoadingError ?? false,
    isPaused: overrides.isPaused ?? false,
    isPending: overrides.isPending ?? false,
    isPlaceholderData: overrides.isPlaceholderData ?? false,
    isRefetchError: overrides.isRefetchError ?? false,
    isRefetching: overrides.isRefetching ?? false,
    isStale: overrides.isStale ?? false,
    isSuccess: overrides.isSuccess ?? true,

    // Status enum
    status: overrides.status ?? 'success',
    fetchStatus: overrides.fetchStatus ?? 'idle',

    // Infinite query specific
    hasNextPage: overrides.hasNextPage ?? false,
    hasPreviousPage: overrides.hasPreviousPage ?? false,
    isFetchingNextPage: overrides.isFetchingNextPage ?? false,
    isFetchingPreviousPage: overrides.isFetchingPreviousPage ?? false,

    // Functions
    refetch: overrides.refetch ?? vi.fn(),
    fetchNextPage: overrides.fetchNextPage ?? vi.fn(),
    fetchPreviousPage: overrides.fetchPreviousPage ?? vi.fn(),
  }

  return mockResult as UseInfiniteQueryResult<InfiniteData<TData>, TError>
}

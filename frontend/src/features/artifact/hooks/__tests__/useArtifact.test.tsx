/**
 * Tests for useArtifact hook - Artifact fetching and download
 */

import type { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { downloadMarkdown } from '../downloadMarkdown'
import { useArtifact } from '../useArtifact'

// Mock the API service
vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    downloadArtifact: vi.fn(),
  },
}))

// Mock downloadMarkdown
vi.mock('../downloadMarkdown', () => ({
  downloadMarkdown: vi.fn(),
}))

// Create wrapper with fresh QueryClient for each test
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useArtifact', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns error when artifactId is undefined', () => {
    const { result } = renderHook(() => useArtifact(undefined), {
      wrapper: createWrapper(),
    })

    expect(result.current.error).toEqual(new Error('No artifact ID provided'))
    expect(result.current.content).toBe(null)
    expect(result.current.isLoading).toBe(false)
  })

  it('fetches artifact content successfully', async () => {
    const mockContent = '# Test Guide\n\nContent here.'
    vi.mocked(analyzeAPI.downloadArtifact).mockResolvedValueOnce(mockContent)

    const { result } = renderHook(() => useArtifact('artifact-123'), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.content).toBe(mockContent)
    expect(result.current.error).toBe(null)
  })

  it('returns error when fetch fails', async () => {
    vi.mocked(analyzeAPI.downloadArtifact).mockResolvedValueOnce(null)

    const { result } = renderHook(() => useArtifact('artifact-123'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.error?.message).toBe('Failed to load artifact content')
    expect(result.current.content).toBe(null)
  })

  it('download callback calls downloadMarkdown with correct parameters', async () => {
    const mockContent = '# Guide Content'
    vi.mocked(analyzeAPI.downloadArtifact).mockResolvedValueOnce(mockContent)

    const { result } = renderHook(() => useArtifact('artifact-456'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.content).toBe(mockContent)
    })

    result.current.download()

    expect(downloadMarkdown).toHaveBeenCalledWith(
      mockContent,
      'implementation-guide-artifact-456.md'
    )
  })

  it('download callback does nothing when data is missing', () => {
    const { result } = renderHook(() => useArtifact(undefined), {
      wrapper: createWrapper(),
    })

    result.current.download()

    expect(downloadMarkdown).not.toHaveBeenCalled()
  })
})

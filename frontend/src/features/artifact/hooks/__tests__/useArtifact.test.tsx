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

// Valid UUIDs for testing
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'
const TEST_ARTIFACT_ID_2 = 'a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6'

// Mock the API service - must match what useArtifact.ts actually calls
vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    getArtifactById: vi.fn(),
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
    vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce({
      analysis_id: 'test-analysis-id',
      artifact_id: TEST_ARTIFACT_ID,
      markdown_content: mockContent,
      trace_id: 'test-trace-id',
    })

    const { result } = renderHook(() => useArtifact(TEST_ARTIFACT_ID), {
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
    vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce(null)

    const { result } = renderHook(() => useArtifact(TEST_ARTIFACT_ID), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.error?.message).toBe('Failed to load artifact metadata')
    expect(result.current.content).toBe(null)
  })

  it('download callback calls downloadMarkdown with correct parameters', async () => {
    const mockContent = '# Guide Content'
    vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce({
      analysis_id: 'test-analysis-id',
      artifact_id: TEST_ARTIFACT_ID_2,
      markdown_content: mockContent,
      trace_id: 'test-trace-id',
    })

    const { result } = renderHook(() => useArtifact(TEST_ARTIFACT_ID_2), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.content).toBe(mockContent)
    })

    result.current.download()

    expect(downloadMarkdown).toHaveBeenCalledWith(
      mockContent,
      `implementation-guide-${TEST_ARTIFACT_ID_2}.md`
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

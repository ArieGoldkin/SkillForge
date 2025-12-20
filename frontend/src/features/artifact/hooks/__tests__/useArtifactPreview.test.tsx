/**
 * Tests for useArtifactPreview hook - Modal state management with artifact fetching
 */

import type { ReactNode } from 'react'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { useArtifactPreview } from '../useArtifactPreview'

// Valid UUID for testing
const TEST_ARTIFACT_ID = '987fcdeb-51a2-43d7-8f9e-123456789abc'

// Mock the API service - must match what useArtifact.ts actually calls
vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    getArtifactById: vi.fn(),
  },
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

describe('useArtifactPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Modal State', () => {
    it('starts with modal closed', () => {
      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      expect(result.current.isOpen).toBe(false)
    })

    it('opens modal when openPreview is called with valid artifactId', () => {
      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      expect(result.current.isOpen).toBe(true)
    })

    it('does not open modal when artifactId is null', () => {
      const { result } = renderHook(() => useArtifactPreview(null), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      expect(result.current.isOpen).toBe(false)
    })

    it('does not open modal when artifactId is undefined', () => {
      const { result } = renderHook(() => useArtifactPreview(undefined), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      expect(result.current.isOpen).toBe(false)
    })

    it('closes modal when closePreview is called', () => {
      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })
      expect(result.current.isOpen).toBe(true)

      act(() => {
        result.current.closePreview()
      })
      expect(result.current.isOpen).toBe(false)
    })
  })

  describe('Lazy Loading', () => {
    it('does not fetch artifact when modal is closed', () => {
      renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      expect(analyzeAPI.getArtifactById).not.toHaveBeenCalled()
    })

    it('fetches artifact when modal is opened', async () => {
      const mockContent = '# Test Guide'
      vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce({
        analysis_id: 'test-analysis-id',
        artifact_id: TEST_ARTIFACT_ID,
        markdown_content: mockContent,
        trace_id: 'test-trace-id',
      })

      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      await waitFor(() => {
        expect(analyzeAPI.getArtifactById).toHaveBeenCalledWith(TEST_ARTIFACT_ID)
      })

      await waitFor(() => {
        expect(result.current.content).toBe(mockContent)
      })
    })
  })

  describe('Loading and Error States', () => {
    it('shows loading state while fetching', async () => {
      vi.mocked(analyzeAPI.getArtifactById).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  analysis_id: 'test-analysis-id',
                  artifact_id: TEST_ARTIFACT_ID,
                  markdown_content: 'content',
                  trace_id: 'test-trace-id',
                }),
              100
            )
          )
      )

      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      expect(result.current.isLoading).toBe(true)
    })

    it('returns error when fetch fails', async () => {
      vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce(null)

      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.error).not.toBeNull()
    })
  })

  describe('Download Function', () => {
    it('exposes download function from useArtifact', async () => {
      const mockContent = '# Guide Content'
      vi.mocked(analyzeAPI.getArtifactById).mockResolvedValueOnce({
        analysis_id: 'test-analysis-id',
        artifact_id: TEST_ARTIFACT_ID,
        markdown_content: mockContent,
        trace_id: 'test-trace-id',
      })

      const { result } = renderHook(() => useArtifactPreview(TEST_ARTIFACT_ID), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.openPreview()
      })

      await waitFor(() => {
        expect(result.current.content).toBe(mockContent)
      })

      expect(typeof result.current.download).toBe('function')
    })
  })
})

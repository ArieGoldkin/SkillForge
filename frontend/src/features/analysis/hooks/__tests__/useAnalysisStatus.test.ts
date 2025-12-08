import { act, renderHook, waitFor } from '@testing-library/react'
import type { Mock } from 'vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeAPI } from '@services/api.service'

import { useAnalysisStatus } from '../useAnalysisStatus'

vi.mock('@services/api.service', () => ({
  analyzeAPI: {
    getAnalysisStatus: vi.fn(),
  },
}))

const mockStatus = analyzeAPI.getAnalysisStatus as unknown as Mock

const baseStatus = {
  analysis_id: 'analysis-1',
  url: 'https://example.com',
  content_type: 'article',
  title: 'Example',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
}

describe('useAnalysisStatus', () => {
  beforeEach(() => {
    vi.useRealTimers()
    mockStatus.mockReset()
  })

  it('resolves complete status on late join and disables SSE', async () => {
    mockStatus.mockResolvedValueOnce({
      ...baseStatus,
      status: 'complete',
      artifact_id: 'artifact-1',
    })

    const { result } = renderHook(() =>
      useAnalysisStatus({
        analysisId: 'analysis-1',
        completedParam: false,
        sseState: { eventsLength: 0, isComplete: false },
      })
    )

    await waitFor(() => expect(result.current.resolvedStatus).toBe('complete'))
    expect(result.current.resolvedArtifactId).toBe('artifact-1')
    expect(result.current.shouldConnect).toBe(false)
  })

  it('rechecks after idle period and resolves complete', async () => {
    mockStatus
      .mockResolvedValueOnce({
        ...baseStatus,
        status: 'pending',
        artifact_id: null,
      })
      .mockResolvedValueOnce({
        ...baseStatus,
        status: 'complete',
        artifact_id: 'artifact-2',
      })

    const { result } = renderHook(() =>
      useAnalysisStatus({
        analysisId: 'analysis-1',
        completedParam: false,
        sseState: { eventsLength: 0, isComplete: false },
      })
    )

    await waitFor(() => expect(mockStatus).toHaveBeenCalledTimes(1))

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => expect(mockStatus).toHaveBeenCalledTimes(2), { timeout: 5000 })
    await waitFor(() => expect(result.current.resolvedStatus).toBe('complete'), {
      timeout: 5000,
    })
    expect(result.current.resolvedArtifactId).toBe('artifact-2')
  }, 20000)
})

import * as router from '@tanstack/react-router'
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { analyzeAPI } from '@/services/api.service'

import { useLibrarySkills } from '../useLibrarySkills'

vi.mock('@/services/api.service', () => ({
  analyzeAPI: {
    retryAnalysis: vi.fn(),
  },
}))

vi.mock('@tanstack/react-router', () => ({
  useNavigate: vi.fn(),
}))

describe('useLibrarySkills - Retry Functionality', () => {
  const mockNavigate = vi.fn()
  const mockSearchResults = {
    pages: [
      {
        items: [
          {
            analysis_id: 'test-id-1',
            title: 'Failed Analysis',
            status: 'failed',
            content_type: 'article',
            error_code: 'EXTRACTION_FAILED',
            error_message: 'Failed to extract',
            failed_at_stage: 'extraction',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    ],
    pageParams: [0],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(router.useNavigate).mockReturnValue(mockNavigate)
    vi.mocked(analyzeAPI.retryAnalysis).mockResolvedValue({
      analysis_id: 'test-id-1',
      status: 'pending',
      retry_count: 1,
      sse_endpoint: '/api/v1/analyze/test-id-1/stream',
    })
  })

  it('provides retry handler in skill data', () => {
    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    expect(result.current.skills).toHaveLength(1)
    expect(result.current.skills[0].onRetry).toBeDefined()
    expect(typeof result.current.skills[0].onRetry).toBe('function')
  })

  it('passes error fields to skill data', () => {
    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    const skill = result.current.skills[0]
    expect(skill.errorCode).toBe('EXTRACTION_FAILED')
    expect(skill.errorMessage).toBe('Failed to extract')
    expect(skill.failedAtStage).toBe('extraction')
  })

  it('calls retry API when retry handler is invoked', async () => {
    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    const skill = result.current.skills[0]
    await skill.onRetry!('test-id-1', 'extraction')

    expect(analyzeAPI.retryAnalysis).toHaveBeenCalledWith('test-id-1')
  })

  it('navigates to analysis page after successful retry', async () => {
    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    const skill = result.current.skills[0]
    await skill.onRetry!('test-id-1')

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith({
        to: '/analyze/$id',
        params: { id: 'test-id-1' },
      })
    })
  })

  it('handles retry errors gracefully', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(analyzeAPI.retryAnalysis).mockRejectedValue(new Error('Retry failed'))

    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    const skill = result.current.skills[0]
    await skill.onRetry!('test-id-1')

    // Should not throw, should log error
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalled()
    })

    consoleErrorSpy.mockRestore()
  })

  it('prevents multiple simultaneous retries', async () => {
    const { result } = renderHook(() => useLibrarySkills({ searchResults: mockSearchResults }))

    const skill = result.current.skills[0]
    const retryPromise1 = skill.onRetry!('test-id-1')
    const retryPromise2 = skill.onRetry!('test-id-1')

    await Promise.all([retryPromise1, retryPromise2])

    // Should only call API once
    expect(analyzeAPI.retryAnalysis).toHaveBeenCalledTimes(1)
  })
})

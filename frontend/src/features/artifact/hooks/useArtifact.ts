/**
 * useArtifact - Hook for fetching and managing artifact content
 */

import { useCallback } from 'react'

import { useQuery } from '@tanstack/react-query'

import { analyzeAPI } from '@services/api.service'

import { downloadMarkdown } from './downloadMarkdown'

export interface UseArtifactState {
  content: string | null
  isLoading: boolean
  error: Error | null
}

export interface UseArtifactReturn extends UseArtifactState {
  download: () => void
}

async function fetchArtifact(artifactId: string): Promise<string> {
  const content = await analyzeAPI.downloadArtifact(artifactId)
  if (!content) {
    throw new Error('Failed to load artifact content')
  }
  return content
}

export function useArtifact(artifactId: string | undefined): UseArtifactReturn {
  const { data, isLoading, error } = useQuery({
    queryKey: ['artifact', artifactId],
    queryFn: () => fetchArtifact(artifactId!),
    enabled: !!artifactId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    retry: false, // Don't retry on failure - user can refresh manually
  })

  const download = useCallback(() => {
    if (data && artifactId) {
      downloadMarkdown(data, `implementation-guide-${artifactId}.md`)
    }
  }, [data, artifactId])

  return {
    content: data ?? null,
    isLoading,
    error: artifactId ? (error as Error | null) : new Error('No artifact ID provided'),
    download,
  }
}

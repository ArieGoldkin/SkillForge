/**
 * useArtifactPreview - Hook for managing artifact preview modal state
 *
 * Combines modal state management with artifact fetching
 */

import { useCallback, useState } from 'react'

import { useArtifact } from './useArtifact'

export interface UseArtifactPreviewReturn {
  /** Whether the preview modal is open */
  isOpen: boolean
  /** Open the preview modal */
  openPreview: () => void
  /** Close the preview modal */
  closePreview: () => void
  /** Artifact content */
  content: string | null
  /** Loading state */
  isLoading: boolean
  /** Error state */
  error: Error | null
  /** Download the artifact */
  download: () => void
}

export function useArtifactPreview(
  artifactId: string | null | undefined
): UseArtifactPreviewReturn {
  const [isOpen, setIsOpen] = useState(false)

  const { content, isLoading, error, download } = useArtifact(
    isOpen ? (artifactId ?? undefined) : undefined
  )

  const openPreview = useCallback(() => {
    if (artifactId) {
      setIsOpen(true)
    }
  }, [artifactId])

  const closePreview = useCallback(() => {
    setIsOpen(false)
  }, [])

  return {
    isOpen,
    openPreview,
    closePreview,
    content,
    isLoading,
    error,
    download,
  }
}

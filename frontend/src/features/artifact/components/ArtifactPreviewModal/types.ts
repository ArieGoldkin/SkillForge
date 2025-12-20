/**
 * Types for ArtifactPreviewModal component
 */

export interface ArtifactPreviewModalProps {
  /** Whether the modal is open */
  isOpen: boolean
  /** Callback to close the modal */
  onClose: () => void
  /** Markdown content to preview */
  content: string | null
  /** Loading state */
  isLoading: boolean
  /** Error state */
  error: Error | null
  /** Callback to trigger download */
  onDownload?: () => void
  /** Optional source URL to display in header */
  sourceUrl?: string
  /** Artifact ID for feedback buttons */
  artifactId?: string | null
}

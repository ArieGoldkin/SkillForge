/**
 * Artifact Feature
 *
 * Handles viewing and managing generated implementation guides.
 * Includes markdown rendering with syntax highlighting and download functionality.
 */

// Main page component
export { default as ArtifactPage } from './ArtifactPage'

// Hooks
export {
  useArtifact,
  useArtifactPreview,
  type UseArtifactReturn,
  type UseArtifactState,
  type UseArtifactPreviewReturn,
} from './hooks'

// Components
export {
  MarkdownPreview,
  ArtifactPreviewModal,
  type MarkdownPreviewProps,
  type ArtifactPreviewModalProps,
} from './components'

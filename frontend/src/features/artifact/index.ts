/**
 * Artifact Feature
 *
 * Handles viewing and managing generated implementation guides.
 * Includes markdown rendering with syntax highlighting and download functionality.
 */

// Main page component
export { default as ArtifactPage } from './ArtifactPage'

// Hooks
export { useArtifact, type UseArtifactReturn, type UseArtifactState } from './hooks'

// Components
export { MarkdownPreview, type MarkdownPreviewProps } from './components'

/**
 * Progress Components
 * Real-time SSE progress visualization for analysis pipeline
 */

export { ProgressTracker, type ProgressTrackerProps } from './ProgressTracker'
export { ProgressColumn } from './ProgressColumn'
export { SSEConnectionStatus } from './SSEConnectionStatus'

// Stage data from registry
export { ALL_STAGES, STAGE_CONFIG, WORKING_STAGES } from '../../config/stageRegistry'

// UI helpers from constants
export { type StageState, createInitialStages } from './constants'

// Status formatting from config
export {
  formatAgentName,
  formatStatus,
  getStatusBadgeVariant,
} from '../../config/stageStatusConfig'

// SSE normalization
export {
  normalizeSSEEvent,
  needsStageMapping,
  needsStatusMapping,
  getMappedStageName,
  getMappedStatus,
} from './sseNormalizer'

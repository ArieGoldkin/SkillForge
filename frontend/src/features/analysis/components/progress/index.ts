/**
 * Progress Components
 * Real-time SSE progress visualization for analysis pipeline
 */

export { ProgressTracker, type ProgressTrackerProps } from './ProgressTracker'
export { ProgressColumn } from './ProgressColumn'

// Stage data from registry
export { ALL_STAGES, STAGE_CONFIG, WORKING_STAGES } from '../../config/stageRegistry'

// UI helpers from constants
export {
  type StageState,
  createInitialStages,
  formatAgentName,
  formatStatus,
  getStatusBadgeVariant,
} from './constants'

// SSE normalization
export {
  normalizeSSEEvent,
  needsStageMapping,
  needsStatusMapping,
  getMappedStageName,
  getMappedStatus,
} from './sseNormalizer'

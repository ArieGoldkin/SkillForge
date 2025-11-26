/**
 * Progress Components
 * Real-time SSE progress visualization for analysis pipeline
 */

export { ProgressTracker, type ProgressTrackerProps } from './ProgressTracker'
export { ProgressColumn } from './ProgressColumn'
export {
  ALL_STAGES,
  STAGE_CONFIG,
  WORKING_STAGES,
  type StageState,
  createInitialStages,
  formatAgentName,
  formatStatus,
  getStatusBadgeVariant,
} from './constants'
export {
  normalizeSSEEvent,
  needsStageMapping,
  needsStatusMapping,
  getMappedStageName,
  getMappedStatus,
} from './sseNormalizer'

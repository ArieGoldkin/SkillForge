/**
 * SSE Event Normalizer
 *
 * Transforms backend SSE events to match frontend type definitions.
 * Handles schema differences between backend implementation and frontend spec.
 */

import type {
  StageName,
  StageStatus,
  SSEEvent,
  SSEProgressEvent,
  SSECompleteEvent,
  SSEErrorEvent,
} from '@app-types/sse'

/**
 * Stage name mapping from backend to frontend
 * Backend may use different names than the frontend spec
 */
const STAGE_NAME_MAP: Record<string, StageName> = {
  supervisor: 'supervisor_routing',
  // Add more mappings as backend stages are implemented
  // embedding: 'extraction', // if embedding should map to extraction
}

/**
 * Status mapping from backend to frontend
 * Handles non-standard statuses from backend
 */
const STATUS_MAP: Record<string, StageStatus> = {
  streaming: 'running', // Backend uses 'streaming' during LLM generation
}

/**
 * Valid stage names (from frontend spec)
 */
const VALID_STAGES: StageName[] = [
  'extraction',
  'supervisor_routing',
  'tech_comparison',
  'security_audit',
  'implementation_planning',
  'performance_audit',
  'code_quality_audit',
  'trends_analysis',
  'dependencies_analysis',
  'aggregation',
  'artifact_generation',
]

/**
 * Valid statuses (from frontend spec)
 */
const VALID_STATUSES: StageStatus[] = ['pending', 'running', 'complete', 'failed']

/**
 * Check if a value is a valid stage name
 */
function isValidStageName(stage: string): stage is StageName {
  return VALID_STAGES.includes(stage as StageName)
}

/**
 * Check if a value is a valid status
 */
function isValidStatus(status: string): status is StageStatus {
  return VALID_STATUSES.includes(status as StageStatus)
}

/**
 * Normalize stage name from backend to frontend
 */
function normalizeStage(stage: string): StageName | null {
  // Check if it needs mapping
  if (stage in STAGE_NAME_MAP) {
    return STAGE_NAME_MAP[stage]
  }

  // Check if it's already valid
  if (isValidStageName(stage)) {
    return stage
  }

  // Unknown stage - log warning but don't fail
  console.warn(`[SSE Normalizer] Unknown stage name: ${stage}`)
  return null
}

/**
 * Normalize status from backend to frontend
 */
function normalizeStatus(status: string): StageStatus {
  // Check if it needs mapping
  if (status in STATUS_MAP) {
    return STATUS_MAP[status]
  }

  // Check if it's already valid
  if (isValidStatus(status)) {
    return status
  }

  // Unknown status - default to 'running' with warning
  console.warn(`[SSE Normalizer] Unknown status: ${status}, defaulting to 'running'`)
  return 'running'
}

/**
 * Extract details object from event
 * Backend may put fields at top level or nested in 'details'
 */
function extractDetails(event: Record<string, unknown>): Record<string, unknown> {
  const details: Record<string, unknown> = {}

  // If event has a details object, use it as base
  if (event.details && typeof event.details === 'object') {
    Object.assign(details, event.details)
  }

  // Also check for top-level fields that should be in details
  const detailFields = [
    'word_count',
    'agent',
    'progress_percent',
    'agent_count',
    'selected_agents',
    'token_chunk',
    'accumulated_content',
    'artifact_id',
    'error',
    'error_code',
  ]

  for (const field of detailFields) {
    if (field in event && !(field in details)) {
      details[field] = event[field]
    }
  }

  return details
}

/**
 * Normalize a progress event
 */
function normalizeProgressEvent(event: Record<string, unknown>): SSEProgressEvent | null {
  const stage = normalizeStage(String(event.stage))
  if (!stage) return null

  const status = normalizeStatus(String(event.status))
  const details = extractDetails(event)

  return {
    type: 'progress',
    analysis_id: String(event.analysis_id),
    stage,
    status,
    timestamp: String(event.timestamp),
    details: Object.keys(details).length > 0 ? details : undefined,
  }
}

/**
 * Normalize a complete event
 */
function normalizeCompleteEvent(event: Record<string, unknown>): SSECompleteEvent | null {
  const details = extractDetails(event)

  // artifact_id is required for complete events
  const artifactId = details.artifact_id || event.artifact_id
  if (!artifactId) {
    console.warn('[SSE Normalizer] Complete event missing artifact_id')
  }

  return {
    type: 'complete',
    analysis_id: String(event.analysis_id),
    stage: 'artifact_generation',
    status: 'complete',
    timestamp: String(event.timestamp),
    artifact_id: String(artifactId || ''),
  }
}

/**
 * Normalize an error event
 */
function normalizeErrorEvent(event: Record<string, unknown>): SSEErrorEvent | null {
  const details = extractDetails(event)

  // Extract error message from various possible locations
  const errorMessage = details.error || event.error || 'Unknown error'
  const errorCode = details.error_code || event.error_code

  return {
    type: 'error',
    analysis_id: String(event.analysis_id),
    stage: String(event.stage || 'unknown'),
    status: 'failed',
    timestamp: String(event.timestamp),
    details: {
      error: String(errorMessage),
      ...(errorCode ? { error_code: String(errorCode) } : {}),
    },
  }
}

/**
 * Normalize an SSE event from backend format to frontend types
 *
 * Handles the following transformations:
 * 1. Stage name mapping (e.g., 'supervisor' → 'supervisor_routing')
 * 2. Status normalization (e.g., 'streaming' → 'running')
 * 3. Details extraction (top-level fields → nested details object)
 * 4. Error structure normalization
 *
 * @param rawEvent - The raw event from backend
 * @returns Normalized SSEEvent or null if invalid
 */
export function normalizeSSEEvent(rawEvent: unknown): SSEEvent | null {
  // Handle null/undefined
  if (!rawEvent || typeof rawEvent !== 'object') {
    console.warn('[SSE Normalizer] Invalid event:', rawEvent)
    return null
  }

  const event = rawEvent as Record<string, unknown>

  // Check for required fields
  if (!event.type || !event.analysis_id) {
    console.warn('[SSE Normalizer] Event missing required fields:', event)
    return null
  }

  const eventType = String(event.type)

  switch (eventType) {
    case 'progress':
      return normalizeProgressEvent(event)
    case 'complete':
      return normalizeCompleteEvent(event)
    case 'error':
      return normalizeErrorEvent(event)
    default:
      console.warn(`[SSE Normalizer] Unknown event type: ${eventType}`)
      return null
  }
}

/**
 * Check if an event is from a stage that needs mapping
 * Useful for debugging integration issues
 */
export function needsStageMapping(stage: string): boolean {
  return stage in STAGE_NAME_MAP
}

/**
 * Check if a status needs mapping
 * Useful for debugging integration issues
 */
export function needsStatusMapping(status: string): boolean {
  return status in STATUS_MAP
}

/**
 * Get the mapped stage name (or original if no mapping needed)
 */
export function getMappedStageName(stage: string): StageName | null {
  return normalizeStage(stage)
}

/**
 * Get the mapped status (or original if no mapping needed)
 */
export function getMappedStatus(status: string): StageStatus {
  return normalizeStatus(status)
}

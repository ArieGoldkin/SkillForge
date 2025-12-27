/**
 * Branded/opaque types for domain IDs.
 *
 * 2025 Best Practice: Use branded types for compile-time type safety without runtime overhead.
 * Prevents accidental mixing of different ID types.
 *
 * @example
 * const analysisId = AnalysisID('123e4567-e89b-12d3-a456-426614174000')
 * const artifactId = ArtifactID('987fcdeb-51a2-3bc4-d567-890123456789')
 *
 * // TypeScript error: Type 'ArtifactID' is not assignable to type 'AnalysisID'
 * // fetchAnalysis(artifactId)  // Compile error!
 */

// Core domain IDs
export type AnalysisID = string & { readonly __brand: 'AnalysisID' }
export type ArtifactID = string & { readonly __brand: 'ArtifactID' }
export type SessionID = string & { readonly __brand: 'SessionID' }
export type ChunkID = string & { readonly __brand: 'ChunkID' }

// Other IDs
export type TraceID = string & { readonly __brand: 'TraceID' }
export type TopicID = string & { readonly __brand: 'TopicID' }
export type MessageID = string & { readonly __brand: 'MessageID' }

// UUID validation regex
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isValidUUID(id: string): boolean {
  return UUID_REGEX.test(id)
}

// Factory functions with runtime validation
export function createAnalysisID(id: string): AnalysisID {
  if (!isValidUUID(id)) throw new Error(`Invalid AnalysisID: ${id}`)
  return id as AnalysisID
}

export function createArtifactID(id: string): ArtifactID {
  if (!isValidUUID(id)) throw new Error(`Invalid ArtifactID: ${id}`)
  return id as ArtifactID
}

export function createSessionID(id: string): SessionID {
  if (!isValidUUID(id)) throw new Error(`Invalid SessionID: ${id}`)
  return id as SessionID
}

export function createChunkID(id: string): ChunkID {
  if (!isValidUUID(id)) throw new Error(`Invalid ChunkID: ${id}`)
  return id as ChunkID
}

export function createTraceID(id: string): TraceID {
  // TraceID can be any string format
  return id as TraceID
}

export function createTopicID(id: string): TopicID {
  // TopicID can be any string format
  return id as TopicID
}

export function createMessageID(id: string): MessageID {
  if (!isValidUUID(id)) throw new Error(`Invalid MessageID: ${id}`)
  return id as MessageID
}

// Type guards for runtime checks
export function isAnalysisID(id: unknown): id is AnalysisID {
  return typeof id === 'string' && isValidUUID(id)
}

export function isArtifactID(id: unknown): id is ArtifactID {
  return typeof id === 'string' && isValidUUID(id)
}

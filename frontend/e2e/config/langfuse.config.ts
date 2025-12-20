/**
 * Langfuse E2E Test Configuration
 *
 * Environment Variables:
 * - E2E_ARTIFACT_ID: Target artifact ID for trace visualization tests
 * - E2E_ANALYSIS_ID: Parent analysis ID for the artifact
 * - E2E_TRACE_ID: Langfuse trace ID (optional, for specific trace tests)
 * - E2E_BASE_URL: Frontend base URL (default: http://localhost:5173)
 * - LANGFUSE_URL: Langfuse UI base URL (default: http://localhost:3000)
 * - LANGFUSE_EMAIL: Langfuse login email (default: dev@skillforge.local)
 * - LANGFUSE_PASSWORD: Langfuse login password (default: skillforge-dev-password)
 *
 * Usage:
 * - Local Dev: Uses default UUIDs and localhost URLs
 * - CI: Set environment variables to target real data
 */

export interface LangfuseConfig {
  /** Artifact ID to test trace visualization with */
  artifactId: string;
  /** Analysis ID that owns the artifact */
  analysisId: string;
  /** Optional Langfuse trace ID for specific trace tests */
  traceId?: string;
  /** Frontend base URL */
  baseUrl: string;
  /** Langfuse UI base URL */
  langfuseUrl: string;
  /** Langfuse login credentials */
  langfuseEmail: string;
  langfusePassword: string;
}

/**
 * Default artifact ID for local development
 * This should correspond to a valid artifact in your local database
 */
const DEFAULT_ARTIFACT_ID = '00000000-0000-0000-0000-000000000001';

/**
 * Default analysis ID for local development
 * This should correspond to the analysis that owns the default artifact
 */
const DEFAULT_ANALYSIS_ID = '00000000-0000-0000-0000-000000000001';

/**
 * Main Langfuse E2E test configuration
 */
export const langfuseConfig: LangfuseConfig = {
  // Artifact & Analysis IDs
  artifactId: process.env.E2E_ARTIFACT_ID || DEFAULT_ARTIFACT_ID,
  analysisId: process.env.E2E_ANALYSIS_ID || DEFAULT_ANALYSIS_ID,
  traceId: process.env.E2E_TRACE_ID, // Optional

  // Base URLs
  baseUrl: process.env.E2E_BASE_URL || 'http://localhost:5173',
  langfuseUrl: process.env.LANGFUSE_URL || 'http://localhost:3000',

  // Langfuse Authentication
  langfuseEmail: process.env.LANGFUSE_EMAIL || 'dev@skillforge.local',
  langfusePassword: process.env.LANGFUSE_PASSWORD || 'skillforge-dev-password',
};

/**
 * Builds the full artifact URL with analysis ID query parameter
 *
 * @returns Full URL to artifact page with analysisId query param
 *
 * @example
 * // Returns: http://localhost:5173/artifact/abc-123?analysisId=def-456
 * const url = getArtifactUrl();
 */
export function getArtifactUrl(): string {
  const { baseUrl, artifactId, analysisId } = langfuseConfig;
  return `${baseUrl}/artifact/${artifactId}?analysisId=${analysisId}`;
}

/**
 * Checks if Langfuse is properly configured for CI testing
 *
 * In CI, we expect all environment variables to be set.
 * In local dev, we use defaults and don't require Langfuse to be running.
 *
 * @returns true if running in CI with real Langfuse credentials
 */
export function isLangfuseEnabled(): boolean {
  return !!(
    process.env.E2E_ARTIFACT_ID &&
    process.env.E2E_ANALYSIS_ID &&
    process.env.LANGFUSE_EMAIL &&
    process.env.LANGFUSE_PASSWORD
  );
}

/**
 * Gets the Langfuse trace URL for a given trace ID
 *
 * @param traceId - Langfuse trace ID
 * @returns Full URL to trace in Langfuse UI
 *
 * @example
 * // Returns: http://localhost:3000/project/default/traces/trace-123
 * const url = getLangfuseTraceUrl('trace-123');
 */
export function getLangfuseTraceUrl(traceId: string): string {
  const { langfuseUrl } = langfuseConfig;
  // Project ID from docker-compose.e2e-langfuse.yml LANGFUSE_INIT_PROJECT_ID
  return `${langfuseUrl}/project/skillforge-e2e/traces/${traceId}`;
}

/**
 * Validates that the configuration has valid UUIDs
 * Useful for catching configuration errors early in tests
 *
 * @throws Error if UUIDs are invalid
 */
export function validateConfig(): void {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  if (!uuidRegex.test(langfuseConfig.artifactId)) {
    throw new Error(
      `Invalid E2E_ARTIFACT_ID: ${langfuseConfig.artifactId}. Expected UUID format.`
    );
  }

  if (!uuidRegex.test(langfuseConfig.analysisId)) {
    throw new Error(
      `Invalid E2E_ANALYSIS_ID: ${langfuseConfig.analysisId}. Expected UUID format.`
    );
  }

  // Note: trace_id can be a string (e.g., "e2e-trace-langfuse-integration-test")
  // or a UUID. Langfuse accepts both formats, so we don't validate trace_id format.
}

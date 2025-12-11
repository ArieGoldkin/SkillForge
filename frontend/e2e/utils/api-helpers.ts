import type { Page, APIRequestContext } from '@playwright/test';

/**
 * API helper functions for real E2E testing.
 * These helpers interact with the actual backend API.
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8500';

/**
 * Get API base URL for the test environment.
 */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/**
 * Create a new analysis via the API.
 */
export async function createAnalysis(
  request: APIRequestContext,
  url: string = 'https://example.com/test-article'
): Promise<{ analysis_id: string; sse_endpoint: string }> {
  const response = await request.post(`${API_BASE_URL}/api/v1/analyze`, {
    data: { url },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create analysis: ${response.status()}`);
  }

  return response.json();
}

/**
 * Get analysis status from the API.
 */
export async function getAnalysis(
  request: APIRequestContext,
  analysisId: string
): Promise<{
  analysis_id: string;
  status: string;
  artifact_id?: string;
  url: string;
  content_type: string;
}> {
  const response = await request.get(`${API_BASE_URL}/api/v1/analyze/${analysisId}`);

  if (!response.ok()) {
    throw new Error(`Failed to get analysis: ${response.status()}`);
  }

  return response.json();
}

/**
 * Get library items from the API.
 */
export async function getLibrary(
  request: APIRequestContext,
  params: { limit?: number; offset?: number; status?: string } = {}
): Promise<{
  items: Array<{
    analysis_id: string;
    url: string;
    title: string | null;
    content_type: string;
    status: string;
  }>;
  total: number;
}> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set('limit', params.limit.toString());
  if (params.offset) searchParams.set('offset', params.offset.toString());
  if (params.status) searchParams.set('status', params.status);

  const response = await request.get(`${API_BASE_URL}/api/v1/library?${searchParams}`);

  if (!response.ok()) {
    throw new Error(`Failed to get library: ${response.status()}`);
  }

  return response.json();
}

/**
 * Get a completed analysis with artifact from the API.
 * Returns the first completed analysis found, or null if none exist.
 */
export async function getCompletedAnalysis(
  request: APIRequestContext
): Promise<{
  analysis_id: string;
  artifact_id: string;
  url: string;
} | null> {
  // Get completed analyses (API uses 'completed' status)
  const library = await getLibrary(request, { status: 'completed', limit: 20 });

  if (library.items.length === 0) {
    return null;
  }

  // Find the first analysis that has an artifact (not all completed analyses have artifacts)
  for (const item of library.items) {
    try {
      const analysis = await getAnalysis(request, item.analysis_id);
      if (analysis.artifact_id) {
        return {
          analysis_id: analysis.analysis_id,
          artifact_id: analysis.artifact_id,
          url: analysis.url,
        };
      }
    } catch {
      // Skip analyses without artifacts
      continue;
    }
  }

  return null;
}

/**
 * Get artifact content via analysis endpoint.
 */
export async function getArtifact(
  request: APIRequestContext,
  analysisId: string
): Promise<{
  artifact_id: string;
  markdown_content: string;
  artifact_metadata: Record<string, unknown> | null;
}> {
  const response = await request.get(`${API_BASE_URL}/api/v1/analyze/${analysisId}/artifact`);

  if (!response.ok()) {
    throw new Error(`Failed to get artifact: ${response.status()}`);
  }

  return response.json();
}

/**
 * Wait for the backend to be healthy.
 */
export async function waitForBackend(request: APIRequestContext, timeout = 30000): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const response = await request.get(`${API_BASE_URL}/api/v1/health`);
      if (response.ok()) {
        return;
      }
    } catch {
      // Backend not ready yet
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Backend not healthy after ${timeout}ms`);
}

/**
 * Create a tutor session via the API.
 */
export async function createTutorSession(
  request: APIRequestContext,
  analysisId: string,
  userLevel: string = 'intermediate'
): Promise<{ session_id: string; status: string; sse_endpoint: string }> {
  const response = await request.post(`${API_BASE_URL}/api/v1/tutor/sessions`, {
    data: { analysis_id: analysisId, user_level: userLevel },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create tutor session: ${response.status()}`);
  }

  return response.json();
}

/**
 * Get a tutor session with conversation history.
 */
export async function getTutorSession(
  request: APIRequestContext,
  sessionId: string
): Promise<{
  session_id: string;
  analysis_id: string | null;
  status: string;
  syllabus: Record<string, unknown> | null;
  current_section: number;
  current_lesson: number;
  current_phase: string;
  user_level: string;
  messages: Array<{
    role: string;
    content: string;
    created_at: string;
    metadata: Record<string, unknown> | null;
  }>;
  started_at: string;
  completed_at: string | null;
}> {
  const response = await request.get(`${API_BASE_URL}/api/v1/tutor/sessions/${sessionId}`);

  if (!response.ok()) {
    throw new Error(`Failed to get tutor session: ${response.status()}`);
  }

  return response.json();
}

/**
 * Send a message in a tutor session.
 */
export async function sendTutorMessage(
  request: APIRequestContext,
  sessionId: string,
  content: string
): Promise<{ message_id: string; status: string }> {
  const response = await request.post(
    `${API_BASE_URL}/api/v1/tutor/sessions/${sessionId}/messages`,
    {
      data: { content },
    }
  );

  if (!response.ok()) {
    throw new Error(`Failed to send tutor message: ${response.status()}`);
  }

  return response.json();
}

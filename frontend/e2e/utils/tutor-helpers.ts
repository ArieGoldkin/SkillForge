import type { APIRequestContext } from '@playwright/test';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8500';

/**
 * Options for waiting for assistant response.
 */
interface WaitForAssistantResponseOptions {
  initialMessageCount?: number;
  maxWaitMs?: number;
  pollIntervalMs?: number;
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

/**
 * Wait for an assistant response in a tutor session.
 * Polls the session endpoint until an assistant message appears.
 *
 * @param request - Playwright API request context
 * @param sessionId - The tutor session ID
 * @param options - Wait options (initialMessageCount, maxWaitMs, pollIntervalMs)
 * @returns true if response received, false if timeout
 */
export async function waitForAssistantResponse(
  request: APIRequestContext,
  sessionId: string,
  options: WaitForAssistantResponseOptions = {}
): Promise<boolean> {
  const { initialMessageCount = 0, maxWaitMs = 60000, pollIntervalMs = 2000 } = options;
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    try {
      const session = await getTutorSession(request, sessionId);
      const assistantMessages = session.messages.filter((m) => m.role === 'assistant');

      // Check if we have more assistant messages than before
      if (assistantMessages.length > initialMessageCount) {
        return true;
      }
    } catch {
      // Session might be temporarily unavailable, continue polling
    }

    await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
  }

  return false;
}

/**
 * Send a message and wait for the LLM response.
 * Combines sendTutorMessage with waitForAssistantResponse for convenience.
 *
 * @param request - Playwright API request context
 * @param sessionId - The tutor session ID
 * @param content - Message content to send
 * @param maxWaitMs - Maximum time to wait for response (default: 60 seconds)
 * @returns The updated session with the assistant response, or null if timeout
 */
export async function sendMessageAndWaitForResponse(
  request: APIRequestContext,
  sessionId: string,
  content: string,
  maxWaitMs: number = 60000
): Promise<Awaited<ReturnType<typeof getTutorSession>> | null> {
  // Get initial message count
  const initialSession = await getTutorSession(request, sessionId);
  const initialAssistantCount = initialSession.messages.filter((m) => m.role === 'assistant').length;

  // Send the message
  await sendTutorMessage(request, sessionId, content);

  // Wait for response
  const gotResponse = await waitForAssistantResponse(request, sessionId, {
    initialMessageCount: initialAssistantCount,
    maxWaitMs,
  });

  if (!gotResponse) {
    return null;
  }

  // Return the updated session
  return getTutorSession(request, sessionId);
}


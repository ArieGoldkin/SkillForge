/**
 * Mock data for analysis API responses.
 */
export const mockAnalysisResponse = {
  analysis_id: 'test-analysis-123',
  url: 'https://example.com/article',
  content_type: 'article',
  status: 'processing',
  sse_endpoint: '/api/v1/analyze/test-analysis-123/stream',
  created_at: '2025-12-11T10:00:00Z',
};

export const mockAnalysisComplete = {
  ...mockAnalysisResponse,
  status: 'complete',
  artifact_id: 'test-artifact-456',
  completed_at: '2025-12-11T10:05:00Z',
};

export const mockAnalysisFailed = {
  ...mockAnalysisResponse,
  status: 'failed',
  error: 'Content extraction failed',
};

/**
 * SSE progress events for the analysis pipeline.
 */
export interface SSEProgressEvent {
  event: string;
  data: {
    stage: string;
    status: 'running' | 'complete' | 'failed';
    progress: number;
    message?: string;
  };
}

export const mockSSEEvents: SSEProgressEvent[] = [
  { event: 'progress', data: { stage: 'extraction', status: 'running', progress: 5 } },
  { event: 'progress', data: { stage: 'extraction', status: 'complete', progress: 15 } },
  { event: 'progress', data: { stage: 'supervisor_routing', status: 'running', progress: 20 } },
  { event: 'progress', data: { stage: 'supervisor_routing', status: 'complete', progress: 25 } },
  { event: 'progress', data: { stage: 'tech_comparator', status: 'running', progress: 30 } },
  { event: 'progress', data: { stage: 'tech_comparator', status: 'complete', progress: 45 } },
  { event: 'progress', data: { stage: 'security_auditor', status: 'running', progress: 50 } },
  { event: 'progress', data: { stage: 'security_auditor', status: 'complete', progress: 60 } },
  { event: 'progress', data: { stage: 'aggregation', status: 'running', progress: 70 } },
  { event: 'progress', data: { stage: 'aggregation', status: 'complete', progress: 85 } },
  { event: 'progress', data: { stage: 'artifact_generation', status: 'running', progress: 90 } },
  { event: 'progress', data: { stage: 'artifact_generation', status: 'complete', progress: 100 } },
  { event: 'complete', data: { stage: 'complete', status: 'complete', progress: 100, message: 'Analysis complete' } },
];

/**
 * Create SSE event string for mocking.
 */
export function formatSSEEvent(event: SSEProgressEvent): string {
  return `event: ${event.event}\ndata: ${JSON.stringify(event.data)}\n\n`;
}

/**
 * Create full SSE stream from events.
 */
export function createSSEStream(events: SSEProgressEvent[] = mockSSEEvents): string {
  return events.map(formatSSEEvent).join('');
}

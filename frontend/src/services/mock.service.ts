import type {
  Analysis,
  AnalyzeRequest,
  AnalyzeResponse,
  Artifact,
  TutoringSession,
  TutoringMessage,
} from '@/types/api'

// Mock data for development (until backend is ready)

// Multiple analyses for Library page
export const mockAnalyses: Analysis[] = [
  {
    id: '550e8400-e29b-41d4-a716-446655440000',
    url: 'https://react.dev/reference/rsc/server-components',
    content_type: 'article',
    title: 'Introduction to React Server Components',
    status: 'complete',
    created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    artifact_id: 'artifact-123',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440001',
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    content_type: 'video',
    title: 'Advanced TypeScript Patterns',
    status: 'complete',
    created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
    artifact_id: 'artifact-124',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440002',
    url: 'https://github.com/vercel/next.js',
    content_type: 'repo',
    title: 'Next.js Repository Analysis',
    status: 'complete',
    created_at: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
    artifact_id: 'artifact-125',
  },
  {
    id: '550e8400-e29b-41d4-a716-446655440003',
    url: 'https://python.org/docs',
    content_type: 'article',
    title: 'Python Documentation Deep Dive',
    status: 'analyzing',
    created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    artifact_id: null,
  },
]

export const mockAnalysis: Analysis = mockAnalyses[0]

export const mockArtifact: Artifact = {
  id: 'artifact-123',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  markdown_content: `# Implementation Guide: React Server Components

## Overview
React Server Components allow you to write components that render on the server...

## Key Concepts
- Server Components run only on the server
- Client Components run in the browser
- Data fetching happens on the server

## Example Code
\`\`\`typescript
async function ServerComponent() {
  const data = await fetch('https://api.example.com/data')
  return <div>{data.title}</div>
}
\`\`\`
`,
  version: 1,
  metadata: {
    topics: ['React', 'Server Components', 'Next.js'],
    complexity: 'intermediate',
    word_count: 1250,
  },
  download_count: 0,
  created_at: new Date().toISOString(),
}

export const mockTutoringSession: TutoringSession = {
  id: 'session-456',
  analysis_id: '550e8400-e29b-41d4-a716-446655440000',
  status: 'active',
  started_at: new Date().toISOString(),
  completed_at: null,
}

export const mockTutoringMessages: TutoringMessage[] = [
  {
    id: 'msg-1',
    session_id: 'session-456',
    role: 'assistant',
    content:
      'Hello! I can help you implement React Server Components. What would you like to learn?',
    created_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 'msg-2',
    session_id: 'session-456',
    role: 'user',
    content: 'How do I fetch data in a Server Component?',
    created_at: new Date(Date.now() - 240000).toISOString(),
  },
  {
    id: 'msg-3',
    session_id: 'session-456',
    role: 'assistant',
    content:
      'Great question! In Server Components, you can fetch data directly using async/await. Here\'s an example:\n\n```typescript\nasync function UserProfile({ userId }: { userId: string }) {\n  const user = await fetch(`https://api.example.com/users/${userId}`)\n  const data = await user.json()\n  return <div>{data.name}</div>\n}\n```\n\nWhat makes this powerful is that it runs on the server, so you never expose API keys to the client.',
    created_at: new Date(Date.now() - 180000).toISOString(),
  },
]

// Mock API functions (to be replaced with real API calls)

export const mockAnalyzeAPI = {
  createAnalysis: async (_request: AnalyzeRequest): Promise<AnalyzeResponse> => {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    const analysisId = `analysis-${Date.now()}`
    return {
      analysis_id: analysisId,
      sse_endpoint: `/api/v1/analyze/${analysisId}/stream`,
      status: 'pending',
    }
  },

  getAnalysis: async (id: string): Promise<Analysis> => {
    await new Promise((resolve) => setTimeout(resolve, 300))
    const found = mockAnalyses.find((a) => a.id === id)
    return found || mockAnalysis
  },

  getArtifact: async (_id: string): Promise<Artifact> => {
    await new Promise((resolve) => setTimeout(resolve, 300))
    return mockArtifact
  },

  listAnalyses: async (): Promise<Analysis[]> => {
    await new Promise((resolve) => setTimeout(resolve, 400))
    return mockAnalyses
  },
}

export const mockTutoringAPI = {
  createSession: async (_analysisId: string): Promise<TutoringSession> => {
    await new Promise((resolve) => setTimeout(resolve, 400))
    return mockTutoringSession
  },

  getSession: async (_sessionId: string): Promise<TutoringSession> => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return mockTutoringSession
  },

  getMessages: async (_sessionId: string): Promise<TutoringMessage[]> => {
    await new Promise((resolve) => setTimeout(resolve, 200))
    return mockTutoringMessages
  },

  sendMessage: async (sessionId: string, content: string): Promise<TutoringMessage> => {
    await new Promise((resolve) => setTimeout(resolve, 600))
    return {
      id: `msg-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
  },
}

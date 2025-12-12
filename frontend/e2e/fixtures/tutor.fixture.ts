/**
 * Mock data for tutor/chat API responses.
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface TutorSession {
  session_id: string;
  artifact_id: string;
  title: string;
  created_at: string;
  messages: ChatMessage[];
}

export const mockTutorSession: TutorSession = {
  session_id: 'session-123',
  artifact_id: 'test-artifact-456',
  title: 'React Hooks Discussion',
  created_at: '2025-12-11T10:10:00Z',
  messages: [],
};

export const mockTutorSessionWithHistory: TutorSession = {
  ...mockTutorSession,
  messages: [
    {
      id: 'msg-1',
      role: 'user',
      content: 'Can you explain useEffect cleanup?',
      timestamp: '2025-12-11T10:11:00Z',
    },
    {
      id: 'msg-2',
      role: 'assistant',
      content:
        'Great question! The cleanup function in useEffect is called when the component unmounts or before the effect runs again. This is essential for preventing memory leaks. Can you think of a scenario where cleanup would be important?',
      timestamp: '2025-12-11T10:11:30Z',
    },
    {
      id: 'msg-3',
      role: 'user',
      content: 'Maybe when setting up event listeners?',
      timestamp: '2025-12-11T10:12:00Z',
    },
    {
      id: 'msg-4',
      role: 'assistant',
      content:
        "Exactly! Event listeners are a perfect example. If you add a window resize listener without cleanup, it would continue running even after the component unmounts. Here's a pattern to follow:\n\n```javascript\nuseEffect(() => {\n  const handleResize = () => { /* ... */ };\n  window.addEventListener('resize', handleResize);\n  return () => window.removeEventListener('resize', handleResize);\n}, []);\n```\n\nWhat other scenarios can you think of that might need cleanup?",
      timestamp: '2025-12-11T10:12:45Z',
    },
  ],
};

export interface ChatResponse {
  message: ChatMessage;
  suggested_questions?: string[];
}

export const mockChatResponse: ChatResponse = {
  message: {
    id: 'msg-new',
    role: 'assistant',
    content:
      "That's an excellent question! Let me help you understand this concept better. What specific aspect would you like to explore first?",
    timestamp: new Date().toISOString(),
  },
  suggested_questions: [
    'How does this relate to the previous concept?',
    'Can you show me a code example?',
    'What are common mistakes to avoid?',
  ],
};

export const mockStreamingResponse = (content: string): string[] => {
  // Simulate streaming by breaking content into chunks
  const words = content.split(' ');
  const chunks: string[] = [];
  let current = '';

  for (const word of words) {
    current += (current ? ' ' : '') + word;
    if (current.length > 20) {
      chunks.push(current);
      current = '';
    }
  }
  if (current) chunks.push(current);

  return chunks;
};

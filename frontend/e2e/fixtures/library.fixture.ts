/**
 * Mock data for library API responses.
 */
export interface LibraryItem {
  analysis_id: string;
  title: string;
  url: string;
  content_type: 'article' | 'video' | 'repository';
  status: 'complete' | 'processing' | 'failed';
  tags: string[];
  created_at: string;
  artifact_id?: string;
}

export const mockLibraryItems: LibraryItem[] = [
  {
    analysis_id: 'analysis-1',
    title: 'React Hooks Deep Dive',
    url: 'https://example.com/react-hooks',
    content_type: 'article',
    status: 'complete',
    tags: ['React', 'Hooks', 'Frontend'],
    created_at: '2025-12-10T10:00:00Z',
    artifact_id: 'artifact-1',
  },
  {
    analysis_id: 'analysis-2',
    title: 'TypeScript Advanced Patterns',
    url: 'https://example.com/typescript',
    content_type: 'article',
    status: 'complete',
    tags: ['TypeScript', 'Patterns'],
    created_at: '2025-12-09T14:30:00Z',
    artifact_id: 'artifact-2',
  },
  {
    analysis_id: 'analysis-3',
    title: 'Node.js Performance Tutorial',
    url: 'https://youtube.com/watch?v=abc123',
    content_type: 'video',
    status: 'complete',
    tags: ['Node.js', 'Performance', 'Backend'],
    created_at: '2025-12-08T09:15:00Z',
    artifact_id: 'artifact-3',
  },
  {
    analysis_id: 'analysis-4',
    title: 'FastAPI Best Practices',
    url: 'https://github.com/example/fastapi-demo',
    content_type: 'repository',
    status: 'complete',
    tags: ['FastAPI', 'Python', 'API'],
    created_at: '2025-12-07T16:45:00Z',
    artifact_id: 'artifact-4',
  },
  {
    analysis_id: 'analysis-5',
    title: 'GraphQL vs REST Comparison',
    url: 'https://example.com/graphql-rest',
    content_type: 'article',
    status: 'complete',
    tags: ['GraphQL', 'REST', 'API'],
    created_at: '2025-12-06T11:20:00Z',
    artifact_id: 'artifact-5',
  },
];

export interface LibraryResponse {
  items: LibraryItem[];
  total: number;
  limit: number;
  offset: number;
}

export const mockLibraryResponse: LibraryResponse = {
  items: mockLibraryItems,
  total: mockLibraryItems.length,
  limit: 15,
  offset: 0,
};

export const mockEmptyLibraryResponse: LibraryResponse = {
  items: [],
  total: 0,
  limit: 15,
  offset: 0,
};

export const mockFilteredLibraryResponse = (contentType: string): LibraryResponse => {
  const filtered = mockLibraryItems.filter(
    (item) => contentType === 'all' || item.content_type === contentType
  );
  return {
    items: filtered,
    total: filtered.length,
    limit: 15,
    offset: 0,
  };
};

export const mockSearchLibraryResponse = (query: string): LibraryResponse => {
  const filtered = mockLibraryItems.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.tags.some((tag) => tag.toLowerCase().includes(query.toLowerCase()))
  );
  return {
    items: filtered,
    total: filtered.length,
    limit: 15,
    offset: 0,
  };
};

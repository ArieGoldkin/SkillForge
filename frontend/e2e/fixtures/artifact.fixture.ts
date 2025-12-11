/**
 * Mock data for artifact API responses.
 */
export const mockArtifactMetadata = {
  artifact_id: 'test-artifact-456',
  analysis_id: 'test-analysis-123',
  title: 'React Hooks Best Practices',
  topics: ['React', 'Hooks', 'TypeScript', 'State Management'],
  complexity: 'intermediate',
  word_count: 2500,
  created_at: '2025-12-11T10:05:00Z',
};

export const mockArtifactContent = `# React Hooks Best Practices

## Executive Summary

This implementation guide covers modern React Hooks patterns and best practices for building scalable applications.

## Key Findings

### 1. State Management

- Use \`useState\` for local component state
- Use \`useReducer\` for complex state logic
- Consider Zustand or Jotai for global state

### 2. Side Effects

- Use \`useEffect\` for side effects
- Always cleanup subscriptions
- Use dependency arrays correctly

### 3. Performance Optimization

- Memoize expensive calculations with \`useMemo\`
- Memoize callbacks with \`useCallback\`
- Use \`React.memo\` for pure components

## Code Examples

### Custom Hook Example

\`\`\`typescript
import { useState, useCallback } from 'react';

interface UseCounterOptions {
  initialValue?: number;
  min?: number;
  max?: number;
}

export function useCounter(options: UseCounterOptions = {}) {
  const { initialValue = 0, min = -Infinity, max = Infinity } = options;
  const [count, setCount] = useState(initialValue);

  const increment = useCallback(() => {
    setCount((c) => Math.min(c + 1, max));
  }, [max]);

  const decrement = useCallback(() => {
    setCount((c) => Math.max(c - 1, min));
  }, [min]);

  const reset = useCallback(() => {
    setCount(initialValue);
  }, [initialValue]);

  return { count, increment, decrement, reset };
}
\`\`\`

### Usage Example

\`\`\`typescript
function Counter() {
  const { count, increment, decrement, reset } = useCounter({
    initialValue: 0,
    min: 0,
    max: 100,
  });

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={decrement}>-</button>
      <button onClick={increment}>+</button>
      <button onClick={reset}>Reset</button>
    </div>
  );
}
\`\`\`

## Recommendations

1. **Extract Custom Hooks**: Move reusable logic into custom hooks
2. **Follow Rules of Hooks**: Only call hooks at the top level
3. **Use TypeScript**: Add type safety to your hooks
4. **Test Your Hooks**: Use @testing-library/react-hooks

## Next Steps

- Review the official React documentation
- Practice building custom hooks
- Explore advanced patterns like compound components
`;

export const mockArtifactWithMetadata = {
  ...mockArtifactMetadata,
  markdown_content: mockArtifactContent,
};

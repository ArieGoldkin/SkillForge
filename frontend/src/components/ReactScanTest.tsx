import { useState } from 'react'

/**
 * Simple test component to verify React Scan performance monitoring
 */
export function ReactScanTest() {
  const [count, setCount] = useState(0)

  return (
    <div className="p-4 border rounded-md shadow-sm">
      <h3 className="text-lg font-semibold">React Scan Test</h3>
      <p>Count: {count}</p>
      <button
        className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        onClick={() => setCount((c) => c + 1)}
      >
        Increment
      </button>
      <p className="mt-2 text-sm text-gray-500">
        Open DevTools to observe component outlines for performance feedback.
      </p>
    </div>
  )
}

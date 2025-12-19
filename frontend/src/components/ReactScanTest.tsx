import { useState } from 'react'

/**
 * Test component to verify React Scan performance monitoring
 * This component intentionally causes re-renders to test detection
 */
export function ReactScanTest() {
  const [count, setCount] = useState(0)
  const [items, setItems] = useState<number[]>([])

  const handleIncrement = () => {
    setCount((prev) => prev + 1)
  }

  const handleAddItem = () => {
    setItems((prev) => [...prev, Date.now()])
  }

  const handleClearItems = () => {
    setItems([])
  }

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm">
      <h3 className="text-lg font-semibold mb-4">React Scan Performance Test</h3>

      <div className="space-y-4">
        {/* Counter test - should show re-render highlighting */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium">Counter: {count}</span>
          <button
            onClick={handleIncrement}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Increment
          </button>
        </div>

        {/* Array manipulation test - should trigger re-renders */}
        <div className="space-y-2">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Items: {items.length}</span>
            <button
              onClick={handleAddItem}
              className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Add Item
            </button>
            <button
              onClick={handleClearItems}
              className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Clear All
            </button>
          </div>

          {items.length > 0 && (
            <div className="max-h-32 overflow-y-auto border rounded p-2 bg-gray-50">
              <ul className="space-y-1">
                {items.map((item, index) => (
                  <li key={item} className="text-xs text-gray-600">
                    Item {index + 1}: {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="text-xs text-gray-500 bg-yellow-50 p-2 rounded border">
          <strong>React Scan Test:</strong> Click buttons above. If React Scan is working, you
          should see colored outlines around components that re-render, and a toolbar in the
          bottom-right corner showing render counts.
        </div>
      </div>
    </div>
  )
}

import { useEffect, useRef } from 'react'

/**
 * Custom hook for infinite scroll using IntersectionObserver
 *
 * Triggers the onLoadMore callback when the sentinel element
 * enters the viewport (with a 200px margin before visibility).
 *
 * @param onLoadMore - Callback to trigger when more items should be loaded
 * @param canLoadMore - Whether more items are available to load
 * @returns Ref to attach to the sentinel element
 */
export function useInfiniteScroll(
  onLoadMore: (() => void) | undefined,
  canLoadMore: boolean
): React.RefObject<HTMLDivElement> {
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!onLoadMore || !canLoadMore) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting) {
          onLoadMore()
        }
      },
      {
        root: null,
        rootMargin: '200px', // trigger slightly before reaching the end
        threshold: 0.1,
      }
    )

    const sentinel = sentinelRef.current
    if (sentinel) observer.observe(sentinel)

    return () => {
      if (sentinel) observer.unobserve(sentinel)
      observer.disconnect()
    }
  }, [onLoadMore, canLoadMore])

  return sentinelRef
}

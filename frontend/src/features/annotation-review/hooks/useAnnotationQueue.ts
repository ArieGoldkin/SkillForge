/**
 * Hook for fetching and managing annotation queue items.
 * Uses TanStack Query for data fetching, caching, and optimistic updates.
 */

import type { AnnotationQueueItem } from '@app-types/annotations'
import { useToast } from '@hooks/use-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { annotationsAPI } from '@/api/annotations'

interface UseAnnotationQueueOptions {
  limit?: number
  offset?: number
  status?: string
}

export function useAnnotationQueue(options: UseAnnotationQueueOptions = {}) {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  // Fetch annotation queue
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['annotationQueue', options],
    queryFn: () => annotationsAPI.getAnnotationQueue(options),
    staleTime: 1000 * 60, // 1 minute
  })

  // Mark as reviewed mutation
  const markReviewedMutation = useMutation({
    mutationFn: (queueId: number) => annotationsAPI.markReviewed(queueId),
    onMutate: async (queueId) => {
      // Cancel ongoing queries
      await queryClient.cancelQueries({ queryKey: ['annotationQueue'] })

      // Snapshot previous value
      const previousData = queryClient.getQueryData(['annotationQueue', options])

      // Optimistically update queue
      queryClient.setQueryData(['annotationQueue', options], (old: any) => {
        if (!old) return old
        return {
          ...old,
          items: old.items.map((item: AnnotationQueueItem) =>
            item.id === queueId
              ? { ...item, status: 'reviewed', reviewed_at: new Date().toISOString() }
              : item
          ),
        }
      })

      return { previousData }
    },
    onSuccess: (data) => {
      toast({
        title: 'Marked as reviewed',
        description: data.message,
        variant: 'success',
      })
    },
    onError: (error, _queueId, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(['annotationQueue', options], context.previousData)
      }
      toast({
        title: 'Failed to mark as reviewed',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      })
    },
    onSettled: () => {
      // Refetch to ensure data consistency
      queryClient.invalidateQueries({ queryKey: ['annotationQueue'] })
    },
  })

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    limit: data?.limit ?? options.limit ?? 20,
    offset: data?.offset ?? options.offset ?? 0,
    isLoading,
    error,
    refetch,
    markReviewed: markReviewedMutation.mutate,
    isMarkingReviewed: markReviewedMutation.isPending,
  }
}

/**
 * Hook for fetching and managing annotation queue items.
 * Uses TanStack Query for data fetching, caching, and optimistic updates.
 */

import type { AnnotationQueueItem, AnnotationQueueListResponse } from '@app-types/annotations'
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
  const queryKey = ['annotationQueue', options]

  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () => annotationsAPI.getAnnotationQueue(options),
    staleTime: 60_000,
  })

  const markReviewedMutation = useMutation({
    mutationFn: (queueId: number) => annotationsAPI.markReviewed(queueId),
    onMutate: async (queueId) => {
      await queryClient.cancelQueries({ queryKey: ['annotationQueue'] })
      const previousData = queryClient.getQueryData<AnnotationQueueListResponse>(queryKey)
      queryClient.setQueryData<AnnotationQueueListResponse>(queryKey, (old) =>
        old ? { ...old, items: updateItemStatus(old.items, queueId) } : old
      )
      return { previousData }
    },
    onSuccess: (result) =>
      toast({ title: 'Marked as reviewed', description: result.message, variant: 'success' }),
    onError: (err, _id, ctx) => {
      if (ctx?.previousData) queryClient.setQueryData(queryKey, ctx.previousData)
      toast({
        title: 'Failed to mark as reviewed',
        description: err instanceof Error ? err.message : 'An error occurred',
        variant: 'destructive',
      })
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['annotationQueue'] }),
  })

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    refetch,
    markReviewed: markReviewedMutation.mutate,
    isMarkingReviewed: markReviewedMutation.isPending,
  }
}

function updateItemStatus(items: AnnotationQueueItem[], queueId: number): AnnotationQueueItem[] {
  return items.map((item) =>
    item.id === queueId
      ? { ...item, status: 'reviewed', reviewed_at: new Date().toISOString() }
      : item
  )
}

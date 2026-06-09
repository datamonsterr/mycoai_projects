import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { indexService } from '@/services/index'
import type { IndexStatus, ReindexRequest } from '@/services/types'

export function useIndexStatus() {
  return useQuery<IndexStatus>({
    queryKey: ['index', 'status'],
    queryFn: () => indexService.getIndexStatus(),
  })
}

export function useTriggerReindex() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (scope: ReindexRequest['scope']) =>
      indexService.triggerReindex(scope),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['index'] })
    },
  })
}

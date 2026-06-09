import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { RetrievalQueryRequest, RetrievalJobResponse } from '@/services/types'
import { startQuery, getJobStatus, getJobResults, querySync } from '@/services/retrieval'

export function useStartRetrieval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: RetrievalQueryRequest) => startQuery(data),
    onSuccess: (data: RetrievalJobResponse) => {
      queryClient.setQueryData(['retrieval-job', data.job_id], data)
    },
  })
}

export function useJobStatus(jobId: string) {
  return useQuery({
    queryKey: ['retrieval-job', jobId],
    queryFn: () => getJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = (query.state.data as RetrievalJobResponse | undefined)?.status
      if (status === 'completed' || status === 'failed') return false
      return 2000
    },
  })
}

export function useJobResults(jobId: string, status: string | undefined) {
  return useQuery({
    queryKey: ['retrieval-results', jobId],
    queryFn: () => getJobResults(jobId),
    enabled: !!jobId && status === 'completed',
  })
}

export function useQuerySync() {
  return useMutation({
    mutationFn: (data: RetrievalQueryRequest) => querySync(data),
  })
}

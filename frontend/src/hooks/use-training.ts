import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { training } from '@/services/training'
import type { TrainingJobItem, TrainingStatus } from '@/services/types'

export function useTrainingStatus() {
  return useQuery<TrainingStatus>({
    queryKey: ['training', 'status'],
    queryFn: () => training.getStatus(),
  })
}

export function useTrainingJobs() {
  return useQuery<TrainingJobItem[]>({
    queryKey: ['training', 'jobs'],
    queryFn: () => training.listJobs(),
  })
}

export function useTrainingJob(jobId: string) {
  return useQuery<TrainingJobItem>({
    queryKey: ['training', 'jobs', jobId],
    queryFn: () => training.getJob(jobId),
    enabled: !!jobId,
  })
}

export function useTriggerTraining() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (reason?: string) => training.triggerTraining(reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] })
    },
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => training.cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] })
    },
  })
}

export function useDeployModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, force }: { jobId: string; force?: boolean }) =>
      training.deployModel(jobId, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] })
    },
  })
}

export function useRollbackModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => training.rollbackModel(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] })
    },
  })
}

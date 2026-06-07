import { api } from '@/services/api-client'
import type { TrainingStatus, TrainingJobItem } from '@/services/types'

export const training = {
  getStatus: () => api.get<TrainingStatus>('/training/status'),

  listJobs: () => api.get<TrainingJobItem[]>('/training/jobs'),

  triggerTraining: (reason?: string) =>
    api.post<{ job_id: string }>('/training/trigger', { reason }),

  getJob: (jobId: string) =>
    api.get<TrainingJobItem>(`/training/jobs/${jobId}`),

  cancelJob: (jobId: string) =>
    api.post<void>(`/training/jobs/${jobId}/cancel`),

  deployModel: (jobId: string, force?: boolean) =>
    api.post<{ status: string }>(`/training/jobs/${jobId}/deploy`, { force }),

  rollbackModel: () =>
    api.post<{ status: string }>('/training/rollback'),
}

import { api } from '@/services/api-client'
import type { IndexStatus, ReindexRequest } from '@/services/types'

export const indexService = {
  triggerReindex: (scope: ReindexRequest['scope']) =>
    api.post<{ status: string }>('/index/reindex', { scope }),

  getIndexStatus: () =>
    api.get<IndexStatus>('/index/status'),
}

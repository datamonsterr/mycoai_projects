import { api } from '@/services/api-client'
import type { FeedbackCreate, FeedbackUpdate, FeedbackResponse, FeedbackBatchRequest, PaginatedResponse } from '@/services/types'

export const feedbackService = {
  submit(data: FeedbackCreate) {
    return api.post<FeedbackResponse>('/feedback', data)
  },

  listMy(params?: { offset?: number; limit?: number; status?: string }) {
    const { offset = 0, limit = 50, status } = params ?? {}
    return api.get<PaginatedResponse<FeedbackResponse>>('/feedback', { params: { offset, limit, status } })
  },

  inbox(params?: { offset?: number; limit?: number; status?: string }) {
    const { offset = 0, limit = 50, status } = params ?? {}
    return api.get<PaginatedResponse<FeedbackResponse>>('/feedback/inbox', { params: { offset, limit, status } })
  },

  review(id: string, data: FeedbackUpdate) {
    return api.patch<FeedbackResponse>(`/feedback/${id}`, data)
  },

  batchReview(data: FeedbackBatchRequest) {
    return api.post<{ updated: number }>('/feedback/batch', data)
  },
}

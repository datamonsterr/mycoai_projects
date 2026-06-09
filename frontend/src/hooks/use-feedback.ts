import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { feedbackService } from '@/services/feedback'
import type { FeedbackCreate, FeedbackUpdate, FeedbackBatchRequest } from '@/services/types'

export function useSubmitFeedback() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FeedbackCreate) => feedbackService.submit(data),
    onSuccess: () => {
      toast.success('Feedback submitted')
      qc.invalidateQueries({ queryKey: ['feedback'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export function useMyFeedback(params?: { offset?: number; limit?: number; status?: string }) {
  return useQuery({
    queryKey: ['feedback', 'my', params],
    queryFn: () => feedbackService.listMy(params),
  })
}

export function useFeedbackInbox(params?: { offset?: number; limit?: number; status?: string }) {
  return useQuery({
    queryKey: ['feedback', 'inbox', params],
    queryFn: () => feedbackService.inbox(params),
  })
}

export function useReviewFeedback() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: FeedbackUpdate }) => feedbackService.review(id, data),
    onSuccess: () => {
      toast.success('Feedback reviewed')
      qc.invalidateQueries({ queryKey: ['feedback'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

export function useBatchReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: FeedbackBatchRequest) => feedbackService.batchReview(data),
    onSuccess: (result) => {
      toast.success(`${result.updated} feedback items updated`)
      qc.invalidateQueries({ queryKey: ['feedback'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })
}

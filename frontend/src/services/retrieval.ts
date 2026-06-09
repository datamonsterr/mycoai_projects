import type {
  RetrievalQueryRequest,
  RetrievalJobResponse,
  RetrievalResultsResponse,
} from '@/services/types'
import { api } from '@/services/api-client'

export function startQuery(data: RetrievalQueryRequest): Promise<RetrievalJobResponse> {
  return api.post('/retrieval/query', data)
}

export function getJobStatus(jobId: string): Promise<RetrievalJobResponse> {
  return api.get(`/retrieval/jobs/${jobId}`)
}

export function getJobResults(jobId: string): Promise<RetrievalResultsResponse> {
  return api.get(`/retrieval/jobs/${jobId}/results`)
}

export function querySync(data: RetrievalQueryRequest): Promise<RetrievalResultsResponse> {
  return api.post('/retrieval/query-sync', data)
}

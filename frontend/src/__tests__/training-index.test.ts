import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/services/api-client', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
  ApiError: class extends Error {
    status: number
    detail: Record<string, unknown> | null
    constructor(status: number, detail: string | Record<string, unknown> | null) {
      const message = typeof detail === 'string' ? detail : 'fail'
      super(message)
      this.status = status
      this.detail = typeof detail === 'object' ? detail as Record<string, unknown> : null
    }
  },
  setToken: () => {},
  clearToken: () => {},
}))

import { training } from '@/services/training'
import { indexService } from '@/services/index'

beforeEach(() => {
  vi.clearAllMocks()
})

describe('training service', () => {
  it('getStatus and listJobs call correct GET endpoints', async () => {
    mockGet.mockResolvedValue({ model_name: 'test', version: 'v1', status: 'idle', deployed_at: null })

    await training.getStatus()
    expect(mockGet).toHaveBeenCalledWith('/training/status')

    await training.listJobs()
    expect(mockGet).toHaveBeenCalledWith('/training/jobs')
  })

  it('triggerTraining and cancelJob call correct POST endpoints', async () => {
    mockPost.mockResolvedValue({ job_id: 'j1' })

    await training.triggerTraining('new data')
    expect(mockPost).toHaveBeenCalledWith('/training/trigger', { reason: 'new data' })

    await training.cancelJob('j1')
    expect(mockPost).toHaveBeenCalledWith('/training/jobs/j1/cancel')

    await training.deployModel('j2', true)
    expect(mockPost).toHaveBeenCalledWith('/training/jobs/j2/deploy', { force: true })

    await training.rollbackModel()
    expect(mockPost).toHaveBeenCalledWith('/training/rollback')
  })
})

describe('index service', () => {
  it('getIndexStatus and triggerReindex call correct endpoints', async () => {
    mockGet.mockResolvedValue({
      qdrant_index_status: 'current',
      changes_since_last: {},
      external_retraining_recommended: false,
    })
    mockPost.mockResolvedValue({ status: 'started' })

    await indexService.getIndexStatus()
    expect(mockGet).toHaveBeenCalledWith('/index/status')

    await indexService.triggerReindex('full_active')
    expect(mockPost).toHaveBeenCalledWith('/index/reindex', { scope: 'full_active' })

    await indexService.triggerReindex('changed')
    expect(mockPost).toHaveBeenCalledWith('/index/reindex', { scope: 'changed' })
  })
})

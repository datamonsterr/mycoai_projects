import { describe, it, expect, vi, beforeEach } from 'vitest'
import { feedbackService } from '@/services/feedback'
import { api } from '@/services/api-client'

vi.mock('@/services/api-client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
  ApiError: class extends Error {
    status: number
    detail: Record<string, unknown> | null
    constructor(status: number, detail: string | Record<string, unknown> | null) {
      super(typeof detail === 'string' ? detail : 'Request failed')
      this.status = status
      this.detail = typeof detail === 'object' ? detail as Record<string, unknown> : null
    }
  },
}))

describe('feedbackService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submit calls POST /feedback with feedback data', async () => {
    const data = { feedback_type: 'issue' as const, description: 'test' }
    ;(api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ id: '1' })
    await feedbackService.submit(data)
    expect(api.post).toHaveBeenCalledWith('/feedback', data)
  })

  it('listMy calls GET /feedback with default offset and limit', async () => {
    ;(api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 })
    await feedbackService.listMy()
    expect(api.get).toHaveBeenCalledWith('/feedback', { params: { offset: 0, limit: 50, status: undefined } })
  })

  it('listMy passes status filter when provided', async () => {
    ;(api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 })
    await feedbackService.listMy({ status: 'pending' })
    expect(api.get).toHaveBeenCalledWith('/feedback', { params: { offset: 0, limit: 50, status: 'pending' } })
  })

  it('inbox calls GET /feedback/inbox with defaults', async () => {
    ;(api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 })
    await feedbackService.inbox()
    expect(api.get).toHaveBeenCalledWith('/feedback/inbox', { params: { offset: 0, limit: 50, status: undefined } })
  })

  it('review calls PATCH /feedback/:id with update data', async () => {
    const data = { status: 'accepted' as const }
    ;(api.patch as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'abc' })
    await feedbackService.review('abc', data)
    expect(api.patch).toHaveBeenCalledWith('/feedback/abc', data)
  })

  it('batchReview calls POST /feedback/batch with ids and status', async () => {
    const data = { feedback_ids: ['1', '2'], status: 'accepted' as const }
    ;(api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ updated: 2 })
    await feedbackService.batchReview(data)
    expect(api.post).toHaveBeenCalledWith('/feedback/batch', data)
  })
})

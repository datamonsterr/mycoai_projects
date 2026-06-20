import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { startQuery, getJobStatus, getJobResults, querySync } from '@/services/retrieval'
import { ApiError } from '@/services/api-client'

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  vi.stubGlobal('localStorage', {
    getItem: vi.fn().mockReturnValue('test-token'),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  mockFetch.mockReset()
})

function mockResponse(body: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
  })
}

describe('startQuery', () => {
  it('POSTs to /retrieval/query and returns RetrievalJobResponse', async () => {
    const expected = { job_id: 'job-1', status: 'queued', estimated_seconds: 30 }
    mockResponse(expected)

    const result = await startQuery({ image_id: 'img-1', k: 5, aggregation: 'freq_strength', environment_strategy: 'same_media' })

    expect(result).toEqual(expected)
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/retrieval/query')
    expect(init.method).toBe('POST')
    expect(init.headers).toHaveProperty('Authorization', 'Bearer test-token')
  })

  it('throws ApiError on non-ok response', async () => {
    mockResponse({ detail: 'Image not found' }, 404)

    await expect(startQuery({ image_id: 'bad-id', k: 5, aggregation: 'freq_strength', environment_strategy: 'same_media' }))
      .rejects.toThrow(ApiError)
  })
})

describe('getJobStatus', () => {
  it('GETs /retrieval/jobs/:id and returns job status', async () => {
    const expected = { job_id: 'job-1', status: 'running', estimated_seconds: 15 }
    mockResponse(expected)

    const result = await getJobStatus('job-1')

    expect(result).toEqual(expected)
    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/retrieval/jobs/job-1')
  })
})

describe('getJobResults', () => {
  it('GETs /retrieval/jobs/:id/results and returns results', async () => {
    const expected = {
      job_id: 'job-1',
      status: 'completed',
      strain: 'T379',
      rankings: [
        { rank: 1, species: 'thymicola', score: 0.91, neighbors: [] },
      ],
    }
    mockResponse(expected)

    const result = await getJobResults('job-1')

    expect(result).toEqual(expected)
    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/retrieval/jobs/job-1/results')
  })
})

describe('querySync', () => {
  it('POSTs to /retrieval/query-sync and returns results', async () => {
    const expected = {
      job_id: 'sync-1',
      status: 'completed',
      strain: 'T379',
      rankings: [],
    }
    mockResponse(expected)

    const result = await querySync({ image_id: 'img-2', k: 3, aggregation: 'freq_strength', environment_strategy: 'same_media' })

    expect(result).toEqual(expected)
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/retrieval/query-sync')
    expect(init.method).toBe('POST')
  })
})

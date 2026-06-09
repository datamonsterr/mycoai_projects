import { describe, it, expect, vi, beforeEach } from 'vitest'
import { uploadImage, getImage, deleteImage } from '@/services/images'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

function mockResponse<T>(data: T, status = 200, contentType = 'application/json') {
  return {
    ok: true,
    status,
    headers: new Headers({ 'content-type': contentType }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  }
}

beforeEach(() => {
  mockFetch.mockReset()
})

describe('uploadImage', () => {
  it('sends correct FormData with strain and media', async () => {
    const file = new File(['test'], 'test.png', { type: 'image/png' })
    mockFetch.mockResolvedValueOnce(
      mockResponse({ image_id: 'img-1', strain: 'T379', media: 'MEA', status: 'processing', job_id: 'job-1' }),
    )

    const result = await uploadImage(file, 'T379', 'MEA', 10)

    expect(result.image_id).toBe('img-1')
    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/images/upload')
    expect(init.method).toBe('POST')
    const body = init.body as FormData
    expect(body.get('strain')).toBe('T379')
    expect(body.get('media')).toBe('MEA')
    expect(body.get('max_colonies')).toBe('10')
    expect(body.get('image')).toBeInstanceOf(File)
  })
})

describe('getImage', () => {
  it('returns image detail', async () => {
    const detail = {
      id: 'img-abc',
      strain: 'T123',
      media: 'PDA',
      status: 'ready',
      segments: [],
    }
    mockFetch.mockResolvedValueOnce(mockResponse(detail))

    const result = await getImage('img-abc')

    expect(result.id).toBe('img-abc')
    expect(result.strain).toBe('T123')
    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/images/img-abc')
  })
})

describe('deleteImage', () => {
  it('calls DELETE endpoint', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse(null, 204))

    await deleteImage('img-del')

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/images/img-del')
    expect(init.method).toBe('DELETE')
  })
})

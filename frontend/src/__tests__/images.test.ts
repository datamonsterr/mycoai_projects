import { describe, it, expect, vi, beforeEach } from 'vitest'
import { uploadImage, getImage, deleteImage, uploadBatchZip, listImages } from '@/services/images'
import { resolveImageUrl } from '@/lib/utils'

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
      image_id: 'img-abc',
      source_url: '/api/v1/images/img-abc/source',
      segments: [],
      segmentation_method: 'kmeans',
    }
    mockFetch.mockResolvedValueOnce(mockResponse(detail))

    const result = await getImage('img-abc')

    expect(result.image_id).toBe('img-abc')
    expect(result.source_url).toBe('/api/v1/images/img-abc/source')
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

describe('uploadBatchZip', () => {
  it('sends ZIP file as FormData with default options', async () => {
    const zipFile = new File(['fake-zip-content'], 'batch.zip', { type: 'application/zip' })
    mockFetch.mockResolvedValueOnce(
      mockResponse({
        status: 'completed',
        batch_name: 'batch',
        total: 3,
        successful: 3,
        failed: 0,
        results: [
          { image_id: 'img-1', strain: 'T379', media: 'MEA', species: 'thymicola', segments: 2, filename: 'images/T379/T379_MEA.jpg' },
        ],
        errors: [],
      }),
    )

    const result = await uploadBatchZip(zipFile)

    expect(result.status).toBe('completed')
    expect(result.successful).toBe(3)
    expect(result.total).toBe(3)
    expect(result.results[0].strain).toBe('T379')

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/images/batch-zip')
    expect(init.method).toBe('POST')
    const body = init.body as FormData
    expect(body.get('zipfile')).toBeInstanceOf(File)
  })

  it('sends custom options as FormData fields', async () => {
    const zipFile = new File(['fake-zip-content'], 'batch.zip', { type: 'application/zip' })
    mockFetch.mockResolvedValueOnce(
      mockResponse({
        status: 'completed',
        batch_name: 'batch',
        total: 0,
        successful: 0,
        failed: 0,
        results: [],
        errors: [],
      }),
    )

    await uploadBatchZip(zipFile, { defaultMedia: 'PDA', defaultSpecies: 'aspergillus', method: 'contour' })

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit]
    const body = init.body as FormData
    expect(body.get('default_media')).toBe('PDA')
    expect(body.get('default_species')).toBe('aspergillus')
    expect(body.get('method')).toBe('contour')
    expect(body.get('zipfile')).toBeInstanceOf(File)
  })

  it('rejects non-ZIP files', async () => {
    // This is a client-side concern, but backend should also reject
    // Test that the endpoint is called correctly even with non-zip (backend validates)
    const txtFile = new File(['not-a-zip'], 'test.txt', { type: 'text/plain' })
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ detail: 'Only .zip files are accepted' }),
      text: () => Promise.resolve(JSON.stringify({ detail: 'Only .zip files are accepted' })),
    })

    await expect(uploadBatchZip(txtFile)).rejects.toThrow('Only .zip files are accepted')

    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/images/batch-zip')
  })
})

// ── listImages tests ──────────────────────────────────────────────────────

describe('listImages', () => {
  it('fetches images list with default params', async () => {
    mockFetch.mockResolvedValueOnce(
      mockResponse({
        items: [
          {
            id: 'uuid-1',
            strain_name: 'T379',
            species_id: 'sp-1',
            species_name: 'thymicola',
            media_id: 'm-1',
            media_name: 'MEA',
            file_path: 'T379/MEA/source.jpg',
            source_url: '/api/v1/images/uuid-1/source',
            angle: 'ob',
            segments_count: 2,
            data_update_status: 'current',
            indexed_in_qdrant: true,
            is_archived: false,
            created_at: '2025-01-01T00:00:00Z',
          },
        ],
        total: 1,
      }),
    )

    const result = await listImages()

    expect(result.total).toBe(1)
    expect(result.items).toHaveLength(1)
    expect(result.items[0].strain_name).toBe('T379')
    expect(result.items[0].source_url).toBe('/api/v1/images/uuid-1/source')
    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/images?offset=0&limit=50')
  })

  it('fetches with species and media filters', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ items: [], total: 0 }))

    await listImages({
      species_id: ['sp-001', 'sp-002'],
      media_id: ['m-001'],
      search: 'T379',
      status: 'current',
    })

    const [url] = mockFetch.mock.calls[0] as [string]
    expect(url).toContain('species_id=sp-001')
    expect(url).toContain('species_id=sp-002')
    expect(url).toContain('media_id=m-001')
    expect(url).toContain('search=T379')
    expect(url).toContain('status=current')
  })

  it('returns empty items when no results', async () => {
    mockFetch.mockResolvedValueOnce(mockResponse({ items: [], total: 0 }))

    const result = await listImages({ search: 'nonexistent' })

    expect(result.total).toBe(0)
    expect(result.items).toEqual([])
  })
})

describe('resolveImageUrl', () => {
  it('returns http URLs unchanged', () => {
    expect(resolveImageUrl('http://minio:9000/bucket/path/img.jpg'))
      .toBe('http://minio:9000/bucket/path/img.jpg')
  })

  it('returns https URLs unchanged', () => {
    expect(resolveImageUrl('https://cdn.example.com/image.png'))
      .toBe('https://cdn.example.com/image.png')
  })

  it('returns absolute paths unchanged', () => {
    expect(resolveImageUrl('/sample/T379/image.jpg'))
      .toBe('/sample/T379/image.jpg')
  })

  it('prepends /static/ to relative paths', () => {
    expect(resolveImageUrl('strain/media/id/source.jpg'))
      .toBe('/static/strain/media/id/source.jpg')
  })
})

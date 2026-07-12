import { describe, it, expect, vi, beforeEach } from 'vitest'
import { species } from '@/services/species'
import { media } from '@/services/media'
import { patchImageSegments, reindexImage, reindexStrainImages } from '@/services/images'

beforeEach(() => {
  vi.restoreAllMocks()
})

function mockFetch(response: unknown, status = 200, headers?: Record<string, string>) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json', ...headers }),
    json: () => Promise.resolve(response),
    text: () => Promise.resolve(JSON.stringify(response)),
  } as Response)
}

describe('species service', () => {
  it('list returns items and total', async () => {
    const data = { items: [{ id: '1', name: 'Test', description: null, is_archived: false, created_at: '2025-01-01', updated_at: '2025-01-01' }], total: 1 }
    mockFetch(data)

    const result = await species.list()
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species?is_archived=false&offset=0&limit=50'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('list passes archived param', async () => {
    mockFetch({ items: [], total: 0 })
    await species.list(true, 10, 25)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('is_archived=true&offset=10&limit=25'),
      expect.anything(),
    )
  })

  it('create posts species data', async () => {
    const returned = { id: '2', name: 'New', description: '', is_archived: false, created_at: '2025-01-01', updated_at: '2025-01-01' }
    mockFetch(returned, 201)

    const result = await species.create({ name: 'New', description: '' })
    expect(result).toEqual(returned)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('get fetches by id', async () => {
    const item = { id: 'abc', name: 'Fetched', description: null, is_archived: false, created_at: '2025-01-01', updated_at: '2025-01-01' }
    mockFetch(item)
    const result = await species.get('abc')
    expect(result).toEqual(item)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species/abc'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('update patches species', async () => {
    const item = { id: 'abc', name: 'Updated', description: null, is_archived: false, created_at: '2025-01-01', updated_at: '2025-06-01' }
    mockFetch(item)
    const result = await species.update('abc', { name: 'Updated' })
    expect(result).toEqual(item)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species/abc'),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('archive sends delete', async () => {
    mockFetch(undefined, 204, { 'content-type': 'text/plain' })
    const result = await species.archive('abc')
    expect(result).toBeUndefined()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species/abc'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('getDeleteImpact fetches archive impact', async () => {
    const impact = { strain_count: 2, segment_count: 8, warning_message: 'Archiving this species affects 2 strain(s) and 8 segment(s).' }
    mockFetch(impact)
    const result = await species.getDeleteImpact('sp1')
    expect(result).toEqual(impact)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/species/sp1/delete-impact'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('throws on error status', async () => {
    mockFetch({ detail: 'Conflict' }, 409)
    await expect(species.create({ name: 'dup' })).rejects.toThrow('Conflict')
  })
})

describe('media service', () => {
  it('list returns items and total', async () => {
    const data = { items: [{ id: '1', name: 'MEA', description: null, is_archived: false, created_at: '2025-01-01', updated_at: '2025-01-01' }], total: 1 }
    mockFetch(data)

    const result = await media.list()
    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/media?is_archived=false&offset=0&limit=50'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('create posts media data', async () => {
    const returned = { id: '2', name: 'PDA', description: '', is_archived: false, created_at: '2025-01-01', updated_at: '2025-01-01' }
    mockFetch(returned, 201)

    const result = await media.create({ name: 'PDA' })
    expect(result).toEqual(returned)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/media'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('update patches media', async () => {
    const item = { id: 'abc', name: 'Updated', description: null, is_archived: false, created_at: '2025-01-01', updated_at: '2025-06-01' }
    mockFetch(item)
    const result = await media.update('abc', { name: 'Updated' })
    expect(result).toEqual(item)
  })

  it('archive sends delete', async () => {
    mockFetch(undefined, 204, { 'content-type': 'text/plain' })
    await media.archive('abc')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/media/abc'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('getDeleteImpact fetches archive impact', async () => {
    const impact = { strain_count: 3, segment_count: 12, warning_message: 'Archiving this media affects 3 strain(s) and 12 segment(s).' }
    mockFetch(impact)
    const result = await media.getDeleteImpact('media-1')
    expect(result).toEqual(impact)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/media/media-1/delete-impact'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('throws on error status', async () => {
    mockFetch({ detail: 'Conflict' }, 409)
    await expect(media.create({ name: 'dup' })).rejects.toThrow('Conflict')
  })
})

describe('images service', () => {
  it('patches image segments', async () => {
    const data = {
      image_id: 'img-1',
      source_url: '/img-1.jpg',
      segmentation_method: 'manual',
      segments: [{ segment_id: 'seg-1', segment_index: 0, bbox: { x: 1, y: 2, w: 3, h: 4 }, crop_url: '/seg-1.jpg', pipeline_url: '/pipe-1.jpg' }],
    }
    mockFetch(data)

    const result = await patchImageSegments('img-1', {
      segments: [{ segment_index: 0, bbox: { x: 1, y: 2, w: 3, h: 4 } }],
      deleted_segments: [1],
    })

    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/images/img-1/segments'),
      expect.objectContaining({ method: 'PATCH' }),
    )
  })

  it('posts image reindex', async () => {
    const data = { image_id: 'img-1', indexed_segments: 2 }
    mockFetch(data)

    const result = await reindexImage('img-1')

    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/images/img-1/reindex'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('posts strain reindex', async () => {
    const data = { strain_id: 'strain-1', images: 3, indexed_segments: 5 }
    mockFetch(data)

    const result = await reindexStrainImages('strain-1')

    expect(result).toEqual(data)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/images/strains/strain-1/reindex'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})

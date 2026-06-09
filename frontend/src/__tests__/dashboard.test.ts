import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getStats, getSpeciesDistribution, getMediaDistribution } from '@/services/dashboard'

const mockGet = vi.fn()
vi.mock('@/services/api-client', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('getStats', () => {
  it('returns dashboard stats from the API', async () => {
    const stats = { total_images: 42, total_strains: 10, total_species: 5, total_media: 3 }
    mockGet.mockResolvedValueOnce(stats)

    const result = await getStats()

    expect(mockGet).toHaveBeenCalledWith('/dashboard/stats')
    expect(result).toEqual(stats)
  })
})

describe('getSpeciesDistribution', () => {
  it('returns species distribution from the API', async () => {
    const distribution = [
      { species_name: 'Penicillium', image_count: 15 },
      { species_name: 'Aspergillus', image_count: 8 },
    ]
    mockGet.mockResolvedValueOnce(distribution)

    const result = await getSpeciesDistribution()

    expect(mockGet).toHaveBeenCalledWith('/dashboard/charts/species-distribution')
    expect(result).toHaveLength(2)
    expect(result[0].species_name).toBe('Penicillium')
  })
})

describe('getMediaDistribution', () => {
  it('returns media distribution from the API', async () => {
    const distribution = [
      { media_name: 'MEA', image_count: 20 },
      { media_name: 'CYA', image_count: 12 },
    ]
    mockGet.mockResolvedValueOnce(distribution)

    const result = await getMediaDistribution()

    expect(mockGet).toHaveBeenCalledWith('/dashboard/charts/media-distribution')
    expect(result).toHaveLength(2)
    expect(result[0].media_name).toBe('MEA')
  })
})

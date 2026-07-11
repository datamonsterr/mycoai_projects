import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DashboardPage from '@/pages/Dashboard'
import { getStats, getSpeciesDistribution, getMediaDistribution } from '@/services/dashboard'

const mockGet = vi.fn()
const dashboardHooks = vi.hoisted(() => ({
  useDashboardStats: vi.fn(),
  useSpeciesDistribution: vi.fn(),
  useMediaDistribution: vi.fn(),
  useStrainDistribution: vi.fn(),
  useQdrantStatus: vi.fn(),
}))

vi.mock('@/services/api-client', () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}))

vi.mock('@/hooks/use-dashboard', () => dashboardHooks)
vi.mock('@/lib/use-auth', () => ({
  useAuth: () => ({ user: { role: 'owner' } }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  dashboardHooks.useDashboardStats.mockReturnValue({ data: { total_images: 42, total_strains: 10, total_species: 5, total_media: 3 }, isLoading: false })
  dashboardHooks.useQdrantStatus.mockReturnValue({ data: { qdrant_index_status: 'current', changes_since_last: {}, external_retraining_recommended: false }, isLoading: false })
  dashboardHooks.useSpeciesDistribution.mockReturnValue({ data: [], isLoading: false })
  dashboardHooks.useMediaDistribution.mockReturnValue({ data: [], isLoading: false })
  dashboardHooks.useStrainDistribution.mockReturnValue({ data: [], isLoading: false })
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

describe('DashboardPage', () => {
  it('does not emit duplicate key warnings for duplicate distribution names', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    dashboardHooks.useSpeciesDistribution.mockReturnValue({
      data: [
        { species_name: 'Duplicate', image_count: 5 },
        { species_name: 'Duplicate', image_count: 3 },
      ],
      isLoading: false,
    })

    render(<DashboardPage />)

    const duplicateKeyWarnings = consoleError.mock.calls.filter(([message]) =>
      typeof message === 'string' && /Encountered two children with the same key/i.test(message),
    )

    expect(duplicateKeyWarnings).toHaveLength(0)
    consoleError.mockRestore()
  })
})

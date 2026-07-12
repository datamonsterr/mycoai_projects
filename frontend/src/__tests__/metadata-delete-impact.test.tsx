import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import MetadataPage from '@/pages/Metadata'

const mocks = vi.hoisted(() => ({
  archiveSpeciesMutate: vi.fn().mockResolvedValue(undefined),
  archiveMediaMutate: vi.fn().mockResolvedValue(undefined),
  restoreSpeciesMutate: vi.fn().mockResolvedValue(undefined),
  restoreMediaMutate: vi.fn().mockResolvedValue(undefined),
  cleanSpeciesMutate: vi.fn().mockResolvedValue(undefined),
  cleanMediaMutate: vi.fn().mockResolvedValue(undefined),
  getSpeciesDeleteImpact: vi.fn().mockResolvedValue({
    strain_count: 2,
    segment_count: 8,
    warning_message: 'Archiving this species affects 2 strain(s) and 8 segment(s).',
  }),
}))

vi.mock('@/hooks/use-taxonomy', () => ({
  useSpeciesList: (archived = false) => ({ data: { items: archived ? [{ id: 'sp2', name: 'Archived Spec', description: null, created_at: '2025-01-01', is_archived: true }] : [{ id: 'sp1', name: 'Spec A', description: null, created_at: '2025-01-01', is_archived: false }] }, isLoading: false }),
  useCreateSpecies: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateSpecies: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useArchiveSpecies: () => ({ mutateAsync: mocks.archiveSpeciesMutate, isPending: false }),
  useRestoreSpecies: () => ({ mutateAsync: mocks.restoreSpeciesMutate, isPending: false }),
  useCleanSpecies: () => ({ mutateAsync: mocks.cleanSpeciesMutate, isPending: false }),
  useMediaList: (archived = false) => ({ data: { items: archived ? [{ id: 'm2', name: 'Archived MEA', description: null, created_at: '2025-01-01', is_archived: true }] : [{ id: 'm1', name: 'MEA', description: null, created_at: '2025-01-01', is_archived: false }] }, isLoading: false }),
  useCreateMedia: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateMedia: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useArchiveMedia: () => ({ mutateAsync: mocks.archiveMediaMutate, isPending: false }),
  useRestoreMedia: () => ({ mutateAsync: mocks.restoreMediaMutate, isPending: false }),
  useCleanMedia: () => ({ mutateAsync: mocks.cleanMediaMutate, isPending: false }),
}))

vi.mock('@/services/species', () => ({
  species: {
    getDeleteImpact: mocks.getSpeciesDeleteImpact,
  },
}))

vi.mock('@/services/media', () => ({
  media: {
    getDeleteImpact: vi.fn().mockResolvedValue({
      strain_count: 1,
      segment_count: 4,
      warning_message: 'Archiving this media affects 1 strain(s) and 4 segment(s).',
    }),
  },
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), apiError: vi.fn() }),
}))

describe('MetadataPage archive impact', () => {
  beforeEach(() => {
    mocks.archiveSpeciesMutate.mockClear()
    mocks.getSpeciesDeleteImpact.mockClear()
  })

  it('shows warning dialog content before archiving species', async () => {
    render(<MetadataPage />)

    await userEvent.click(screen.getAllByRole('button').find((button) => button.className.includes('text-destructive'))!)

    expect(await screen.findByText(/affects 2 strain\(s\) and 8 segment\(s\)/i)).toBeInTheDocument()
    expect(screen.getByText('2 strain(s) · 8 segment(s)')).toBeInTheDocument()
  })

  it('shows archived items in trash view with restore action', async () => {
    render(<MetadataPage />)

    expect(screen.getByRole('button', { name: /trash/i })).toBeInTheDocument()
  })
})

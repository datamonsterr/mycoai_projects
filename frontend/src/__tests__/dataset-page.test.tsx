import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DatasetPage from '@/pages/Dataset'

const mockUseAuth = vi.fn()
const mockUseImageGroups = vi.fn()

vi.mock('@/lib/use-auth', () => ({ useAuth: () => mockUseAuth() }))
vi.mock('@/hooks/use-taxonomy', () => ({
  useSpeciesList: () => ({ data: { items: [] } }),
  useMediaList: () => ({ data: { items: [] } }),
}))
const groupedResponse = {
  isLoading: false,
  data: {
    total: 1,
    items: [
      {
        strain_id: 'strain-1',
        strain_name: 'DTO 148-F1',
        species_id: 'species-1',
        species_name: 'Penicillium chrysogenum',
        media_names: ['CYA', 'MEA'],
        image_count: 2,
        images: [
          {
            id: 'image-1',
            source_url: '/image-1.jpg',
            data_update_status: 'current',
            indexed_in_qdrant: true,
            is_archived: false,
            created_at: '2026-07-01T00:00:00Z',
          },
          {
            id: 'image-2',
            source_url: '/image-2.jpg',
            data_update_status: 'updated_requires_reindex',
            indexed_in_qdrant: false,
            is_archived: false,
            created_at: '2026-07-02T00:00:00Z',
          },
        ],
      },
    ],
  },
}

vi.mock('@/hooks/use-images', () => ({
  useImageGroups: (params: unknown) => mockUseImageGroups(params),
}))

describe('DatasetPage strain groups', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: { role: 'owner' } })
    mockUseImageGroups.mockReturnValue(groupedResponse)
  })

  it('renders strain rows without plate or image detail identifiers', () => {
    render(<DatasetPage />)

    expect(screen.getByText('DTO 148-F1')).toBeInTheDocument()
    expect(screen.getByText('CYA, MEA')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Images' })).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Plate' })).not.toBeInTheDocument()
    expect(screen.queryByText('Image ID')).not.toBeInTheDocument()
    expect(screen.queryByText('Segments')).not.toBeInTheDocument()
  })

  it('expands a strain into child image rows without exposing image ids', () => {
    render(<DatasetPage />)

    fireEvent.click(screen.getByTitle('Expand images'))

    expect(screen.getAllByRole('img')).toHaveLength(2)
    expect(screen.getByText('Indexed')).toBeInTheDocument()
    expect(screen.getByText('Needs Reindex')).toBeInTheDocument()
    const editButtons = screen.getAllByRole('button', { name: 'Edit image' })
    expect(editButtons).toHaveLength(2)
    fireEvent.click(editButtons[0])
    expect(screen.queryByText('image-1')).not.toBeInTheDocument()
  })

  it('includes archived images when the archived status filter is selected', () => {
    render(<DatasetPage />)

    fireEvent.click(screen.getByRole('button', { name: /filters/i }))
    fireEvent.click(screen.getByRole('radio', { name: 'Archived' }))

    expect(mockUseImageGroups).toHaveBeenLastCalledWith(expect.objectContaining({
      status: 'archived',
      include_archived: true,
    }))
  })
})

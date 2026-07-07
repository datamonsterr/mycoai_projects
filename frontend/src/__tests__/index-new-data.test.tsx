import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import IndexNewDataPage from '@/pages/IndexNewData'

vi.mock('@/hooks/use-taxonomy', () => ({
  useSpeciesList: () => ({ data: { items: [{ id: 'sp1', name: 'thymicola', is_archived: false }] } }),
  useMediaList: () => ({ data: { items: [{ id: 'm1', name: 'MEA', is_archived: false }] } }),
  useCreateSpecies: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), apiError: vi.fn() }),
}))

vi.mock('@/services/images', () => ({
  uploadBatchZip: vi.fn().mockResolvedValue({
    status: 'completed',
    batch_id: 'batch-1',
    batch_name: 'test',
    total: 2,
    successful: 2,
    failed: 0,
    results: [
      { image_id: 'img1', strain: 'T1', species: 'thymicola', media: 'MEA', segments: 1, filename: 'a.jpg', source_url: '/a.jpg', status: 'segmented' },
      { image_id: 'img2', strain: 'T2', species: 'thymicola', media: 'MEA', segments: 1, filename: 'b.jpg', source_url: '/b.jpg', status: 'uploaded' },
    ],
    errors: [],
    progress: {
      batch_id: 'batch-1',
      status: 'completed',
      batch_name: 'test',
      upload: { completed: 2, total: 2, percent: 100 },
      segmentation: { completed: 1, total: 2, percent: 50 },
      feature_extraction: { completed: 0, total: 2, percent: 0 },
      strains: [],
      images: [],
    },
  }),
  confirmBatchStrain: vi.fn().mockResolvedValue({
    batch_id: 'batch-1',
    status: 'completed',
    batch_name: 'test',
    upload: { completed: 2, total: 2, percent: 100 },
    segmentation: { completed: 2, total: 2, percent: 100 },
    feature_extraction: { completed: 1, total: 2, percent: 50 },
    strains: [],
    images: [],
  }),
  listSegments: vi.fn().mockResolvedValue([]),
  autoSegment: vi.fn().mockResolvedValue({ segmentation_method: 'yolo', segments: [] }),
}))

describe('IndexNewDataPage', () => {
  it('shows compact batch guidance and AGENTS modal', async () => {
    render(<IndexNewDataPage />)

    expect(screen.getByRole('button', { name: 'Batch ZIP' })).toBeInTheDocument()
    expect(screen.getByText('Batch upload for indexing')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /download agents/i })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'AGENTS.md' }))

    expect(screen.getByText('Instructions included in the template ZIP for your local agent.')).toBeInTheDocument()
    expect(screen.getAllByText(/metadata.json/).length).toBeGreaterThan(0)
  })

  it('switches to single strain tab and keeps Segment Uploaded as the only segmentation action', async () => {
    render(<IndexNewDataPage />)

    await userEvent.click(screen.getByRole('button', { name: 'Single strain' }))

    expect(screen.getByRole('button', { name: 'Load sample strains' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Segment Uploaded' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: /auto segment/i })).not.toBeInTheDocument()
  })

  it('shows batch upload and segmentation progress with dimmed pending rows', async () => {
    render(<IndexNewDataPage />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    expect(await screen.findByText(/Upload 2\/2 \(100%\)/)).toBeInTheDocument()
    expect(screen.getByText(/Segmentation 1\/2 \(50%\)/)).toBeInTheDocument()
    expect(screen.getByText('b.jpg').closest('tr')).toHaveClass('opacity-50')
  })

  it('shows per-strain confirmation progress and advances review flow', async () => {
    render(<IndexNewDataPage />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['zip'], 'batch.zip', { type: 'application/zip' }))
    await userEvent.click(await screen.findByRole('button', { name: /Segment Uploaded/ }))

    expect(await screen.findByText(/Segmentation 0\/2/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Confirm strain 0\/2/ })).toBeInTheDocument()
  })
})

import { render, screen, waitFor } from '@testing-library/react'
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

const imagesModule = vi.hoisted(() => ({
  uploadBatchZip: vi.fn().mockResolvedValue({
    status: 'processing',
    batch_id: 'batch-1',
    batch_name: 'test',
    total: 2,
    successful: 0,
    failed: 0,
    results: [],
    errors: [],
    progress: {
      batch_id: 'batch-1',
      status: 'processing',
      batch_name: 'test',
      upload: { completed: 2, total: 2, percent: 100 },
      segmentation: { completed: 1, total: 2, percent: 50 },
      feature_extraction: { completed: 0, total: 2, percent: 0 },
      strains: [],
      images: [
        { filename: 'images/T1/MEA/a.jpg', strain: 'T1', species: 'thymicola', media: 'MEA', status: 'segmented', image_id: 'img1', segments: 1, source_url: '/a.jpg', error: null },
        { filename: 'images/T2/CYA/b.jpg', strain: 'T2', species: 'thymicola', media: 'CYA', status: 'uploaded', image_id: 'img2', segments: 0, source_url: '/b.jpg', error: null },
      ],
    },
  }),
  getBatchProgress: vi.fn().mockResolvedValue({
    batch_id: 'batch-1',
    status: 'completed',
    batch_name: 'test',
    upload: { completed: 2, total: 2, percent: 100 },
    segmentation: { completed: 2, total: 2, percent: 100 },
    feature_extraction: { completed: 0, total: 2, percent: 0 },
    strains: [],
    images: [
      { filename: 'images/T1/MEA/a.jpg', strain: 'T1', species: 'thymicola', media: 'MEA', status: 'segmented', image_id: 'img1', segments: 1, source_url: '/a.jpg', error: null },
      { filename: 'images/T2/CYA/b.jpg', strain: 'T2', species: 'thymicola', media: 'CYA', status: 'segmented', image_id: 'img2', segments: 1, source_url: '/b.jpg', error: null },
    ],
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

vi.mock('@/services/images', () => imagesModule)

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
    expect(screen.getByText(/2 strain\(s\) · 2 image\(s\)/i)).toBeInTheDocument()
  })

  it('shows per-strain confirmation flow without crashing after segment step', async () => {
    render(<IndexNewDataPage />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['zip'], 'batch.zip', { type: 'application/zip' }))
    const segmentButton = await screen.findByRole('button', { name: /Segment Uploaded/ })
    expect(segmentButton).toBeInTheDocument()
  })

  it('polls batch progress after zip upload', async () => {
    render(<IndexNewDataPage />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    await waitFor(() => expect(imagesModule.getBatchProgress.mock.calls.length).toBeGreaterThan(0))
  })

  it('keeps media from nested zip folder instead of defaulting to MEA', async () => {
    render(<IndexNewDataPage />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(input, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    expect(screen.getByText(/2 strain\(s\) · 2 image\(s\)/i)).toBeInTheDocument()
    expect(screen.getByText(/Upload 2\/2 \(100%\)/)).toBeInTheDocument()
  })
})

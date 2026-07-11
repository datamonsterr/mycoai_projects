import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RetrievePage from '@/pages/Retrieve'

const mockStartMutation = vi.fn()
const mockToast = { success: vi.fn(), error: vi.fn(), apiError: vi.fn(), info: vi.fn() }
const imagesModule = vi.hoisted(() => ({
  uploadImage: vi.fn(),
  uploadBatchZip: vi.fn(),
  autoSegment: vi.fn(),
  getBatchProgress: vi.fn(),
  patchImageSegments: vi.fn(),
  reindexImage: vi.fn(),
  reindexStrainImages: vi.fn(),
}))

let mockJobStatus: { data?: { status: string; estimated_seconds?: number }; isLoading?: boolean } = {}
let mockJobResults: { data?: { rankings: Array<{ rank: number; species: string; score: number; neighbors: [] }>; queried_images: Array<{ image_id: string; image_url: string; media: string; segment_image_urls: string[]; neighbors: [] }>; threshold?: null } } = {
  data: { rankings: [], queried_images: [], threshold: null },
}
const mockUseAuth = vi.fn(() => ({ user: { role: 'owner' } }))

vi.mock('@/hooks/use-toast', () => ({ useToast: () => mockToast }))
vi.mock('@/lib/use-auth', () => ({ useAuth: () => mockUseAuth() }))
vi.mock('@/lib/template', () => ({
  downloadTemplate: vi.fn(),
  downloadAgentsMd: vi.fn(),
  downloadTemplateZip: vi.fn(),
  INDEX_TEMPLATE_CSV: 'strain,media,file',
}))
vi.mock('@/services/images', () => imagesModule)
vi.mock('@/lib/mock-data', () => ({
  mediaList: [{ media_id: 'm1', name: 'MEA', is_archived: false }],
}))
vi.mock('@/lib/sample-assets', () => ({
  sampleStrains: [
    {
      species: 'spec-a',
      strain: 'strain-a',
      images: [
        {
          id: 'img-a',
          fileName: 'a.jpg',
          media: 'MEA',
          original: '/a.jpg',
          segments: [{ url: '/seg-a.jpg', bbox: { x: 1, y: 2, w: 30, h: 40 } }],
        },
      ],
    },
    {
      species: 'spec-b',
      strain: 'strain-b',
      images: [
        {
          id: 'img-b',
          fileName: 'b.jpg',
          media: 'MEA',
          original: '/b.jpg',
          segments: [{ url: '/seg-b.jpg', bbox: { x: 3, y: 4, w: 30, h: 40 } }],
        },
      ],
    },
  ],
}))
vi.mock('@/hooks/use-retrieval', () => ({
  useStartRetrieval: () => ({ isPending: false, isError: false, mutate: mockStartMutation }),
  useJobStatus: () => mockJobStatus,
  useJobResults: () => mockJobResults,
}))

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <RetrievePage />
    </QueryClientProvider>,
  )
}

describe('RetrievePage', () => {
  beforeEach(() => {
    mockUseAuth.mockReset()
    mockUseAuth.mockReturnValue({ user: { role: 'user' } })
    mockStartMutation.mockReset()
    mockToast.success.mockReset()
    mockToast.error.mockReset()
    mockToast.apiError.mockReset()
    mockToast.info.mockReset()
    mockUseAuth.mockReset()
    mockUseAuth.mockReturnValue({ user: { role: 'owner' } })
    imagesModule.uploadImage.mockReset()
    imagesModule.uploadBatchZip.mockReset()
    imagesModule.autoSegment.mockReset()
    imagesModule.getBatchProgress.mockReset()
    imagesModule.patchImageSegments.mockReset()
    imagesModule.reindexImage.mockReset()
    imagesModule.reindexStrainImages.mockReset()
    imagesModule.uploadImage
      .mockResolvedValueOnce({ image_id: 'img-a', source_url: '/uploaded-a.jpg' })
      .mockResolvedValueOnce({ image_id: 'img-b', source_url: '/uploaded-b.jpg' })
      .mockResolvedValue({ image_id: 'img-a', source_url: '/uploaded-a.jpg' })
    imagesModule.uploadBatchZip.mockResolvedValue({
      status: 'processing',
      batch_id: 'batch-1',
      batch_name: 'batch',
      total: 2,
      successful: 1,
      failed: 1,
      results: [
        { image_id: 'img-a', strain: 'strain-a', species: 'spec-a', media: 'MEA', segments: 1, filename: 'strain-a/a.jpg', source_url: '/uploaded-a.jpg', status: 'segmented' },
      ],
      errors: [{ file: 'strain-b/b.jpg', error: 'segment failed' }],
      progress: {
        batch_id: 'batch-1',
        status: 'processing',
        batch_name: 'batch',
        upload: { completed: 2, total: 2, percent: 100 },
        segmentation: { completed: 1, total: 2, percent: 50 },
        feature_extraction: { completed: 0, total: 2, percent: 0 },
        strains: [],
        images: [
          { filename: 'strain-a/a.jpg', strain: 'strain-a', media: 'MEA', species: 'spec-a', status: 'segmented', image_id: 'img-a', segments: 1, source_url: '/uploaded-a.jpg', error: null },
          { filename: 'strain-b/b.jpg', strain: 'strain-b', media: 'MEA', species: 'spec-b', status: 'failed', image_id: null, segments: 0, source_url: null, error: 'segment failed' },
        ],
      },
    })
    imagesModule.getBatchProgress.mockResolvedValue({
      batch_id: 'batch-1',
      status: 'completed',
      batch_name: 'batch',
      upload: { completed: 2, total: 2, percent: 100 },
      segmentation: { completed: 1, total: 2, percent: 50 },
      feature_extraction: { completed: 0, total: 2, percent: 0 },
      strains: [],
      images: [
        { filename: 'strain-a/a.jpg', strain: 'strain-a', media: 'MEA', species: 'spec-a', status: 'segmented', image_id: 'img-a', segments: 1, source_url: '/uploaded-a.jpg', error: null },
        { filename: 'strain-b/b.jpg', strain: 'strain-b', media: 'MEA', species: 'spec-b', status: 'failed', image_id: null, segments: 0, source_url: null, error: 'segment failed' },
      ],
    })
    imagesModule.autoSegment.mockResolvedValue({
      image_id: 'img-a',
      source_url: '/uploaded-a.jpg',
      segmentation_method: 'yolo',
      segments: [{ segment_id: 'seg-1', segment_index: 0, bbox: { x: 1, y: 2, w: 30, h: 40 }, crop_url: '/seg-a.jpg', pipeline_url: '/pipe-a.jpg' }],
    })
    imagesModule.patchImageSegments.mockResolvedValue({
      image_id: 'img-a',
      source_url: '/uploaded-a.jpg',
      segmentation_method: 'manual',
      segments: [{ segment_id: 'seg-1', segment_index: 0, bbox: { x: 1, y: 2, w: 30, h: 40 }, crop_url: '/seg-a.jpg', pipeline_url: '/pipe-a.jpg' }],
    })
    imagesModule.reindexImage.mockResolvedValue({ image_id: 'img-a', indexed_segments: 1 })
    imagesModule.reindexStrainImages.mockResolvedValue({ strain_id: 'strain-a', images: 1, indexed_segments: 1 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ blob: () => Promise.resolve(new Blob(['img'], { type: 'image/jpeg' })) }))
    mockJobStatus = {}
    mockJobResults = {
      data: {
        rankings: [{ rank: 1, species: 'spec-a', score: 0.9, neighbors: [] }],
        queried_images: [
          { image_id: 'img-a', image_url: '/a.jpg', media: 'MEA', segment_image_urls: ['/seg-a.jpg'], neighbors: [] },
          { image_id: 'img-b', image_url: '/b.jpg', media: 'MEA', segment_image_urls: ['/seg-b.jpg'], neighbors: [] },
        ],
        threshold: null,
      },
    }
  })

  it('submits all batch strain image ids, not only first strain', async () => {
    mockStartMutation.mockImplementation((_payload, options) => {
      options?.onSuccess?.({ job_id: 'job-1', status: 'processing', estimated_seconds: 5 })
    })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /Batch processing/i }))
    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalledTimes(2))
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))
    await userEvent.click(screen.getByRole('button', { name: /confirm image/i }))
    await userEvent.click(screen.getByRole('button', { name: /^Run Retrieval/i }))

    expect(mockStartMutation).toHaveBeenCalledTimes(1)
    const [payload] = mockStartMutation.mock.calls[0] as [{ image_id: string; image_ids: string[]; k: number; aggregation: string; media_strategy: string }]
    expect(payload.image_id).toBe('img-a')
    expect(payload.image_ids).toEqual(['img-a', 'img-b'])
  })

  it('applies retrieval config explicitly from results screen', async () => {
    mockJobStatus = { data: { status: 'completed', estimated_seconds: 0 }, isLoading: false }
    mockStartMutation.mockImplementation((_payload, options) => {
      options?.onSuccess?.({ job_id: 'job-2', status: 'processing', estimated_seconds: 5 })
    })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))
    await userEvent.click(screen.getByRole('button', { name: /confirm image/i }))
    await userEvent.click(screen.getByRole('button', { name: /^Run Retrieval/i }))
    await waitFor(() => screen.getByRole('slider'))

    fireEvent.change(screen.getByRole('slider'), { target: { value: '7' } })
    await userEvent.click(screen.getByRole('button', { name: /apply retrieval config/i }))

    await waitFor(() => expect(mockStartMutation).toHaveBeenCalledTimes(2))
    const [payload] = mockStartMutation.mock.calls[1] as [{ k: number; aggregation: string }]
    expect(payload.k).toBe(7)
    expect(payload.aggregation).toBe('freq_strength')
  })

  it('shows batch setup steps like index new data', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    expect(screen.getByText('Batch Upload (ZIP)')).toBeInTheDocument()
    expect(screen.getByText(/1\. Download template/i)).toBeInTheDocument()
    expect(screen.getByText(/2\. Run local agent/i)).toBeInTheDocument()
    expect(screen.getByText(/3\. Upload ZIP/i)).toBeInTheDocument()
  })

  it('shows batch per-image statuses and toasts failed zip rows', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    const zipInput = document.querySelector('input[type="file"][accept=".zip"]') as HTMLInputElement
    await userEvent.upload(zipInput, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    expect(await screen.findByText(/1 successful, 1 failed/i)).toBeInTheDocument()
    expect(screen.getByText('strain-a/a.jpg')).toBeInTheDocument()
    expect(screen.getByText('strain-b/b.jpg')).toBeInTheDocument()
    expect(screen.getByText('failed')).toBeInTheDocument()
    await waitFor(() => expect(imagesModule.getBatchProgress).toHaveBeenCalledWith('batch-1'))
    expect(mockToast.error).toHaveBeenCalled()
  })

  it('keeps full uploaded images grouped by strain with metadata visible after batch zip upload', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    const zipInput = document.querySelector('input[type="file"][accept=".zip"]') as HTMLInputElement
    await userEvent.upload(zipInput, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    const strainTab = await screen.findByRole('button', { name: /strain-a/i })
    expect(strainTab).toBeInTheDocument()
    expect(screen.getByDisplayValue('strain-a/a.jpg')).toBeInTheDocument()
    expect(screen.getAllByText('Media').length).toBeGreaterThan(0)
    expect(screen.getByText('Max')).toBeInTheDocument()
  })

  it('does not emit duplicate key warnings when batch progress and grouped cards reuse filenames', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    const zipInput = document.querySelector('input[type="file"][accept=".zip"]') as HTMLInputElement
    await userEvent.upload(zipInput, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    await screen.findByRole('button', { name: /strain-a/i })
    expect(consoleError).not.toHaveBeenCalledWith(expect.stringMatching(/Encountered two children with the same key/i))
    consoleError.mockRestore()
  })

  it('does not show stale no-valid-images toast when upload has valid batch results', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    const zipInput = document.querySelector('input[type="file"][accept=".zip"]') as HTMLInputElement
    await userEvent.upload(zipInput, new File(['zip'], 'batch.zip', { type: 'application/zip' }))

    await screen.findByText(/1 successful, 1 failed/i)
    expect(mockToast.error).not.toHaveBeenCalledWith(expect.stringMatching(/No valid images found/i))
  })

  it('shows compact retrieve mode tabs without redundant sample switcher buttons', () => {
    renderPage()

    expect(screen.getByRole('button', { name: /^Single Strain$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Batch processing$/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Load Single Sample/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Load Batch Sample/i })).not.toBeInTheDocument()
  })

  it('keeps add image visible during async single uploads and does not auto-advance past segmentation', async () => {
    let resolveFirstUpload: ((value: { image_id: string; source_url: string }) => void) | undefined
    let resolveSecondUpload: ((value: { image_id: string; source_url: string }) => void) | undefined

    imagesModule.uploadImage
      .mockReset()
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveFirstUpload = resolve as typeof resolveFirstUpload
      }))
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveSecondUpload = resolve as typeof resolveSecondUpload
      }))
    imagesModule.autoSegment.mockResolvedValue({
      image_id: 'img-a',
      source_url: '/uploaded-a.jpg',
      segmentation_method: 'yolo',
      segments: [{ segment_id: 'seg-1', segment_index: 0, bbox: { x: 1, y: 2, w: 30, h: 40 }, crop_url: '/seg-a.jpg', pipeline_url: '/pipe-a.jpg' }],
    })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /add image/i }))
    const imageInput = document.querySelector('input[type="file"][accept="image/*"]') as HTMLInputElement
    await userEvent.upload(
      imageInput,
      [
        new File(['a'], 'first.jpg', { type: 'image/jpeg' }),
        new File(['b'], 'second.jpg', { type: 'image/jpeg' }),
      ],
    )

    expect(screen.getByRole('button', { name: /add image/i })).toBeInTheDocument()
    expect(screen.getByText(/Upload 0\/2/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Segment All/i })).toBeInTheDocument()

    await act(async () => {
      resolveFirstUpload?.({ image_id: 'img-a', source_url: '/uploaded-a.jpg' })
    })
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalledTimes(2))
    await act(async () => {
      resolveSecondUpload?.({ image_id: 'img-b', source_url: '/uploaded-b.jpg' })
    })

    await waitFor(() => expect(imagesModule.autoSegment).toHaveBeenCalledTimes(2))
    expect(screen.getByText(/Segmentation Confirmation/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Run Retrieval/i })).toBeInTheDocument()
    expect(screen.queryByText(/Ranked Species Result/i)).not.toBeInTheDocument()
  })

  it('hides batch zip ui for non-owner users, shows for owner and dataowner', async () => {
    mockUseAuth.mockReturnValue({ user: { role: 'user' } })
    const { rerender } = renderPage()

    expect(screen.queryByText(/Batch Upload \(ZIP\)/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /download batch template zip/i })).not.toBeInTheDocument()

    mockUseAuth.mockReturnValue({ user: { role: 'owner' } })
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <RetrievePage />
      </QueryClientProvider>,
    )
    expect(screen.getByRole('button', { name: /batch processing/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    expect(screen.getByText(/Batch Upload \(ZIP\)/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /download batch template zip/i })).toBeInTheDocument()

    mockUseAuth.mockReturnValue({ user: { role: 'dataowner' } })
    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <RetrievePage />
      </QueryClientProvider>,
    )
    await userEvent.click(screen.getByRole('button', { name: /batch processing/i }))
    expect(screen.getByText(/Batch Upload \(ZIP\)/i)).toBeInTheDocument()
  })

  it('shows active feature extraction progress during extract-all instead of unavailable copy', async () => {
    let resolveReindex: ((value: { strain_id: string; images: number; indexed_segments: number }) => void) | undefined
    imagesModule.reindexStrainImages.mockImplementation(() => new Promise((resolve) => {
      resolveReindex = resolve as typeof resolveReindex
    }))

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))

    expect(screen.queryByText(/Feature extraction unavailable/i)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /extract all/i }))

    expect(await screen.findByText(/Feature extraction 0\/1/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /extracting/i })).toBeDisabled()

    await act(async () => {
      resolveReindex?.({ strain_id: 'strain-a', images: 1, indexed_segments: 1 })
    })
  })

  it('persists bbox edits per image and shows success toast', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))
    await userEvent.click(screen.getByRole('button', { name: /save boxes/i }))

    await waitFor(() => expect(imagesModule.patchImageSegments).toHaveBeenCalledWith('img-a', {
      segments: [{ segment_index: 0, bbox: { x: 1, y: 2, w: 30, h: 40 } }],
      deleted_segments: [],
    }))
    expect(mockToast.success).toHaveBeenCalledWith('Saved boxes for a.jpg')
  })

  it('confirms segmentation per image before retrieval and shows extracted status', async () => {
    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))

    expect(screen.getByText(/Segmentation Confirmation/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reindex image/i })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /confirm image/i }))
    await waitFor(() => expect(imagesModule.reindexImage).toHaveBeenCalledWith('img-a'))
    expect(mockToast.success).toHaveBeenCalledWith('Confirmed a.jpg')
    expect(screen.getByText(/Feature extracted/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Run Retrieval/i })).toBeInTheDocument()
  })

  it('prevents duplicate retrieval submissions from results config changes while a request is pending', async () => {
    mockJobStatus = { data: { status: 'completed', estimated_seconds: 0 }, isLoading: false }
    let pendingSuccess: ((value: { job_id: string; status: string; estimated_seconds: number }) => void) | undefined
    mockStartMutation.mockImplementation((_payload, options) => {
      pendingSuccess = options?.onSuccess
    })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /^Load Sample$/i }))
    await waitFor(() => expect(imagesModule.uploadImage).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: /^Segment All/i }))
    await userEvent.click(screen.getByRole('button', { name: /confirm image/i }))
    await userEvent.click(screen.getByRole('button', { name: /^Run Retrieval/i }))

    expect(mockStartMutation).toHaveBeenCalledTimes(1)
    await act(async () => {
      pendingSuccess?.({ job_id: 'job-3', status: 'processing', estimated_seconds: 5 })
    })
    mockJobStatus = { data: { status: 'running', estimated_seconds: 5 }, isLoading: false }

    expect(screen.getByRole('button', { name: /apply retrieval config/i })).toBeDisabled()
    expect(mockStartMutation).toHaveBeenCalledTimes(1)
  })
})

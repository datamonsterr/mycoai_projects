import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { mediaList } from '@/lib/mock-data'
import { sampleStrains } from '@/lib/sample-assets'
import { downloadTemplate, INDEX_TEMPLATE_CSV, downloadAgentsMd, downloadTemplateZip } from '@/lib/template'
import { uploadImage, uploadBatchZip, autoSegment } from '@/services/images'
import { ArrowRight, ChevronRight, Download, FlaskConical, Images, Loader2, Plus, Trash2, FileText, FileArchive } from 'lucide-react'
import { useStartRetrieval, useJobStatus, useJobResults } from '@/hooks/use-retrieval'
import type { RetrievalRanking, RetrievalNeighbor } from '@/services/types'

type Step = 'upload' | 'segmentation' | 'processing' | 'results'

type StrainImage = {
  id: string
  fileName: string
  media: string
  mediaIsNew: boolean
  maxColonies: string
  original?: string
  yoloPreview?: string
  yoloBboxes?: Array<{ x: number; y: number; w: number; h: number }>
  segments?: Array<{ url: string; bbox: { x: number; y: number; w: number; h: number } }>
}

type StrainDraft = {
  strain: string
  images: StrainImage[]
}

type Rank = {
  rank: number
  species: string
  score: number
}

const ranks: Rank[] = [
  { rank: 1, species: 'thymicola', score: 0.91 },
  { rank: 2, species: 'sclerotigenum', score: 0.66 },
  { rank: 3, species: 'Penicillium commune', score: 0.38 },
]

const stepLabels: Record<Step, string> = { upload: 'Upload', segmentation: 'Segment', processing: 'Preparing ...', results: 'Results' }

function Breadcrumb({ step, isBatch }: { step: Step; isBatch: boolean }) {
  const labels = ['Retrieve Species', isBatch ? 'Batch Strains' : 'Single Strain', stepLabels[step]]
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
      {labels.map((label, index) => (
        <span key={`${label}-${index}`} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="h-3 w-3" />}
          <span className={index === labels.length - 1 ? 'text-foreground font-medium' : ''}>{label}</span>
        </span>
      ))}
    </nav>
  )
}

function Stepper({ step }: { step: Step }) {
  const order: Array<{ key: Step; label: string }> = [
    { key: 'upload', label: 'Upload' },
    { key: 'segmentation', label: 'Segment' },
    { key: 'results', label: 'Results' },
  ]
  const displayStep = step === 'processing' ? 'segmentation' : step
  return (
    <div className="flex items-center gap-2">
      {order.map((item, index) => (
        <div key={item.key} className="flex items-center gap-2">
          <div className={`flex h-8 w-8 items-center justify-center rounded-full font-heading text-sm font-medium ${displayStep === item.key ? 'bg-primary text-primary-foreground' : (step === 'results' && index < 2 ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground')}`}>
            {step === 'results' && index < 2 ? <ChevronRight className="h-4 w-4" /> : index + 1}
          </div>
          <span className={`text-sm ${displayStep === item.key ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
            {item.label}
          </span>
          {index < order.length - 1 && <div className="h-px w-8 bg-border" />}
        </div>
      ))}
    </div>
  )
}

type SampleImage = {
  id: string
  fileName: string
  media: string
  original: string
  yoloPreview?: string
  yoloBboxes?: ReadonlyArray<{ x: number; y: number; w: number; h: number }>
  segments: ReadonlyArray<{ url: string; bbox: { x: number; y: number; w: number; h: number } }>
}

type SampleStrain = {
  species: string
  strain: string
  images: ReadonlyArray<SampleImage>
}

const typedSampleStrains = sampleStrains as unknown as ReadonlyArray<SampleStrain>

function fromSampleImage(image: SampleImage): StrainImage {
  return {
    id: image.id,
    fileName: image.fileName,
    media: image.media,
    mediaIsNew: false,
    maxColonies: 'default',
    original: image.original,
    yoloPreview: image.yoloPreview,
    yoloBboxes: image.yoloBboxes ? [...image.yoloBboxes] : undefined,
    segments: [...image.segments],
  }
}

function mediaOptions() {
  return mediaList.filter((media) => !media.is_archived).map((media) => (
    <option key={media.media_id} value={media.name}>{media.name}</option>
  ))
}

function imageCount(strains: StrainDraft[]) {
  return strains.reduce((sum, strain) => sum + strain.images.length, 0)
}

function getNeighbors(currentImage: StrainImage, k = 5) {
  const pool = typedSampleStrains.flatMap((strain) =>
    strain.images.map((image) => ({
      strain: strain.strain,
      species: strain.species,
      media: image.media,
      original: image.original,
    })),
  )
  const sameMedia = pool.filter((image) => image.media === currentImage.media)
  const ordered = [...sameMedia, ...pool.filter((image) => image.media !== currentImage.media)]
  return ordered.slice(0, k).map((image, index) => ({ ...image, similarity: Math.max(0.51, 0.94 - index * 0.07) }))
}

function ImageMetaCard({
  image,
  onUpdate,
  onRemove,
}: {
  image: StrainImage
  onUpdate: (field: Partial<StrainImage>) => void
  onRemove: () => void
}) {
  return (
    <Card className="overflow-hidden">
      <div className="relative aspect-[4/3] bg-muted">
        {image.original ? (
          <img src={image.original} alt={`${image.fileName} plate`} className="h-full w-full object-contain" />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">Image preview</div>
        )}
        <Badge className="absolute left-2 top-2" variant="secondary">{image.media || 'Media'}</Badge>
        <Button variant="destructive" size="sm" className="absolute right-2 top-2 h-8 px-2" onClick={onRemove}>
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
      <CardContent className="p-3">
        <div className="grid grid-cols-[1fr_96px_96px] gap-2 items-end">
          <div className="space-y-1">
            <Label className="text-xs">File</Label>
            <Input className="h-8 text-xs" value={image.fileName} readOnly />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Media</Label>
            <Select className="h-8 text-xs" value={image.media} disabled={image.mediaIsNew} onChange={(e) => onUpdate({ media: e.target.value, mediaIsNew: false })}>
              {mediaOptions()}
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Max</Label>
            <Select className="h-8 text-xs" value={image.maxColonies} onChange={(e) => onUpdate({ maxColonies: e.target.value })}>
              <option value="default">Auto</option>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => <option key={n} value={String(n)}>{n}</option>)}
            </Select>
          </div>
        </div>
        <label className="mt-2 flex items-center gap-2 text-xs">
          <input type="checkbox" checked={image.mediaIsNew} onChange={(e) => onUpdate({ mediaIsNew: e.target.checked, media: e.target.checked ? '' : mediaList[0].name })} />
          <span>New/other media</span>
          {image.mediaIsNew && <Input className="h-7 max-w-48 text-xs" placeholder="Media name" value={image.media} onChange={(e) => onUpdate({ media: e.target.value })} />}
        </label>
      </CardContent>
    </Card>
  )
}

function SegmentCard({
  image,
  onUpdateBbox,
  onAddBbox,
  onRemoveBbox,
}: {
  image: StrainImage
  onUpdateBbox: (segmentIndex: number, bbox: { x: number; y: number; w: number; h: number }) => void
  onAddBbox: (bbox: { x: number; y: number; w: number; h: number }) => void
  onRemoveBbox: (segmentIndex: number) => void
}) {
  const segments = image.segments ?? []
  const yoloBboxes = image.yoloBboxes ?? []
  const preview = image.yoloPreview || image.original
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [drawing, setDrawing] = useState<{ x: number; y: number; w: number; h: number } | null>(null)

  const [imgDims, setImgDims] = useState<{ w: number; h: number; dispW: number; dispH: number; offX: number; offY: number }>({ w: 320, h: 320, dispW: 320, dispH: 320, offX: 0, offY: 0 })

  useEffect(() => {
    const img = imgRef.current
    if (!img) return
    function update() {
      const natural = { w: img!.naturalWidth || 320, h: img!.naturalHeight || 320 }
      const containerRect = img!.parentElement?.getBoundingClientRect() ?? { width: 320, height: 320 }
      const scale = Math.min(containerRect.width / natural.w, containerRect.height / natural.h)
      const dispW = natural.w * scale
      const dispH = natural.h * scale
      const offX = (containerRect.width - dispW) / 2
      const offY = (containerRect.height - dispH) / 2
      setImgDims({ ...natural, dispW, dispH, offX, offY })
    }
    update()
    window.addEventListener('resize', update)
    if (img.complete) update()
    else img.onload = update
    return () => { window.removeEventListener('resize', update); img.onload = null }
  }, [preview])

  const natW = imgDims.w || 320; const natH = imgDims.h || 320
  const bboxes = yoloBboxes.length ? yoloBboxes : segments.map((segment) => segment.bbox)
  const allBboxes = drawing ? [...bboxes, drawing] : bboxes

  const startDraw = (e: React.MouseEvent<HTMLDivElement>) => {
    const container = containerRef.current
    if (!container) return
    const rect = container.getBoundingClientRect()
    const localX = ((e.clientX - rect.left - imgDims.offX) / imgDims.dispW) * natW
    const localY = ((e.clientY - rect.top - imgDims.offY) / imgDims.dispH) * natH
    const initX = Math.round(Math.max(0, localX))
    const initY = Math.round(Math.max(0, localY))
    setDrawing({ x: initX, y: initY, w: 0, h: 0 })
    const handleMove = (ev: MouseEvent) => {
      const curX = ((ev.clientX - rect.left - imgDims.offX) / imgDims.dispW) * natW
      const curY = ((ev.clientY - rect.top - imgDims.offY) / imgDims.dispH) * natH
      setDrawing({
        x: Math.round(Math.max(0, Math.min(initX, curX))),
        y: Math.round(Math.max(0, Math.min(initY, curY))),
        w: Math.round(Math.abs(curX - initX)),
        h: Math.round(Math.abs(curY - initY)),
      })
    }
    const handleUp = () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleUp)
      setDrawing((prev) => {
        if (prev && prev.w > 10 && prev.h > 10) onAddBbox(prev)
        return null
      })
    }
    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleUp)
  }

  const startMove = (index: number, e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation()
    const box = e.currentTarget; const parent = box.parentElement
    if (!parent) return
    const startX = e.clientX; const startY = e.clientY; const initLeft = box.offsetLeft; const initTop = box.offsetTop
    const bbox = bboxes[index]
    const handleMove = (ev: MouseEvent) => {
      const parentRect = parent.getBoundingClientRect()
      const newLeft = Math.max(0, Math.min(parentRect.width - box.offsetWidth, initLeft + ev.clientX - startX))
      const newTop = Math.max(0, Math.min(parentRect.height - box.offsetHeight, initTop + ev.clientY - startY))
      const localX = Math.round(((newLeft - imgDims.offX) / imgDims.dispW) * natW)
      const localY = Math.round(((newTop - imgDims.offY) / imgDims.dispH) * natH)
      onUpdateBbox(index, { x: Math.max(0, localX), y: Math.max(0, localY), w: bbox.w, h: bbox.h })
    }
    const handleUp = () => { document.removeEventListener('mousemove', handleMove); document.removeEventListener('mouseup', handleUp) }
    document.addEventListener('mousemove', handleMove); document.addEventListener('mouseup', handleUp)
  }

  const startResize = (index: number, e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation()
    const startX = e.clientX; const startY = e.clientY
    const bbox = bboxes[index]
    const handleMove = (ev: MouseEvent) => {
      const dx = ((ev.clientX - startX) / imgDims.dispW) * natW
      const dy = ((ev.clientY - startY) / imgDims.dispH) * natH
      onUpdateBbox(index, {
        x: bbox.x,
        y: bbox.y,
        w: Math.max(10, bbox.w + Math.round(dx)),
        h: Math.max(10, bbox.h + Math.round(dy)),
      })
    }
    const handleUp = () => { document.removeEventListener('mousemove', handleMove); document.removeEventListener('mouseup', handleUp) }
    document.addEventListener('mousemove', handleMove); document.addEventListener('mouseup', handleUp)
  }

  const toPxW = (val: number) => `${Math.max(4, (val / natW) * imgDims.dispW)}px`
  const toPxH = (val: number) => `${Math.max(4, (val / natH) * imgDims.dispH)}px`

  return (
    <Card>
      <CardHeader className="p-3 pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm font-heading">{image.fileName}</CardTitle>
            <CardDescription className="text-xs">{image.media} · {segments.length} detected segments · YOLO segmentation</CardDescription>
          </div>
          <Badge variant="success">Ready</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <div className="grid gap-3 lg:grid-cols-[minmax(360px,1.15fr)_1fr]">
          <div
            ref={containerRef}
            className="relative min-h-[320px] overflow-hidden rounded-lg border border-border bg-muted cursor-crosshair"
            onMouseDown={startDraw}
          >
            {preview && <img ref={imgRef} src={preview} alt={`${image.fileName} with YOLO boxes`} className="pointer-events-none h-full max-h-[520px] min-h-[320px] w-full object-contain select-none" />}
            {allBboxes.map((bbox, index) => (
              <div
                key={`${image.id}-bbox-${index}`}
                className={`absolute border-2 rounded-md bg-primary/10 pointer-events-auto group ${index >= bboxes.length ? 'border-warning' : 'border-primary'}`}
                style={{
                  left: `${imgDims.offX + (bbox.x / natW) * imgDims.dispW}px`,
                  top: `${imgDims.offY + (bbox.y / natH) * imgDims.dispH}px`,
                  width: toPxW(bbox.w),
                  height: toPxH(bbox.h),
                }}
                onMouseDown={(e) => startMove(index, e)}
              >
                <button className="absolute -top-3 -right-1 hidden group-hover:flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-xs text-white" onMouseDown={(e) => { e.stopPropagation(); onRemoveBbox(index) }}>×</button>
                <div
                  className="absolute -bottom-1 -right-1 hidden group-hover:block h-4 w-4 rounded-full bg-primary border-2 border-white cursor-se-resize"
                  onMouseDown={(e) => startResize(index, e)}
                />
                <div className="absolute -left-2 top-1 z-10 hidden group-hover:block rounded bg-card/95 px-1.5 py-0.5 font-mono text-[10px] shadow-sm text-foreground whitespace-nowrap">
                  {bbox.w}×{bbox.h}
                </div>
              </div>
            ))}
            <div className="absolute left-2 top-2 rounded bg-card/95 px-2 py-1 text-xs shadow-sm">Drag to move · corner to resize · click-drag to add · hover to see X</div>
          </div>
          <div className="grid grid-cols-3 gap-2 content-start">
            {segments.map((segment, index) => (
              <div key={`${image.id}-seg-${index}`} className="relative overflow-hidden rounded-lg border border-border bg-muted">
                <div className="aspect-square">
                  {segment.url ? <img src={segment.url} alt={`Segment ${index + 1}`} className="h-full w-full object-contain" /> : <div className="flex h-full items-center justify-center text-xs text-muted-foreground">Seg {index + 1}</div>}
                </div>
                <div className="flex items-center justify-between border-t border-border bg-card px-2 py-1 text-xs">
                  <span>Seg {index + 1}</span>
                  <span className="font-mono">{segment.bbox.w}×{segment.bbox.h}</span>
                </div>
                <button className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-xs text-white">×</button>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function apiNeighborsToDisplay(neighbors: RetrievalNeighbor[]) {
  return neighbors.map((neighbor) => ({
    strain: neighbor.strain,
    species: neighbor.species,
    media: neighbor.media,
    original: neighbor.image_thumbnail_url,
    similarity: neighbor.similarity,
  }))
}

function ResultDetail({
  strain,
  images,
  knnK,
  aggMethod,
  rankings: apiRankings,
  topNeighbors: apiNeighbors,
}: {
  strain: string
  images: StrainImage[]
  knnK: number
  aggMethod: 'weighted' | 'uni' | 'freq_strength' | 'relative' | 'per_species_avg' | 'max_score' | 'perquery_norm_avg'
  rankings?: RetrievalRanking[]
  topNeighbors?: RetrievalNeighbor[]
}) {
  const displayRanks = apiRankings ?? ranks
  const displayNeighbors = apiNeighbors ? apiNeighborsToDisplay(apiNeighbors) : null
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="p-4">
          <CardTitle className="font-heading">Ranked Species Result</CardTitle>
          <CardDescription>
            {strain} · {images.length} queried images · k={knnK} {aggMethod}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 p-4 pt-0">
          {displayRanks.map((rank) => (
            <div key={rank.rank} className="grid grid-cols-[40px_1fr_140px_64px] items-center gap-3 rounded-lg border border-border p-3">
              <div className="font-heading text-lg font-bold">#{rank.rank}</div>
              <div className="font-heading font-semibold">{rank.species}</div>
              <div className="h-2 overflow-hidden rounded-full bg-muted">
                <div className={`h-full ${rank.score > 0.7 ? 'bg-success' : rank.score > 0.45 ? 'bg-warning' : 'bg-destructive'}`} style={{ width: `${rank.score * 100}%` }} />
              </div>
              <div className="font-mono text-sm">{rank.score.toFixed(2)}</div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="p-4">
          <CardTitle className="font-heading">Per Queried Image KNN Detail</CardTitle>
          <CardDescription>Each uploaded image shows its top k={knnK} matching database images ({aggMethod}).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 p-4 pt-0">
          {images.map((image) => (
            <details key={image.id} className="rounded-lg border border-border bg-card" open>
              <summary className="grid cursor-pointer grid-cols-[160px_1fr_120px] items-center gap-3 p-3 text-sm hover:bg-muted/50">
                <img src={image.original} alt={`${image.fileName} query`} className="h-28 w-40 rounded-md object-contain border border-border bg-muted" />
                <div>
                  <div className="font-heading font-semibold">{image.fileName}</div>
                  <div className="text-xs text-muted-foreground">Query image · media {image.media} · {image.segments?.length ?? 0} segments</div>
                </div>
                <Badge variant="secondary">K={knnK}</Badge>
              </summary>
              <div className="grid grid-cols-1 gap-3 border-t border-border p-3 md:grid-cols-5">
                {(displayNeighbors ?? getNeighbors(image, knnK)).map((neighbor, index) => (
                  <div key={`${image.id}-${neighbor.strain}-${neighbor.media}-${index}`} className="overflow-hidden rounded-lg border border-border bg-muted">
                    <img src={neighbor.original} alt={`${neighbor.species} ${neighbor.media}`} className="h-32 w-full object-contain" />
                    <div className="space-y-1 bg-card p-2 text-xs">
                      <div className="font-heading font-semibold truncate">#{index + 1} {neighbor.species}</div>
                      <div className="font-mono text-muted-foreground">{neighbor.strain} · {neighbor.media}</div>
                      <div className="font-mono">sim {neighbor.similarity.toFixed(2)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

export default function RetrievePage() {
  const [step, setStep] = useState<Step>('upload')
  const [isBatch, setIsBatch] = useState(false)
  const [activeStrain, setActiveStrain] = useState(0)
  const [detailStrain, setDetailStrain] = useState(0)
  const [knnK, setKnnK] = useState(5)
  const [aggMethod, setAggMethod] = useState<'weighted' | 'uni' | 'freq_strength' | 'relative' | 'per_species_avg' | 'max_score' | 'perquery_norm_avg'>('freq_strength')
  const [strains, setStrains] = useState<StrainDraft[]>([{ strain: '', images: [] }])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pendingStrainIndex = useRef(0)
  const [uploading, setUploading] = useState(false)
  const [isZipUploading, setIsZipUploading] = useState(false)
  const [autoSegmenting, setAutoSegmenting] = useState(false)
  const [zipResult, setZipResult] = useState<{
    successful: number
    failed: number
    total: number
    results: Array<{ strain: string; media: string; filename: string; image_id: string }>
  } | null>(null)

  const [jobId, setJobId] = useState<string | null>(null)

  const startRetrieval = useStartRetrieval()
  const jobStatus = useJobStatus(jobId ?? '')
  const jobResults = useJobResults(jobId ?? '', jobStatus.data?.status)

  useEffect(() => {
    if (jobStatus.data?.status === 'completed' && step === 'processing') {
      queueMicrotask(() => setStep('results'))
    }
  }, [jobStatus.data?.status, step])

  const current = strains[activeStrain]
  const totalImages = imageCount(strains)

  const title = isBatch ? 'Batch Strains' : 'Single Strain'

  const loadSampleSingle = () => {
    const sample = typedSampleStrains[0]
    setIsBatch(false)
    setStrains([{ strain: sample.strain, images: sample.images.map(fromSampleImage) }])
    setActiveStrain(0)
  }

  const loadSampleBatch = () => {
    setIsBatch(true)
    setStrains(typedSampleStrains.map((sample) => ({ strain: sample.strain, images: sample.images.map(fromSampleImage) })))
    setActiveStrain(0)
    setDetailStrain(0)
  }

  const addStrain = () => {
    setStrains([...strains, { strain: '', images: [] }])
    setActiveStrain(strains.length)
  }

  const updateStrain = (index: number, field: Partial<StrainDraft>) => {
    setStrains(strains.map((strain, idx) => (idx === index ? { ...strain, ...field } : strain)))
  }

  const removeStrain = (index: number) => {
    const next = strains.filter((_, idx) => idx !== index)
    setStrains(next.length ? next : [{ strain: '', images: [] }])
    setActiveStrain(Math.max(0, Math.min(index - 1, next.length - 1)))
  }

  const addImage = (strainIndex: number) => {
    pendingStrainIndex.current = strainIndex
    fileInputRef.current?.click()
  }

  const handleFilesSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setUploading(true)
    const strainIndex = pendingStrainIndex.current
    const strain = strains[strainIndex]
    const strainName = strain.strain || 'unknown'
    for (const file of Array.from(files)) {
      try {
        const res = await uploadImage(file, strainName, mediaList[0].name)
        const newImage: StrainImage = {
          id: res.image_id,
          fileName: file.name,
          media: res.media,
          mediaIsNew: false,
          maxColonies: 'default',
          original: URL.createObjectURL(file),
        }
        setStrains((prev) => {
          const updated = [...prev]
          updated[strainIndex] = {
            ...updated[strainIndex],
            images: [...updated[strainIndex].images, newImage],
          }
          return updated
        })
      } catch {
        /* continue with next file */
      }
    }
    e.target.value = ''
    setUploading(false)
  }

  const handleBatchZipUpload = async (file: File) => {
    setIsZipUploading(true)
    setZipResult(null)
    try {
      const result = await uploadBatchZip(file)
      setZipResult({ successful: result.successful, failed: result.failed, total: result.total, results: result.results.map((r) => ({ strain: r.strain, media: r.media, filename: r.filename, image_id: r.image_id })) })

      const batchStrains: StrainDraft[] = []
      const strainMap = new Map<string, StrainDraft>()
      for (const r of result.results) {
        const key = r.strain || 'unknown'
        if (!strainMap.has(key)) {
          strainMap.set(key, { strain: key, images: [] })
          batchStrains.push(strainMap.get(key)!)
        }
        strainMap.get(key)!.images.push({
          id: r.image_id || crypto.randomUUID(),
          fileName: r.filename,
          media: r.media || 'MEA',
          mediaIsNew: false,
          maxColonies: 'default',
          original: undefined,
        })
      }
      setStrains(batchStrains)
      setIsBatch(batchStrains.length > 1)
      setActiveStrain(0)
    } catch {
      /* continue */
    } finally {
      setIsZipUploading(false)
    }
  }

  const runAutoSegment = async () => {
    setAutoSegmenting(true)
    let successCount = 0
    try {
      for (const strain of strains) {
        for (const img of strain.images) {
          if (!img.id) continue
          try {
            const result = await autoSegment(img.id, 'kmeans')
            setStrains((prev) => prev.map((s) => ({
              ...s,
              images: s.images.map((i) => {
                if (i.id !== img.id) return i
                return {
                  ...i,
                  segments: result.segments.map((seg) => ({
                    url: seg.crop_url,
                    bbox: { x: seg.bbox.x, y: seg.bbox.y, w: seg.bbox.w, h: seg.bbox.h },
                  })),
                  yoloBboxes: result.segments.map((seg) => ({
                    x: seg.bbox.x, y: seg.bbox.y, w: seg.bbox.w, h: seg.bbox.h,
                  })),
                }
              }),
            })))
            successCount++
          } catch {
            /* skip failed */
          }
        }
      }
      if (successCount > 0) {
        setStep('segmentation')
      }
    } catch {
      /* handle silently */
    } finally {
      setAutoSegmenting(false)
    }
  }

  const updateImage = (strainIndex: number, imageId: string, field: Partial<StrainImage>) => {
    const strain = strains[strainIndex]
    updateStrain(strainIndex, { images: strain.images.map((image) => (image.id === imageId ? { ...image, ...field } : image)) })
  }

  const removeImage = (strainIndex: number, imageId: string) => {
    const strain = strains[strainIndex]
    updateStrain(strainIndex, { images: strain.images.filter((image) => image.id !== imageId) })
  }

  const updateYoloBbox = (strainIndex: number, imageId: string, segmentIndex: number, bbox: { x: number; y: number; w: number; h: number }) => {
    const strain = strains[strainIndex]
    updateStrain(strainIndex, {
      images: strain.images.map((image) => {
        if (image.id !== imageId) return image
        const existing = image.yoloBboxes ?? image.segments?.map((segment) => segment.bbox) ?? []
        return { ...image, yoloBboxes: existing.map((item, index) => (index === segmentIndex ? bbox : item)) }
      }),
    })
  }

  const addYoloBbox = (strainIndex: number, imageId: string, bbox: { x: number; y: number; w: number; h: number }) => {
    const strain = strains[strainIndex]
    updateStrain(strainIndex, {
      images: strain.images.map((image) => {
        if (image.id !== imageId) return image
        const existing = image.yoloBboxes ?? image.segments?.map((segment) => segment.bbox) ?? []
        return { ...image, yoloBboxes: [...existing, bbox] }
      }),
    })
  }

  const removeYoloBbox = (strainIndex: number, imageId: string, segmentIndex: number) => {
    const strain = strains[strainIndex]
    updateStrain(strainIndex, {
      images: strain.images.map((image) => {
        if (image.id !== imageId) return image
        const existing = image.yoloBboxes ?? image.segments?.map((segment) => segment.bbox) ?? []
        return { ...image, yoloBboxes: existing.filter((_, index) => index !== segmentIndex) }
      }),
    })
  }

  const currentSegments = isBatch ? strains[activeStrain]?.images ?? [] : strains[0]?.images ?? []
  const resultStrains = isBatch ? strains : [strains[0]]
  const activeResult = resultStrains[detailStrain] ?? resultStrains[0]

  const totalSegments = useMemo(() => strains.reduce((sum, strain) => sum + strain.images.reduce((imgSum, image) => imgSum + (image.segments?.length ?? 3), 0), 0), [strains])

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Breadcrumb step={step} isBatch={isBatch} />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Retrieve Species</h1>
            <p className="text-sm text-muted-foreground">Strain-centered workflow. Each strain has multiple media images; KNN results aggregate per strain.</p>
          </div>
          <Stepper step={step} />
        </div>
      </div>

      {step === 'processing' && (
        <Card className="max-w-2xl mx-auto">
          <CardHeader className="p-6 text-center">
            <CardTitle className="font-heading text-xl">Running Retrieval</CardTitle>
            <CardDescription>
              {startRetrieval.isPending
                ? 'Submitting query...'
                : jobStatus.data?.status === 'queued'
                  ? 'Job queued — waiting for worker'
                  : jobStatus.data?.status === 'running'
                    ? 'Processing retrieval pipeline...'
                    : jobStatus.data?.status === 'completed'
                      ? 'Retrieval complete'
                      : jobStatus.data?.status ?? 'Preparing...'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 p-6 pt-0">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium">
                  {jobStatus.data?.status ?? 'queued'}
                </span>
                <span className="font-mono">
                  {jobStatus.data?.status === 'completed'
                    ? 'Done'
                    : jobStatus.data?.estimated_seconds
                      ? `~${jobStatus.data.estimated_seconds}s`
                      : '...'}
                </span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500 ease-linear"
                  style={{
                    width: jobStatus.data?.status === 'completed'
                      ? '100%'
                      : jobStatus.data?.status === 'running'
                        ? '70%'
                        : '30%',
                    animation: jobStatus.data?.status === 'completed' ? 'none' : undefined,
                  }}
                />
              </div>
            </div>

            {startRetrieval.isError && (
              <p className="text-center text-sm text-destructive">
                {startRetrieval.error instanceof Error ? startRetrieval.error.message : 'Failed to start retrieval'}
              </p>
            )}

            {jobStatus.data?.status === 'failed' && (
              <p className="text-center text-sm text-destructive">Job failed. Check the image and try again.</p>
            )}

            {jobStatus.isLoading && (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Polling job status...
              </div>
            )}

            {jobStatus.data?.status === 'completed' && (
              <p className="text-center text-xs text-muted-foreground">Loading results...</p>
            )}
          </CardContent>
        </Card>
      )}

      {step === 'upload' && (
        <div className="space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*"
            className="hidden"
            onChange={handleFilesSelected}
          />
          {/* --- Batch ZIP Upload Section --- */}
          <Card className="mb-4">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="font-heading text-base">Batch Upload (ZIP)</CardTitle>
              <CardDescription>
                Download the template zip with AGENTS.md instructions, organize images by strain, re-zip, and upload.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-0 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => downloadTemplateZip()}>
                  <Download className="h-4 w-4" /> Download Template (ZIP)
                </Button>
                <Button variant="outline" size="sm" onClick={downloadAgentsMd}><FileText className="h-4 w-4" /> AGENTS.md</Button>
              </div>

              <label
                className={`flex h-36 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
                  isZipUploading ? 'border-primary bg-primary/5' : 'border-border hover:border-primary'
                }`}
                onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-primary') }}
                onDragLeave={(e) => { e.currentTarget.classList.remove('border-primary') }}
                onDrop={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.remove('border-primary')
                  const file = e.dataTransfer.files?.[0]
                  if (file?.name.endsWith('.zip')) handleBatchZipUpload(file)
                }}
              >
                <input
                  type="file"
                  accept=".zip"
                  className="hidden"
                  disabled={isZipUploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleBatchZipUpload(file)
                    e.target.value = ''
                  }}
                />
                {isZipUploading ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <span className="text-sm text-muted-foreground">Processing batch...</span>
                  </div>
                ) : (
                  <>
                    <FileArchive className="mb-2 h-8 w-8 text-muted-foreground" />
                    <span className="text-sm font-medium">Drop ZIP here or click to browse</span>
                    <span className="text-xs text-muted-foreground">mycoai_batch_template.zip with AGENTS.md</span>
                  </>
                )}
              </label>

              {zipResult && (
                <div className="rounded-lg border border-border p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={zipResult.failed > 0 ? 'warning' : 'success'}>
                      {zipResult.successful} successful, {zipResult.failed} failed
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {zipResult.total} total images in batch
                    </span>
                  </div>
                  {zipResult.results.length > 0 && (
                    <div className="max-h-36 overflow-auto text-xs">
                      <table className="w-full">
                        <thead>
                          <tr className="text-left text-muted-foreground">
                            <th className="pb-1 pr-2">Strain</th>
                            <th className="pb-1 pr-2">Media</th>
                            <th className="pb-1">File</th>
                          </tr>
                        </thead>
                        <tbody>
                          {zipResult.results.map((r, i) => (
                            <tr key={i} className="border-t border-border">
                              <td className="py-1 pr-2">{r.strain}</td>
                              <td className="py-1 pr-2">{r.media}</td>
                              <td className="py-1 text-muted-foreground">{r.filename}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => downloadTemplate('mycoai_retrieve_template.csv', INDEX_TEMPLATE_CSV)}><Download className="h-4 w-4" /> Download Template</Button>
            <Button variant="outline" size="sm" onClick={downloadAgentsMd}><FileText className="h-4 w-4" /> AGENTS.md</Button>
            <Button variant={!isBatch ? 'default' : 'outline'} size="sm" onClick={() => { setIsBatch(false); setActiveStrain(0) }}>
              <FlaskConical className="h-4 w-4" /> Single Strain
            </Button>
            <Button variant={isBatch ? 'default' : 'outline'} size="sm" onClick={() => setIsBatch(true)}>
              <Images className="h-4 w-4" /> Batch Strains
            </Button>
            <Button variant="outline" size="sm" onClick={loadSampleSingle}><Download className="h-4 w-4" /> Load Single Sample</Button>
            <Button variant="outline" size="sm" onClick={loadSampleBatch}><Download className="h-4 w-4" /> Load Batch Sample</Button>
            {isBatch && <Button variant="outline" size="sm" onClick={addStrain}><Plus className="h-4 w-4" /> Add Strain</Button>}
            <div className="ml-auto text-xs text-muted-foreground">{strains.length} strain(s) · {totalImages} image(s)</div>
          </div>

          <div className="flex flex-wrap gap-2 border-b border-border pb-2">
            {(isBatch ? strains : [strains[0]]).map((strain, index) => (
              <button
                key={`${strain.strain}-${index}`}
                onClick={() => setActiveStrain(index)}
                className={`rounded-t-md px-3 py-2 text-sm transition-colors cursor-pointer ${activeStrain === index ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
              >
                {strain.strain || `${title} ${index + 1}`} <span className="text-xs opacity-75">({strain.images.length})</span>
              </button>
            ))}
          </div>

          {current && (
            <Card>
              <CardHeader className="p-4 pb-3">
                <div className="grid gap-3 lg:grid-cols-[280px_1fr_auto] lg:items-end">
                  <div className="space-y-1">
                    <Label htmlFor="strain" className="text-xs">Strain Identifier</Label>
                    <Input id="strain" className="h-9" placeholder="e.g. T379" value={current.strain} onChange={(e) => updateStrain(activeStrain, { strain: e.target.value })} />
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Compact metadata shown per card. Bigger plate preview helps catch wrong media/image before segmentation.
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={uploading} onClick={() => addImage(activeStrain)}><Plus className="h-4 w-4" /> {uploading ? 'Uploading...' : 'Add Image'}</Button>
                    <Button variant="default" size="sm" disabled={autoSegmenting || current.images.length === 0} onClick={runAutoSegment}>
                      {autoSegmenting ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Segmenting...</>
                      ) : (
                        <><Images className="h-4 w-4" /> Auto Segment</>
                      )}
                    </Button>
                    {isBatch && <Button variant="ghost" size="sm" className="text-destructive" onClick={() => removeStrain(activeStrain)}><Trash2 className="h-4 w-4" /></Button>}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                {current.images.length === 0 ? (
                  <button className="flex h-64 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-sm text-muted-foreground hover:border-primary" disabled={uploading} onClick={() => addImage(activeStrain)}>
                    <Images className="mb-2 h-8 w-8" /> {uploading ? 'Uploading...' : 'Add first image for this strain'}
                  </button>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {current.images.map((image) => (
                      <ImageMetaCard
                        key={image.id}
                        image={image}
                        onUpdate={(field) => updateImage(activeStrain, image.id, field)}
                        onRemove={() => removeImage(activeStrain, image.id)}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {step === 'segmentation' && (
        <div className="space-y-4">
          {isBatch && (
            <div className="flex flex-wrap gap-2 border-b border-border pb-2">
              {strains.map((strain, index) => (
                <button
                  key={`${strain.strain}-${index}`}
                  onClick={() => setActiveStrain(index)}
                  className={`rounded-t-md px-3 py-2 text-sm transition-colors cursor-pointer ${activeStrain === index ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
                >
                  {strain.strain || `Strain ${index + 1}`} <span className="text-xs opacity-75">{strain.images.length} img</span>
                </button>
              ))}
            </div>
          )}
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="font-heading">Segmentation Review</CardTitle>
              <CardDescription>
                {isBatch ? `${strains[activeStrain]?.strain || `Strain ${activeStrain + 1}`}` : `${strains[0]?.strain || 'Single strain'}`} · bigger plate view · compact segment grid · editable bbox controls
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-4 pt-0">
              {currentSegments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No images for this strain.</p>
              ) : currentSegments.map((image) => (
                <SegmentCard
                  key={image.id}
                  image={image}
                  onUpdateBbox={(si, bb) => updateYoloBbox(activeStrain, image.id, si, bb)}
                  onAddBbox={(bb) => addYoloBbox(activeStrain, image.id, bb)}
                  onRemoveBbox={(si) => removeYoloBbox(activeStrain, image.id, si)}
                />
              ))}
              <div className="flex gap-2">
                <Button variant="outline" size="sm">Add Bounding Box</Button>
                <Button variant="outline" size="sm">Reset Current Image</Button>
                <Badge variant="secondary" className="ml-auto">{totalSegments} total segments</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {step === 'results' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card px-4 py-3">
            <span className="text-sm font-medium">KNN Configuration</span>
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <label className="text-xs text-muted-foreground whitespace-nowrap">K: {knnK}</label>
              <input
                type="range"
                min={1}
                max={15}
                step={1}
                value={knnK}
                onChange={(e) => setKnnK(Number(e.target.value))}
                className="flex-1 h-2 accent-primary cursor-pointer"
              />
              <span className="font-mono text-xs w-6 text-right">{knnK}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Aggregation:</span>
              <button
                onClick={() => setAggMethod('weighted')}
                className={`rounded-full px-3 py-1 text-xs font-medium cursor-pointer ${aggMethod === 'weighted' ? 'bg-primary text-primary-foreground' : 'border border-border bg-card text-muted-foreground hover:text-foreground'}`}
              >
                weighted
              </button>
              <button
                onClick={() => setAggMethod('uni')}
                className={`rounded-full px-3 py-1 text-xs font-medium cursor-pointer ${aggMethod === 'uni' ? 'bg-primary text-primary-foreground' : 'border border-border bg-card text-muted-foreground hover:text-foreground'}`}
              >
                uni
              </button>
              <button
                onClick={() => setAggMethod('freq_strength')}
                className={`rounded-full px-3 py-1 text-xs font-medium cursor-pointer ${aggMethod === 'freq_strength' ? 'bg-primary text-primary-foreground' : 'border border-border bg-card text-muted-foreground hover:text-foreground'}`}
              >
                freq_strength
              </button>
            </div>
          </div>
          {isBatch ? (
            <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
              <Card>
                <CardHeader className="p-4">
                  <CardTitle className="font-heading text-base">Batch Results</CardTitle>
                  <CardDescription>Click strain to inspect result detail.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 p-4 pt-0">
                  {resultStrains.map((strain, index) => (
                    <button
                      key={`${strain.strain}-result-${index}`}
                      onClick={() => setDetailStrain(index)}
                      className={`w-full rounded-md p-3 text-left text-sm transition-colors cursor-pointer ${detailStrain === index ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/70'}`}
                    >
                      <div className="font-heading font-semibold">{strain.strain || `Strain ${index + 1}`}</div>
                      <div className="text-xs opacity-75">{strain.images.length} images · top: {jobResults.data?.rankings?.[0]?.species ?? ranks[index % ranks.length].species}</div>
                    </button>
                  ))}
                  <Button variant="outline" size="sm" className="w-full"><Download className="h-4 w-4" /> Export Batch CSV</Button>
                </CardContent>
              </Card>
              <ResultDetail strain={activeResult?.strain || 'Strain'} images={activeResult?.images ?? []} knnK={knnK} aggMethod={aggMethod} rankings={jobResults.data?.rankings} topNeighbors={jobResults.data?.rankings?.[0]?.neighbors} />
            </div>
          ) : (
            <ResultDetail strain={strains[0]?.strain || 'Single strain'} images={strains[0]?.images ?? []} knnK={knnK} aggMethod={aggMethod} rankings={jobResults.data?.rankings} topNeighbors={jobResults.data?.rankings?.[0]?.neighbors} />
          )}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" disabled={step === 'upload' || step === 'processing'} onClick={() => setStep(step === 'results' ? 'segmentation' : 'upload')}>Previous</Button>
        <Button
          onClick={() => {
            if (step === 'upload') setStep('segmentation')
            if (step === 'segmentation') {
              const queryImageId = strains[0]?.images[0]?.id
              if (!queryImageId) return
              setStep('processing')
              startRetrieval.mutate(
                {
                  image_id: queryImageId,
                  k: knnK,
                  aggregation: aggMethod,
                  environment_strategy: 'mean',
                },
                {
                  onSuccess: (data) => setJobId(data.job_id),
                },
              )
            }
          }}
          disabled={step === 'results' || step === 'processing'}
        >
          {step === 'upload' ? 'Segment All' : step === 'processing' ? 'Running...' : 'Run Retrieval'} <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

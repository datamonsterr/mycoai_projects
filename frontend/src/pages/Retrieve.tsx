import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import JSZip from 'jszip'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { sampleStrains } from '@/lib/sample-assets'
import { downloadTemplateZip } from '@/lib/template'
import { uploadImage, uploadBatchZip, autoSegment, getBatchProgress, patchImageSegments, updateImageMedia, reindexImage, type BatchProgress } from '@/services/images'
import { useMediaList } from '@/hooks/use-taxonomy'
import { ArrowRight, ChevronRight, Download, FlaskConical, Images, Loader2, Plus, Trash2, FileArchive } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useStartRetrieval, useJobStatus, useJobResults } from '@/hooks/use-retrieval'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/lib/use-auth'
import type { RetrievalRanking, RetrievalNeighbor, RetrievalQueryImageResult } from '@/services/types'

type Step = 'upload' | 'segmentation' | 'processing' | 'results'

type RetrievalConfig = {
  k: number
  aggregation: 'weighted' | 'uni' | 'freq_strength' | 'relative' | 'per_species_avg' | 'max_score' | 'perquery_norm_avg'
}

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
  selected?: boolean
  confirmed?: boolean
  featureStatus?: 'pending' | 'extracting' | 'done' | 'failed'
}

type StrainDraft = {
  id?: string
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

const stepLabels: Record<Step, string> = { upload: 'Upload', segmentation: 'Confirm', processing: 'Preparing ...', results: 'Results' }

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
    { key: 'segmentation', label: 'Confirm' },
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
    selected: true,
    confirmed: true,
    featureStatus: 'done',
  }
}

function mediaOptions(items: Array<{ id: string; name: string; is_archived: boolean }>) {
  return items.filter((media) => !media.is_archived).map((media) => (
    <option key={media.id} value={media.name}>{media.name}</option>
  ))
}

function imageCount(strains: StrainDraft[]) {
  return strains.reduce((sum, strain) => sum + strain.images.length, 0)
}

const BATCH_IMAGE_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.jpe'])
const BATCH_ARTIFACT_PATTERNS = [/^segment_\d+\.(jpg|jpeg|png|jpe)$/i, /^prepared\.(jpg|jpeg|png|jpe)$/i, /^source\.(jpg|jpeg|png|jpe)$/i, /^bbox_.*\.(jpg|jpeg|png|jpe)$/i, /^pipeline_.*\.(jpg|jpeg|png|jpe)$/i]

type BatchZipPreview = {
  total: number
  images: BatchProgress['images']
}

async function inspectBatchZip(file: File): Promise<BatchZipPreview> {
  const zip = await JSZip.loadAsync(file)
  const images: BatchProgress['images'] = []
  const mediaNames = new Set(['CREA', 'CYA30', 'CYAS', 'CYA', 'DG18', 'MEA', 'YES', 'OA', 'M40Y'])
  for (const entry of Object.values(zip.files)) {
    if (entry.dir) continue
    const parts = entry.name.split('/').filter(Boolean)
    const filename = parts.at(-1) ?? ''
    const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase()
    if (!BATCH_IMAGE_EXTENSIONS.has(ext)) continue
    if (BATCH_ARTIFACT_PATTERNS.some((pattern) => pattern.test(filename))) continue
    const folderParts = parts.slice(0, -1)
    const strain = folderParts.find((part) => !['images', 'mycoai_batch', 'mycoai_batch_template'].includes(part.toLowerCase()) && !mediaNames.has(part.toUpperCase())) ?? 'unknown-strain'
     const media = folderParts.map((part) => part.toUpperCase()).find((part) => mediaNames.has(part)) ?? (filename.match(/(CREA|CYA30|CYAS|CYA|DG18|MEA|YES|OA|M40Y)/i)?.[1]?.toUpperCase() ?? 'Other media')
     images.push({ filename: entry.name, strain, media: media === 'CYA30' || media === 'CYAS' ? 'CYA' : media, species: 'pending', status: 'queued', image_id: null, segments: 0, error: null, source_url: null })

  }
  return { total: images.length, images }
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
  return sameMedia.slice(0, k).map((image, index) => ({ ...image, similarity: Math.max(0.51, 0.94 - index * 0.07) }))
}

function ImageMetaCard({
  image,
  mediaItems,
  onUpdate,
  onRemove,
}: {
  image: StrainImage
  mediaItems: Array<{ id: string; name: string; is_archived: boolean }>
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
                {mediaOptions(mediaItems)}
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
          <input type="checkbox" checked={image.mediaIsNew} onChange={(e) => onUpdate({ mediaIsNew: e.target.checked, media: e.target.checked ? '' : mediaItems[0]?.name ?? 'Other media' })} />
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
  onSave,
  onConfirm,
  onToggleSelected,
  saving,
  confirming,
}: {
  image: StrainImage
  onUpdateBbox: (segmentIndex: number, bbox: { x: number; y: number; w: number; h: number }) => void
  onAddBbox: (bbox: { x: number; y: number; w: number; h: number }) => void
  onRemoveBbox: (segmentIndex: number) => void
  onSave: () => void
  onConfirm: () => void
  onToggleSelected: (selected: boolean) => void
  saving: boolean
  confirming: boolean
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
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-sm font-heading">{image.fileName}</CardTitle>
            <CardDescription className="text-xs">{image.media} · {segments.length} detected segments · YOLO segmentation</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <input type="checkbox" checked={image.selected ?? false} onChange={(e) => onToggleSelected(e.target.checked)} />
              <span>Select uploaded</span>
            </label>
            <Button size="sm" variant="outline" onClick={onSave} disabled={saving || confirming}>
              {saving ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</> : 'Save boxes'}
            </Button>
            <Button size="sm" onClick={onConfirm} disabled={confirming || !(image.selected ?? false)}>
              {confirming ? <><Loader2 className="h-4 w-4 animate-spin" /> Confirming...</> : 'Confirm image'}
            </Button>
            <Badge variant={image.featureStatus === 'done' ? 'success' : image.featureStatus === 'extracting' ? 'warning' : image.featureStatus === 'failed' ? 'destructive' : image.confirmed ? 'warning' : 'secondary'}>
              {image.featureStatus === 'done' ? 'Feature extracted' : image.featureStatus === 'extracting' ? 'Extracting' : image.featureStatus === 'failed' ? 'Failed' : image.confirmed ? 'Confirmed' : 'Uploaded'}
            </Badge>
          </div>
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

function getRetrievalReadyImages(strain: StrainDraft | undefined) {
  return (strain?.images ?? []).filter((image) => !image.mediaIsNew && !!image.id && !!image.confirmed && ((image.yoloBboxes?.length ?? 0) > 0 || (image.segments?.length ?? 0) > 0))
}

function getAllRetrievalReadyImages(strains: StrainDraft[]) {
  return strains.flatMap((strain) => getRetrievalReadyImages(strain))
}

function getConfirmableImages(strain: StrainDraft | undefined) {
  return (strain?.images ?? []).filter((image) => image.selected && ((image.yoloBboxes?.length ?? 0) > 0 || (image.segments?.length ?? 0) > 0))
}

function hasNewMediaImages(strain: StrainDraft | undefined) {
  return (strain?.images ?? []).some((image) => image.mediaIsNew)
}

function getDisplayImageUrl(image?: Pick<StrainImage, 'original'> | null) {
  return image?.original || ''
}

function getNeighborImageUrl(url: string) {
  return url || ''
}

type DisplayNeighbor = {
  strain: string
  species: string
  media: string
  original: string
  similarity: number
}

function apiNeighborsToDisplay(neighbors: RetrievalNeighbor[] | DisplayNeighbor[]): DisplayNeighbor[] {
  return neighbors.map((neighbor) => ({
    strain: 'strain' in neighbor ? neighbor.strain : '',
    species: 'species' in neighbor ? neighbor.species : '',
    media: 'media' in neighbor ? neighbor.media : '',
    original: 'image_thumbnail_url' in neighbor ? neighbor.image_thumbnail_url : 'original' in neighbor ? neighbor.original : '',
    similarity: 'similarity' in neighbor ? neighbor.similarity : 0,
  }))
}

function mediaFromFilename(filename: string) {
  const parts = filename.split('/').filter(Boolean)
  const media = [...parts].reverse().find((part) => ['CREA', 'CYA30', 'CYAS', 'CYA', 'DG18', 'MEA', 'YES', 'OA', 'M40Y', 'OTHER MEDIA'].includes(part.toUpperCase()))
  if (!media) return 'Other media'
  const normalized = media.toUpperCase()
  return normalized === 'CYA30' || normalized === 'CYAS' ? 'CYA' : normalized
}

function ResultDetail({
  strain,
  images,
  knnK,
  aggMethod,
  rankings: apiRankings,
  queriedImages,
  threshold,
}: {
  strain: string
  images: StrainImage[]
  knnK: number
  aggMethod: 'weighted' | 'uni' | 'freq_strength' | 'relative' | 'per_species_avg' | 'max_score' | 'perquery_norm_avg'
  rankings?: RetrievalRanking[]
  queriedImages?: RetrievalQueryImageResult[]
  threshold?: import('@/services/types').ThresholdConfidence | null
}) {
  const displayRanks = apiRankings ?? ranks
  const showThreshold = threshold != null && threshold.confidence != null
  return (
    <div className="space-y-4">
      {showThreshold && (
        <div className={`flex items-center gap-3 rounded-lg border p-3 ${threshold.is_known ? 'border-success/30 bg-success/5' : 'border-warning/30 bg-warning/5'}`}>
          <div>
            <div className="text-xs text-muted-foreground">Threshold Confidence</div>
            <div className="text-lg font-mono font-bold">{threshold.confidence.toFixed(3)}</div>
          </div>
          <div className="flex-1">
            <div className="text-xs text-muted-foreground">Formula: {threshold.formula} · t={threshold.threshold}</div>
          </div>
          <Badge variant={threshold.is_known ? 'success' : 'warning'}>
            {threshold.is_known ? 'Known' : 'Unknown'}
          </Badge>
        </div>
      )}
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
          <CardTitle className="font-heading">Per Segment KNN Detail</CardTitle>
          <CardDescription>Each query segment shows its own top k={knnK} nearest neighbors ({aggMethod}) in one horizontal row.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 p-4 pt-0">
          {images.map((image) => {
            const queriedImage = queriedImages?.find((item) => item.image_id === image.id)
            const displayImageUrl = queriedImage?.image_url || getDisplayImageUrl(image)
            const querySegments = queriedImage?.segments ?? (image.segments ?? []).map((segment, index) => ({
              segment_index: index,
              segment_image_url: segment.url,
              neighbors: getNeighbors(image, knnK),
            }))

            return (
              <details key={image.id} className="rounded-lg border border-border bg-card" open>
                <summary className="grid cursor-pointer grid-cols-[160px_1fr_120px] items-center gap-3 p-3 text-sm hover:bg-muted/50">
                  {displayImageUrl ? (
                    <img src={displayImageUrl} alt={`${image.fileName} query`} className="h-28 w-40 rounded-md object-contain border border-border bg-muted" />
                  ) : (
                    <div className="flex h-28 w-40 items-center justify-center rounded-md border border-border bg-muted text-xs text-muted-foreground">No preview</div>
                  )}
                  <div>
                    <div className="font-heading font-semibold">{image.fileName}</div>
                    <div className="text-xs text-muted-foreground">Query image · media {queriedImage?.media ?? image.media} · {querySegments.length} segments queried</div>
                  </div>
                  <Badge variant="secondary">K={knnK}</Badge>
                </summary>
                <div className="space-y-4 border-t border-border p-3">
                  {querySegments.map((segment) => {
                    const displayNeighbors = apiNeighborsToDisplay(segment.neighbors)
                    return (
                      <div key={`${image.id}-segment-${segment.segment_index}`} className="space-y-2 rounded-lg border border-border p-3">
                        <div className="flex items-center gap-3">
                          <div className="overflow-hidden rounded-lg border border-border bg-muted">
                            {segment.segment_image_url ? (
                              <img src={segment.segment_image_url} alt={`${image.fileName} segment ${segment.segment_index + 1}`} className="h-24 w-24 object-contain" />
                            ) : (
                              <div className="flex h-24 w-24 items-center justify-center text-xs text-muted-foreground">No segment image</div>
                            )}
                          </div>
                          <div>
                            <div className="font-medium">Segment {segment.segment_index + 1}</div>
                            <div className="text-xs text-muted-foreground">Top {displayNeighbors.length} neighbors</div>
                          </div>
                        </div>
                        <div className="overflow-x-auto">
                          <div className="flex min-w-max gap-3">
                            {displayNeighbors.map((neighbor, index) => (
                              <div key={`${image.id}-${segment.segment_index}-${neighbor.strain}-${neighbor.media}-${index}`} className="w-40 overflow-hidden rounded-lg border border-border bg-muted">
                                {getNeighborImageUrl(neighbor.original) ? (
                                  <img src={getNeighborImageUrl(neighbor.original)} alt={`${neighbor.species} ${neighbor.media}`} className="h-32 w-full object-contain" />
                                ) : (
                                  <div className="flex h-32 w-full items-center justify-center text-xs text-muted-foreground">No neighbor image</div>
                                )}
                                <div className="space-y-1 bg-card p-2 text-xs">
                                  <div className="font-heading font-semibold truncate">#{index + 1} {neighbor.species}</div>
                                  <div className="font-mono text-muted-foreground">{neighbor.strain} · {neighbor.media}</div>
                                  <div className="font-mono">sim {neighbor.similarity.toFixed(2)}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </details>
            )
          })}
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
  const [retrievalConfig, setRetrievalConfig] = useState<RetrievalConfig>({ k: 11, aggregation: 'freq_strength' })
  const [submittedConfig, setSubmittedConfig] = useState<RetrievalConfig>({ k: 11, aggregation: 'freq_strength' })
  const [strains, setStrains] = useState<StrainDraft[]>([{ strain: '', images: [] }])
  const toast = useToast()
  const queryClient = useQueryClient()
  const { data: mediaData } = useMediaList()
  const mediaItems = mediaData?.items ?? []
  const defaultMediaName = mediaItems[0]?.name ?? 'Other media'
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pendingStrainIndex = useRef(0)
  const lastSubmittedConfig = useRef<RetrievalConfig | null>(null)
  const [isZipUploading, setIsZipUploading] = useState(false)
  const [autoSegmenting, setAutoSegmenting] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ completed: number; total: number; current?: string } | null>(null)
  const [segmentProgress, setSegmentProgress] = useState<{ completed: number; total: number; current?: string } | null>(null)
  const [featureProgress, setFeatureProgress] = useState<{ completed: number; total: number; current?: string } | null>(null)
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null)
  const [savingImageId, setSavingImageId] = useState<string | null>(null)
  const [confirmingImageId, setConfirmingImageId] = useState<string | null>(null)
  const [reindexingStrain, setReindexingStrain] = useState(false)
  const [zipResult, setZipResult] = useState<{
    successful: number
    failed: number
    total: number
    results: Array<{ strain: string; media: string; filename: string; image_id: string }>
  } | null>(null)

  const [jobId, setJobId] = useState<string | null>(null)
  const batchPollFailures = useRef(0)

  const { user } = useAuth()
  const isOwner = user?.role === 'owner' || user?.role === 'dataowner'
  const startRetrieval = useStartRetrieval()
  const jobStatus = useJobStatus(jobId ?? '')
  const jobResults = useJobResults(jobId ?? '', jobStatus.data?.status)

  useEffect(() => {
    if (jobStatus.data?.status === 'completed' && step === 'processing') {
      queueMicrotask(() => setStep('results'))
    }
  }, [jobStatus.data?.status, step])

  const syncBatchStrains = useCallback((progress: BatchProgress) => {
    if (!progress.images.length) return
    const strainMap = new Map<string, StrainDraft>()
    const nextStrains: StrainDraft[] = []
    for (const [index, image] of progress.images.entries()) {
      const key = image.strain || 'unknown'
      if (!strainMap.has(key)) {
        const draft: StrainDraft = { id: key, strain: key, images: [] }
        strainMap.set(key, draft)
        nextStrains.push(draft)
      }
        strainMap.get(key)!.images.push({
          id: image.image_id || `${key}-${image.filename}-${index}`,
          fileName: image.filename,
          media: image.media || mediaFromFilename(image.filename),
          mediaIsNew: (image.media || mediaFromFilename(image.filename)) === 'Other media',
          maxColonies: 'default',
          original: image.source_url || undefined,
          segments: image.segment_urls?.map((url) => ({ url, bbox: { x: 0, y: 0, w: 1, h: 1 } })) ?? undefined,
          selected: false,
          confirmed: image.status === 'indexed',
          featureStatus: image.status === 'indexed' ? 'done' : image.status === 'extracting' ? 'extracting' : image.status === 'failed' ? 'failed' : image.status === 'segmented' ? 'pending' : 'pending',
        })

    }
    setStrains(nextStrains.length ? nextStrains : [{ strain: '', images: [] }])
    setIsBatch(nextStrains.length > 1)
    setActiveStrain((current) => Math.min(current, Math.max(0, nextStrains.length - 1)))
  }, [])

  useEffect(() => {
    const batchId = batchProgress?.batch_id
    if (!batchId || !isZipUploading || batchId === 'pending-upload') return
    let cancelled = false
    let timer: number | undefined

    const poll = async () => {
      try {
        const next = await getBatchProgress(batchId)
        if (cancelled) return
        batchPollFailures.current = 0
        setBatchProgress(next)
        syncBatchStrains(next)
        if (next.images.some((image) => image.status === 'failed' && image.error)) {
          const failedCount = next.images.filter((image) => image.status === 'failed').length
          toast.error(`${failedCount} batch image${failedCount === 1 ? '' : 's'} failed during processing`)
        }
        if (next.status !== 'processing') {
          setIsZipUploading(false)
          return
        }
      } catch {
        batchPollFailures.current += 1
        if (batchPollFailures.current >= 3) {
          toast.error('Batch progress polling stopped. Refresh to check final status.')
          setIsZipUploading(false)
          return
        }
      }
      if (!cancelled) timer = window.setTimeout(poll, 800)
    }

    timer = window.setTimeout(poll, 800)
    return () => {
      cancelled = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [batchProgress?.batch_id, isZipUploading, syncBatchStrains, toast])

  const current = strains[activeStrain]
  const totalImages = imageCount(strains)
  const hasPendingConfigChanges = submittedConfig.k !== retrievalConfig.k || submittedConfig.aggregation !== retrievalConfig.aggregation
  const retrievalSubmitting = startRetrieval.isPending || step === 'processing'

  const title = isBatch ? 'Batch Strains' : 'Single Strain'

  const loadSampleSingle = async () => {
    const sample = typedSampleStrains[0]
    setIsBatch(false)
    setUploadProgress({ completed: 0, total: sample.images.length })

    const uploadedImages: StrainImage[] = []
    for (const [index, img] of sample.images.entries()) {
      setUploadProgress({ completed: index, total: sample.images.length, current: img.fileName })
      try {
        const response = await fetch(img.original)
        const blob = await response.blob()
        const file = new File([blob], img.fileName, { type: blob.type })
        const res = await uploadImage(file, sample.strain, img.media)
        
        uploadedImages.push(fromSampleImage({
          ...img,
          id: res.image_id,
          original: res.source_url,
        }))
      } catch (err) {
        console.error(`Failed to upload ${img.fileName}:`, err)
      }
    }
    
      setStrains([{ id: sample.strain, strain: sample.strain, images: uploadedImages }])

    setActiveStrain(0)
    setUploadProgress({ completed: uploadedImages.length, total: sample.images.length })
  }

  const loadSampleBatch = async () => {
    setIsBatch(true)
    const total = typedSampleStrains.reduce((sum, sample) => sum + sample.images.length, 0)
    let completed = 0
    setUploadProgress({ completed: 0, total })

    const uploadedStrains: StrainDraft[] = []
    for (const sample of typedSampleStrains) {
      const uploadedImages: StrainImage[] = []
      for (const img of sample.images) {
        setUploadProgress({ completed, total, current: img.fileName })
        try {
          const response = await fetch(img.original)
          const blob = await response.blob()
          const file = new File([blob], img.fileName, { type: blob.type })
          const res = await uploadImage(file, sample.strain, img.media)
          
          uploadedImages.push(fromSampleImage({
            ...img,
            id: res.image_id,
            original: res.source_url,
          }))
        } catch (err) {
          console.error(`Failed to upload ${img.fileName}:`, err)
        }
        completed += 1
      }
      uploadedStrains.push({ id: sample.strain, strain: sample.strain, images: uploadedImages })
    }
    
    setStrains(uploadedStrains)
    setActiveStrain(0)
    setDetailStrain(0)
    setUploadProgress({ completed, total })
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
    setAutoSegmenting(true)
    const fileList = Array.from(files)
    setUploadProgress({ completed: 0, total: fileList.length })
    setSegmentProgress({ completed: 0, total: fileList.length })
    const strainIndex = pendingStrainIndex.current
    const strain = strains[strainIndex]
    const strainName = strain.strain || 'unknown'
    let uploadedCount = 0
    let segmentedCount = 0
    for (const file of fileList) {
      try {
        setUploadProgress({ completed: uploadedCount, total: fileList.length, current: file.name })
        const res = await uploadImage(file, strainName, defaultMediaName)
        const segmentResult = res.segments?.length
          ? { segments: res.segments }
          : await autoSegment(res.image_id, 'yolo')
        const newImage: StrainImage = {
          id: res.image_id,
          fileName: file.name,
          media: defaultMediaName,
          mediaIsNew: false,
          maxColonies: 'default',
          original: res.source_url,
          segments: segmentResult.segments.map((seg) => ({
            url: seg.crop_url,
            bbox: { x: seg.bbox.x, y: seg.bbox.y, w: seg.bbox.w, h: seg.bbox.h },
          })),
          yoloBboxes: segmentResult.segments.map((seg) => ({
            x: seg.bbox.x, y: seg.bbox.y, w: seg.bbox.w, h: seg.bbox.h,
          })),
          selected: false,
          confirmed: false,
          featureStatus: 'pending',
        }
        uploadedCount += 1
        segmentedCount += 1
        setUploadProgress({ completed: uploadedCount, total: fileList.length, current: file.name })
        setSegmentProgress({ completed: segmentedCount, total: fileList.length, current: file.name })
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
    setAutoSegmenting(false)
    if (segmentedCount > 0) setStep('segmentation')
  }

  const handleBatchZipUpload = async (file: File) => {
    setIsZipUploading(true)
    setZipResult(null)
    try {
      const preview = await inspectBatchZip(file).catch<BatchZipPreview>(() => ({ total: 0, images: [] }))
      if (preview.total > 0) {
        setBatchProgress({
          batch_id: 'pending-upload',
          status: 'processing',
          batch_name: file.name.replace(/\.zip$/i, ''),
          upload: { completed: 0, total: preview.total, percent: 0 },
          segmentation: { completed: 0, total: preview.total, percent: 0 },
          feature_extraction: { completed: 0, total: preview.total, percent: 0 },
          strains: [],
          images: preview.images,
        })
        syncBatchStrains({
          batch_id: 'pending-upload',
          status: 'processing',
          batch_name: file.name.replace(/\.zip$/i, ''),
          upload: { completed: 0, total: preview.total, percent: 0 },
          segmentation: { completed: 0, total: preview.total, percent: 0 },
          feature_extraction: { completed: 0, total: preview.total, percent: 0 },
          strains: [],
          images: preview.images,
        })
      }

      const result = await uploadBatchZip(file)
      const mergedProgress = result.progress.upload.total === 0 && preview.total > 0
        ? {
            ...result.progress,
            upload: { ...result.progress.upload, total: preview.total },
            segmentation: { ...result.progress.segmentation, total: preview.total },
            feature_extraction: { ...result.progress.feature_extraction, total: preview.total },
            images: result.progress.images.length > 0 ? result.progress.images : preview.images,
          }
        : result.progress
      setBatchProgress(mergedProgress)
      syncBatchStrains(mergedProgress)
      setIsZipUploading(result.progress.status === 'processing')
      setZipResult({ successful: result.successful, failed: result.failed, total: result.total || preview.total, results: result.results.map((r) => ({ strain: r.strain, media: r.media, filename: r.filename, image_id: r.image_id })) })
      if (result.failed > 0) {
        toast.error(`${result.failed} batch image${result.failed === 1 ? '' : 's'} failed to upload or segment`)
      }

      if (result.total === 0 && mergedProgress.images.length === 0) {
        toast.error('No valid images found in the uploaded ZIP. Ensure the ZIP contains strain folders with .jpg/.jpeg/.png images.')
        return
      }
      syncBatchStrains(mergedProgress)
    } catch {
      setIsZipUploading(false)
    }
  }

  const runAutoSegment = async () => {
    if (batchProgress?.batch_id) {
      setStep('segmentation')
      return
    }
    setAutoSegmenting(true)
    const total = strains.reduce((sum, strain) => sum + strain.images.length, 0)
    let successCount = 0
    let attemptedCount = 0
    setSegmentProgress({ completed: 0, total })
    try {
      for (const strain of strains) {
        for (const img of strain.images) {
          if (!img.id) continue
          attemptedCount++
          setSegmentProgress({ completed: successCount, total, current: img.fileName })
          try {
            const result = await autoSegment(img.id, 'yolo')
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
            setSegmentProgress({ completed: successCount, total, current: img.fileName })
          } catch {
            /* skip failed */
          }
        }
      }
      if (attemptedCount > 0 && successCount === attemptedCount) {
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

  const toggleImageSelected = useCallback((strainIndex: number, imageId: string, selected: boolean) => {
    setStrains((prev) => prev.map((strain, idx) => ({
      ...strain,
      images: strain.images.map((image) => idx === strainIndex && image.id === imageId ? { ...image, selected } : image),
    })))
  }, [])

  const setSelectAllUploaded = useCallback((strainIndex: number, selected: boolean) => {
    setStrains((prev) => prev.map((strain, idx) => ({
      ...strain,
      images: strain.images.map((image) => idx === strainIndex ? { ...image, selected } : image),
    })))
  }, [])

  const persistSegments = useCallback(async (strainIndex: number, imageId: string) => {
    const image = strains[strainIndex]?.images.find((item) => item.id === imageId)
    if (!image?.id) return
    const bboxes = image.yoloBboxes ?? image.segments?.map((segment) => segment.bbox) ?? []
    setSavingImageId(imageId)
    try {
      const result = await patchImageSegments(image.id, {
        segments: bboxes.map((bbox, index) => ({ segment_index: index, bbox })),
        deleted_segments: [],
      })
      setStrains((prev) => prev.map((strain, idx) => ({
        ...strain,
        images: strain.images.map((item) => {
          if (idx !== strainIndex || item.id !== imageId) return item
          return {
            ...item,
            segments: result.segments.map((seg) => ({
              url: seg.crop_url,
              bbox: { x: seg.bbox.x, y: seg.bbox.y, w: seg.bbox.w, h: seg.bbox.h },
            })),
            yoloBboxes: result.segments.map((seg) => ({
              x: seg.bbox.x,
              y: seg.bbox.y,
              w: seg.bbox.w,
              h: seg.bbox.h,
            })),
          }
        }),
      })))
      toast.success(`Saved boxes for ${image.fileName}`)
    } catch (err) {
      toast.apiError(err, `Failed to save boxes for ${image.fileName}`)
    } finally {
      setSavingImageId(null)
    }
  }, [strains, toast])

  const confirmImage = useCallback(async (strainIndex: number, imageId: string) => {
    const image = strains[strainIndex]?.images.find((item) => item.id === imageId)
    if (!image?.id) return
    setConfirmingImageId(imageId)
    setStrains((prev) => prev.map((strain, idx) => ({
      ...strain,
      images: strain.images.map((item) => idx === strainIndex && item.id === imageId ? { ...item, featureStatus: 'extracting', confirmed: true } : item),
    })))
    try {
      await reindexImage(image.id)
      setStrains((prev) => prev.map((strain, idx) => ({
        ...strain,
        images: strain.images.map((item) => idx === strainIndex && item.id === imageId ? { ...item, featureStatus: 'done', confirmed: true } : item),
      })))
      toast.success(`Confirmed ${image.fileName}`)
    } catch (err) {
      setStrains((prev) => prev.map((strain, idx) => ({
        ...strain,
        images: strain.images.map((item) => idx === strainIndex && item.id === imageId ? { ...item, featureStatus: 'failed', confirmed: false } : item),
      })))
      toast.apiError(err, `Failed to confirm ${image.fileName}`)
    } finally {
      setConfirmingImageId(null)
    }
  }, [strains, toast])

  const runStrainReindex = useCallback(async () => {
    const strain = strains[activeStrain]
    if (!strain) return
    const images = strain.images.filter((image) => image.id && (image.segments?.length ?? 0) > 0)
    setReindexingStrain(true)
    setFeatureProgress({ completed: 0, total: images.length, current: strain.strain || 'New strain' })
    let completed = 0
    try {
      for (const image of images) {
        setFeatureProgress({ completed, total: images.length, current: image.fileName })
        setStrains((prev) => prev.map((item, strainIndex) => ({
          ...item,
          images: item.images.map((candidate) => strainIndex === activeStrain && candidate.id === image.id
            ? { ...candidate, featureStatus: 'extracting' }
            : candidate),
        })))
        try {
          if (image.media) await updateImageMedia(image.id, image.media)
          await reindexImage(image.id)
          completed += 1
          setStrains((prev) => prev.map((item, strainIndex) => ({
            ...item,
            images: item.images.map((candidate) => strainIndex === activeStrain && candidate.id === image.id
              ? { ...candidate, featureStatus: 'done', confirmed: true }
              : candidate),
          })))
        } catch (err) {
          setStrains((prev) => prev.map((item, strainIndex) => ({
            ...item,
            images: item.images.map((candidate) => strainIndex === activeStrain && candidate.id === image.id
              ? { ...candidate, featureStatus: 'failed' }
              : candidate),
          })))
          toast.apiError(err, `Failed to extract ${image.fileName}`)
        }
      }
      setFeatureProgress({ completed, total: images.length, current: strain.strain || 'New strain' })
      if (completed === images.length) toast.success(`Extracted ${completed} image(s) for ${strain.strain || 'new strain'}`)
    } finally {
      setReindexingStrain(false)
    }
  }, [activeStrain, strains, toast])

  const totalSegments = useMemo(() => strains.reduce((sum, strain) => sum + strain.images.reduce((imgSum, image) => imgSum + (image.segments?.length ?? 3), 0), 0), [strains])
  const retrievalReadyImages = isBatch ? getAllRetrievalReadyImages(strains) : getRetrievalReadyImages(strains[0])
  const singleHasNewMedia = hasNewMediaImages(strains[0])

  const runRetrieval = useCallback(async (config: RetrievalConfig) => {
    const queryImageId = retrievalReadyImages[0]?.id
    if (!queryImageId || retrievalSubmitting) return

    setFeatureProgress({ completed: 0, total: retrievalReadyImages.length, current: 'Preparing retrieval images' })
    try {
      for (const [index, image] of retrievalReadyImages.entries()) {
        setFeatureProgress({ completed: index, total: retrievalReadyImages.length, current: image.fileName })
        if (image.media) await updateImageMedia(image.id, image.media)
        if (image.featureStatus !== 'done') {
          await reindexImage(image.id)
        }
      }
    } catch (err) {
      toast.apiError(err, 'Failed to prepare images for retrieval')
      return
    }

    setFeatureProgress({ completed: retrievalReadyImages.length, total: retrievalReadyImages.length, current: 'KNN retrieval' })
    setStep('processing')
    setSubmittedConfig(config)
    lastSubmittedConfig.current = config
    queryClient.removeQueries({ queryKey: ['retrieval-results'] })
    startRetrieval.mutate(
      {
        image_id: queryImageId,
        image_ids: retrievalReadyImages.map((image) => image.id),
        k: config.k,
        aggregation: config.aggregation,
        media_strategy: 'same_media',
      },
      {
        onSuccess: (data) => {
          setJobId(data.job_id)
          if (jobStatus.data?.status === 'completed') {
            setStep('results')
          }
        },
      },
    )
  }, [jobStatus.data?.status, queryClient, retrievalReadyImages, retrievalSubmitting, startRetrieval, toast])

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
          <div className="flex flex-wrap items-center gap-2">
            <Tabs defaultValue={isBatch ? 'batch' : 'single'} className="w-auto">
              <TabsList>
                <TabsTrigger value="single" active={!isBatch} onClick={() => { setIsBatch(false); setActiveStrain(0) }}><FlaskConical className="h-4 w-4" /> Single Strain</TabsTrigger>
                {isOwner && <TabsTrigger value="batch" active={isBatch} onClick={() => { setIsBatch(true); setActiveStrain(0) }}><Images className="h-4 w-4" /> Batch processing</TabsTrigger>}
              </TabsList>
            </Tabs>
            {isBatch && <Button variant="outline" size="sm" onClick={addStrain}><Plus className="h-4 w-4" /> Add Strain</Button>}
            <Button variant="outline" size="sm" onClick={isBatch ? loadSampleBatch : loadSampleSingle}><Download className="h-4 w-4" /> Load Sample</Button>
            <div className="ml-auto text-xs text-muted-foreground">{strains.length} strain(s) · {totalImages} image(s)</div>
          </div>

          {isBatch && isOwner && (
            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="font-heading text-base">Batch Upload (ZIP)</CardTitle>
                <CardDescription>
                  Download the template zip with AGENTS.md instructions, organize images by strain, re-zip, and upload.
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <ol className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                  <li className="rounded-md border border-border p-3"><b className="text-foreground">1. Download template</b><br />Includes AGENTS.md and metadata examples.</li>
                  <li className="rounded-md border border-border p-3"><b className="text-foreground">2. Run local agent</b><br />Ask your coding agent to follow AGENTS.md, map strain folders, then zip the folder.</li>
                  <li className="rounded-md border border-border p-3"><b className="text-foreground">3. Upload ZIP</b><br />MycoAI imports images, segments, then prepares retrieval-ready confirmation data.</li>
                </ol>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => downloadTemplateZip()}>
                    <Download className="h-4 w-4" /> Download Batch Template ZIP
                  </Button>
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
                      <span className="text-sm text-muted-foreground">Uploading ZIP… {batchProgress?.upload.completed ?? 0}/{batchProgress?.upload.total ?? 0} images queued</span>
                      {batchProgress && <span className="text-xs text-muted-foreground">Segment {batchProgress.segmentation.completed}/{batchProgress.segmentation.total} · Feature {batchProgress.feature_extraction.completed}/{batchProgress.feature_extraction.total}</span>}
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
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={zipResult.failed > 0 ? 'warning' : 'success'}>
                        {zipResult.successful} successful, {zipResult.failed} failed
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {zipResult.total} total images in batch
                      </span>
                      {batchProgress && (
                        <span className="text-xs text-muted-foreground">
                          Upload {batchProgress.upload.completed}/{batchProgress.upload.total} · Segmentation {batchProgress.segmentation.completed}/{batchProgress.segmentation.total} · Feature extraction {batchProgress.feature_extraction.completed}/{batchProgress.feature_extraction.total}
                        </span>
                      )}
                    </div>
                    {((batchProgress?.images.length ?? 0) > 0 || zipResult.results.length > 0) && (
                      <div className="max-h-36 overflow-auto text-xs">
                        <table className="w-full">
                          <thead>
                            <tr className="text-left text-muted-foreground">
                              <th className="pb-1 pr-2">Strain</th>
                              <th className="pb-1 pr-2">Media</th>
                              <th className="pb-1 pr-2">Status</th>
                              <th className="pb-1">File</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(batchProgress?.images ?? zipResult.results.map((r) => ({ ...r, status: 'uploaded' }))).map((r, i) => (
                              <tr key={`${r.image_id ?? 'no-id'}-${r.filename}-${i}`} className="border-t border-border">
                                <td className="py-1 pr-2">{r.strain}</td>
                                <td className="py-1 pr-2">{r.media}</td>
                                <td className="py-1 pr-2">{r.status}</td>
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
          )}

          {strains.length > 0 && (
            <div className="flex flex-wrap gap-2 border-b border-border pb-2">
              {(isBatch ? strains : [strains[0]]).map((strain, index) => (
                <button
                  key={`${strain?.strain || 'unnamed'}-${index}`}
                  onClick={() => setActiveStrain(index)}
                  className={`rounded-t-md px-3 py-2 text-sm transition-colors cursor-pointer ${activeStrain === index ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
                >
                  {strain?.strain || `${title} ${index + 1}`} <span className="text-xs opacity-75">({strain?.images?.length ?? 0})</span>
                </button>
              ))}
            </div>
          )}

          {current && (
            <Card>
              <CardHeader className="p-4 pb-3">
                <div className="grid gap-3 lg:grid-cols-[280px_1fr_auto] lg:items-end">
                  <div className="space-y-1">
                    <Label htmlFor="strain" className="text-xs">Strain Identifier</Label>
                    <Input id="strain" className="h-9" placeholder="e.g. T379" value={current.strain} onChange={(e) => updateStrain(activeStrain, { strain: e.target.value })} />
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>Compact metadata shown per card. Bigger plate preview helps catch wrong media/image before segmentation.</div>
                    {uploadProgress && <div>Upload {uploadProgress.completed}/{uploadProgress.total}{uploadProgress.current ? ` · ${uploadProgress.current}` : ''}</div>}
                    {segmentProgress && <div>Segmentation {segmentProgress.completed}/{segmentProgress.total}{segmentProgress.current ? ` · ${segmentProgress.current}` : ''}</div>}
                    {featureProgress && <div>Feature extraction {featureProgress.completed}/{featureProgress.total}{featureProgress.current ? ` · ${featureProgress.current}` : ''}</div>}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => addImage(activeStrain)}><Plus className="h-4 w-4" /> Add Image</Button>
                    <Button variant="default" size="sm" disabled={autoSegmenting || current.images.length === 0} onClick={runAutoSegment}>
                      {autoSegmenting ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Segmenting {segmentProgress?.completed ?? 0}/{segmentProgress?.total ?? 0}</>
                      ) : (
                        <><Images className="h-4 w-4" /> Upload & segment</>
                      )}
                    </Button>
                    {isBatch && <Button variant="ghost" size="sm" className="text-destructive" onClick={() => removeStrain(activeStrain)}><Trash2 className="h-4 w-4" /></Button>}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                {current.images.length === 0 ? (
                  <button className="flex h-64 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-sm text-muted-foreground hover:border-primary" onClick={() => addImage(activeStrain)}>
                    <Images className="mb-2 h-8 w-8" /> Add first image for this strain
                  </button>
                 ) : (
                   <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                     {current.images.map((image) => (
                        <ImageMetaCard
                          key={image.id}
                          image={image}
                          mediaItems={mediaItems}
                          onUpdate={(field) => updateImage(activeStrain, image.id, field)}
                          onRemove={() => removeImage(activeStrain, image.id)}
                        />

                     ))}
                   </div>
                 )}
                {singleHasNewMedia && !isBatch && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-warning/20 bg-warning/10 p-3 text-sm text-foreground">
                    <Badge variant="warning">New media</Badge>
                    <p>New/other media images upload and display normally, but retrieval ignores them. Research-verified flow only queries same-media indexed images.</p>
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
              <CardTitle className="font-heading">Segmentation Confirmation</CardTitle>
              <CardDescription>
                {isBatch ? `${strains[activeStrain]?.strain || `Strain ${activeStrain + 1}`}` : `${strains[0]?.strain || 'Single strain'}`} · review all images, confirm segments, then feature extraction status updates before results
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-4 pt-0">
              {featureProgress && <div className="text-xs text-muted-foreground">Feature extraction {featureProgress.completed}/{featureProgress.total}{featureProgress.current ? ` · ${featureProgress.current}` : ''}</div>}
              {currentSegments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No images for this strain.</p>
              ) : (
                <>
                  <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={currentSegments.length > 0 && currentSegments.every((image) => image.selected)}
                        onChange={(e) => setSelectAllUploaded(activeStrain, e.target.checked)}
                      />
                      <span>Select all uploaded</span>
                    </label>
                    <Badge variant="secondary" className="ml-auto">{getConfirmableImages(strains[activeStrain]).length} selected</Badge>
                  </div>
                  {currentSegments.map((image) => (
                    <SegmentCard
                      key={image.id}
                      image={image}
                      onUpdateBbox={(si, bb) => updateYoloBbox(activeStrain, image.id, si, bb)}
                      onAddBbox={(bb) => addYoloBbox(activeStrain, image.id, bb)}
                      onRemoveBbox={(si) => removeYoloBbox(activeStrain, image.id, si)}
                      onSave={() => void persistSegments(activeStrain, image.id)}
                      onConfirm={() => void confirmImage(activeStrain, image.id)}
                      onToggleSelected={(selected) => toggleImageSelected(activeStrain, image.id, selected)}
                      saving={savingImageId === image.id}
                      confirming={confirmingImageId === image.id}
                    />
                  ))}
                </>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={runAutoSegment} disabled={autoSegmenting || currentSegments.length === 0}>
                  Segment All
                </Button>
                <Button variant="default" size="sm" onClick={() => void runStrainReindex()} disabled={reindexingStrain || currentSegments.length === 0}>
                  {reindexingStrain ? <><Loader2 className="h-4 w-4 animate-spin" /> Extracting...</> : 'Extract all'}
                </Button>
                <Badge variant="secondary" className="ml-auto">{totalSegments} total segments</Badge>
              </div>
              <p className="text-xs text-muted-foreground">Confirm view only validates bounding boxes and image status. Retrieval extracts only remaining unindexed segments.</p>
            </CardContent>
          </Card>
        </div>
      )}

      {step === 'results' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card px-4 py-3">
            <span className="text-sm font-medium">KNN Configuration</span>
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <label className="text-xs text-muted-foreground whitespace-nowrap">K: {retrievalConfig.k}</label>
              <input
                type="range"
                min={1}
                max={30}
                step={1}
                value={retrievalConfig.k}
                onChange={(e) => setRetrievalConfig((prev) => ({ ...prev, k: Number(e.target.value) }))}
                className="flex-1 h-2 accent-primary cursor-pointer"
              />
              <span className="font-mono text-xs w-6 text-right">{retrievalConfig.k}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Aggregation:</span>
               <button
                 type="button"
                 aria-label="freq_strength"
                 onClick={() => setRetrievalConfig((prev) => ({ ...prev, aggregation: 'freq_strength' }))}
                 className={`rounded-full px-3 py-1 text-xs font-medium cursor-pointer ${retrievalConfig.aggregation === 'freq_strength' ? 'bg-primary text-primary-foreground' : 'border border-border bg-card text-muted-foreground hover:text-foreground'}`}
               >
                 freq_strength
               </button>
               <button
                 type="button"
                 aria-label="weighted"
                 onClick={() => setRetrievalConfig((prev) => ({ ...prev, aggregation: 'weighted' }))}
                 className={`rounded-full px-3 py-1 text-xs font-medium cursor-pointer ${retrievalConfig.aggregation === 'weighted' ? 'bg-primary text-primary-foreground' : 'border border-border bg-card text-muted-foreground hover:text-foreground'}`}
               >
                 weighted
               </button>
            </div>
            <Button size="sm" disabled={!hasPendingConfigChanges || retrievalSubmitting} onClick={() => runRetrieval(retrievalConfig)}>
              Apply Retrieval Config
            </Button>
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
                </CardContent>
              </Card>
               <ResultDetail strain={activeResult?.strain || 'Strain'} images={activeResult?.images ?? []} knnK={submittedConfig.k} aggMethod={submittedConfig.aggregation} rankings={jobResults.data?.rankings} queriedImages={jobResults.data?.queried_images} threshold={jobResults.data?.threshold} />

            </div>
          ) : (
            <ResultDetail strain={strains[0]?.strain || 'Single strain'} images={strains[0]?.images ?? []} knnK={submittedConfig.k} aggMethod={submittedConfig.aggregation} rankings={jobResults.data?.rankings} queriedImages={jobResults.data?.queried_images} threshold={jobResults.data?.threshold} />
          )}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" disabled={step === 'upload' || step === 'processing'} onClick={() => setStep(step === 'results' ? 'segmentation' : 'upload')}>Previous</Button>
        <Button
          onClick={() => {
            if (step === 'upload') {
              void runAutoSegment()
              return
            }
            if (step === 'segmentation') {
              runRetrieval(retrievalConfig)
            }
          }}
          disabled={step === 'results' || step === 'processing' || (step === 'segmentation' && retrievalReadyImages.length === 0)}
        >
          {step === 'upload' ? 'Segment All' : step === 'processing' ? 'Running...' : 'Run Retrieval'} <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

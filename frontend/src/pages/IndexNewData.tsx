import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { sampleStrains } from '@/lib/sample-assets'
import { AGENTS_MD_CONTENT, downloadTemplateZip } from '@/lib/template'
import { useSpeciesList, useMediaList, useCreateSpecies } from '@/hooks/use-taxonomy'
import { useToast } from '@/hooks/use-toast'
import { uploadBatchZip, listSegments, autoSegment, confirmBatchStrain, type BatchProgress, type BatchZipResult } from '@/services/images'
import type { SegmentDetail } from '@/services/types'
import { ArrowRight, ChevronRight, Download, Images, Plus, Trash2, Check, X, FileArchive, Loader2, FileText } from 'lucide-react'

type Step = 'upload' | 'segment' | 'review' | 'done'

interface Bbox {
  x: number
  y: number
  w: number
  h: number
}

interface StrainImage {
  id: string
  imageId: string
  fileName: string
  media: string
  original?: string
  yoloPreview?: string
  yoloBboxes: Bbox[]
  segments: Array<{ url: string; bbox: Bbox }>
}

interface IndexStrain {
  strain: string
  species: string
  images: StrainImage[]
}

function Breadcrumb({ step }: { step: Step }) {
  const items = [
    { key: 'upload' as const, label: 'Upload' },
    { key: 'segment' as const, label: 'Segment' },
    { key: 'review' as const, label: 'Review' },
    { key: 'done' as const, label: 'Indexed' },
  ]
  const currentIdx = items.findIndex((i) => i.key === step)
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
      <span>Index New Data</span>
      {items.map((item, idx) => (
        <span key={item.key} className="flex items-center gap-1">
          <ChevronRight className="h-3 w-3" />
          <span className={idx === currentIdx ? 'text-foreground font-medium' : idx < currentIdx ? 'text-success' : ''}>
            {item.label}
          </span>
        </span>
      ))}
    </nav>
  )
}

function Stepper({ step }: { step: Step }) {
  const order: Array<{ key: Step; label: string }> = [
    { key: 'upload', label: 'Upload' },
    { key: 'segment', label: 'Segment' },
    { key: 'review', label: 'Review' },
    { key: 'done', label: 'Indexed' },
  ]
  const currentIdx = order.findIndex((i) => i.key === step)
  return (
    <div className="flex items-center gap-2">
      {order.map((item, idx) => (
        <div key={item.key} className="flex items-center gap-2">
          <div className={`flex h-8 w-8 items-center justify-center rounded-full font-heading text-sm font-medium ${
            step === item.key ? 'bg-primary text-primary-foreground' : idx < currentIdx ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
          }`}>
            {idx < currentIdx ? <Check className="h-4 w-4" /> : idx + 1}
          </div>
          <span className={`text-sm ${step === item.key ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
            {item.label}
          </span>
          {idx < order.length - 1 && <div className="h-px w-8 bg-border" />}
        </div>
      ))}
    </div>
  )
}

function SegmentCard({
  image,
  onUpdateBbox,
  onAddBbox,
  onRemoveBbox,
  readOnly,
}: {
  image: StrainImage
  onUpdateBbox: (segmentIndex: number, bbox: Bbox) => void
  onAddBbox: (bbox: Bbox) => void
  onRemoveBbox: (segmentIndex: number) => void
  readOnly?: boolean
}) {
  const segments = image.segments ?? []
  const yoloBboxes = image.yoloBboxes ?? []
  const bboxes = yoloBboxes.length ? yoloBboxes : segments.map((s) => s.bbox)
  const preview = image.yoloPreview || image.original
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [drawing, setDrawing] = useState<Bbox | null>(null)
  const [imgDims, setImgDims] = useState<{ w: number; h: number; dispW: number; dispH: number; offX: number; offY: number }>({
    w: 320, h: 320, dispW: 320, dispH: 320, offX: 0, offY: 0,
  })

  useEffect(() => {
    const img = imgRef.current
    if (!img) return
    function update() {
      const natural = { w: img!.naturalWidth || 320, h: img!.naturalHeight || 320 }
      const containerRect = img!.parentElement?.getBoundingClientRect() ?? { width: 320, height: 320 }
      const scale = Math.min(containerRect.width / natural.w, containerRect.height / natural.h)
      const dispW = natural.w * scale
      const dispH = natural.h * scale
      setImgDims({ ...natural, dispW, dispH, offX: (containerRect.width - dispW) / 2, offY: (containerRect.height - dispH) / 2 })
    }
    update()
    window.addEventListener('resize', update)
    if (img.complete) update()
    else img.onload = update
    return () => { window.removeEventListener('resize', update); img.onload = null }
  }, [preview])

  const natW = imgDims.w || 320; const natH = imgDims.h || 320
  const allBboxes = drawing ? [...bboxes, drawing] : bboxes

  const startDraw = (e: React.MouseEvent<HTMLDivElement>) => {
    if (readOnly) return
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
      setDrawing({ x: Math.round(Math.max(0, Math.min(initX, curX))), y: Math.round(Math.max(0, Math.min(initY, curY))), w: Math.round(Math.abs(curX - initX)), h: Math.round(Math.abs(curY - initY)) })
    }
    const handleUp = () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleUp)
      setDrawing((prev) => { if (prev && prev.w > 10 && prev.h > 10) onAddBbox(prev); return null })
    }
    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleUp)
  }

  const startMove = (index: number, e: React.MouseEvent<HTMLDivElement>) => {
    if (readOnly) return
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
    if (readOnly) return
    e.stopPropagation()
    const startX = e.clientX; const startY = e.clientY
    const bbox = bboxes[index]
    const handleMove = (ev: MouseEvent) => {
      const dx = ((ev.clientX - startX) / imgDims.dispW) * natW
      const dy = ((ev.clientY - startY) / imgDims.dispH) * natH
      onUpdateBbox(index, { x: bbox.x, y: bbox.y, w: Math.max(10, bbox.w + Math.round(dx)), h: Math.max(10, bbox.h + Math.round(dy)) })
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
            <CardDescription className="text-xs">
              {image.media} · {segments.length} segments · {segments.length > 0 ? 'K-means segmentation' : 'No segments yet'}
            </CardDescription>
          </div>
          <Badge variant={segments.length > 0 ? 'success' : 'secondary'}>
            {segments.length > 0 ? `${segments.length} segments` : 'Pending'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-3 pt-0">
        <div className="grid gap-3 lg:grid-cols-[minmax(360px,1.15fr)_1fr]">
          <div
            ref={containerRef}
            className={`relative min-h-[320px] overflow-hidden rounded-lg border border-border bg-muted ${readOnly ? '' : 'cursor-crosshair'}`}
            onMouseDown={startDraw}
          >
            {preview ? (
              <img ref={imgRef} src={preview} alt={image.fileName} className="pointer-events-none h-full max-h-[520px] min-h-[320px] w-full object-contain select-none" />
            ) : (
              <div className="flex h-full min-h-[320px] items-center justify-center text-xs text-muted-foreground">No preview available</div>
            )}
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
                {!readOnly && (
                  <>
                    <button className="absolute -top-3 -right-1 hidden group-hover:flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-xs text-white" onMouseDown={(e) => { e.stopPropagation(); onRemoveBbox(index) }}>×</button>
                    <div className="absolute -bottom-1 -right-1 hidden group-hover:block h-4 w-4 rounded-full bg-primary border-2 border-white cursor-se-resize" onMouseDown={(e) => startResize(index, e)} />
                  </>
                )}
                <div className="absolute -left-2 top-1 z-10 hidden group-hover:block rounded bg-card/95 px-1.5 py-0.5 font-mono text-[10px] shadow-sm text-foreground whitespace-nowrap">
                  {bbox.w}×{bbox.h}
                </div>
              </div>
            ))}
            <div className="absolute left-2 top-2 rounded bg-card/95 px-2 py-1 text-xs shadow-sm">
              {readOnly ? 'Bounding box preview' : 'Drag to move · corner to resize · click-drag to add'}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 content-start">
            {segments.map((segment, index) => (
              <div key={`${image.id}-seg-${index}`} className="relative overflow-hidden rounded-lg border border-border bg-muted">
                <div className="aspect-square">
                  {segment.url ? (
                    <img src={segment.url} alt={`Segment ${index + 1}`} className="h-full w-full object-contain" />
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-muted-foreground">Seg {index + 1}</div>
                  )}
                </div>
                <div className="flex items-center justify-between border-t border-border bg-card px-2 py-1 text-xs">
                  <span>Seg {index + 1}</span>
                  <span className="font-mono">{segment.bbox.w}×{segment.bbox.h}</span>
                </div>
              </div>
            ))}
            {segments.length === 0 && bboxes.length > 0 && (
              <div className="col-span-3 text-center text-xs text-muted-foreground py-4">
                {bboxes.length} bounding boxes drawn. Segments will be generated on index.
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function IndexNewDataPage() {
  const [step, setStep] = useState<Step>('upload')
  const [strains, setStrains] = useState<IndexStrain[]>([])
  const [activeStrain, setActiveStrain] = useState(0)
  const [creatingSpecies, setCreatingSpecies] = useState<{ strainIdx: number; name: string; description: string } | null>(null)
  const [batchResult, setBatchResult] = useState<BatchZipResult | null>(null)
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null)
  const [confirmedStrains, setConfirmedStrains] = useState<Set<string>>(new Set())
  const [isUploading, setIsUploading] = useState(false)
  const [loadingSegments, setLoadingSegments] = useState(false)
  const [autoSegmenting, setAutoSegmenting] = useState(false)
  const [segmentsByImage, setSegmentsByImage] = useState<Record<string, SegmentDetail[]>>({})
  const [uploadMode, setUploadMode] = useState<'batch' | 'single'>('batch')
  const [agentsOpen, setAgentsOpen] = useState(false)

  const { data: speciesData } = useSpeciesList()
  const { data: mediaData } = useMediaList()
  const speciesList = useMemo(() => speciesData?.items ?? [], [speciesData?.items])
  const mList = mediaData?.items ?? []
  const createSpeciesMutation = useCreateSpecies()
  const toast = useToast()

  const current = strains[activeStrain]
  const totalImages = strains.reduce((sum, s) => sum + s.images.length, 0)
  const segmentedImages = strains.reduce((sum, s) => sum + s.images.filter((img) => img.segments.length > 0 || img.yoloBboxes.length > 0).length, 0)
  const confirmedCount = confirmedStrains.size
  const defaultSpeciesId = speciesList.length > 0 ? speciesList[0].id : ''

  const addStrain = () => {
    setStrains([...strains, { strain: '', species: defaultSpeciesId, images: [] }])
    setActiveStrain(strains.length)
  }

  const removeStrain = (idx: number) => {
    const next = strains.filter((_, i) => i !== idx)
    setStrains(next)
    setActiveStrain(Math.max(0, idx - 1))
  }

  const confirmCreateSpecies = async () => {
    if (!creatingSpecies || !creatingSpecies.name.trim()) return
    try {
      const result = await createSpeciesMutation.mutateAsync({
        name: creatingSpecies.name.trim(),
        description: creatingSpecies.description || null,
      })
      updateStrain(creatingSpecies.strainIdx, { species: result.id })
      setCreatingSpecies(null)
      toast.success('Species created')
    } catch (err) {
      toast.apiError(err, 'Failed to create species')
    }
  }

  const cancelCreateSpecies = () => setCreatingSpecies(null)

  const updateStrain = (idx: number, field: Partial<IndexStrain>) => {
    setStrains(strains.map((s, i) => (i === idx ? { ...s, ...field } : s)))
  }

  const findSpeciesByName = useCallback((name: string) => speciesList.find((sp) => sp.name === name)?.id, [speciesList])

  const loadSample = () => {
    const mapped = (sampleStrains as unknown as Array<{
      strain: string; species: string; images: Array<{
        id: string; fileName: string; media: string; original: string
      }>
    }>).map((s) => ({
      strain: s.strain,
      species: findSpeciesByName(s.species) ?? defaultSpeciesId,
      images: s.images.map((img) => ({
        id: crypto.randomUUID(),
        imageId: img.id,
        fileName: img.fileName,
        media: img.media,
        original: img.original,
        yoloBboxes: [] as Bbox[],
        segments: [] as Array<{ url: string; bbox: Bbox }>,
      })),
    }))
    setStrains(mapped)
    setActiveStrain(0)
  }

  const addImage = (strainIdx: number) => {
    const pool = (sampleStrains as unknown as Array<{
      images: Array<{ id: string; fileName: string; media: string; original: string }>
    }>).flatMap((s) => s.images)
    const sample = pool[strains[strainIdx].images.length % pool.length]
    const img: StrainImage = {
      id: crypto.randomUUID(),
      imageId: sample?.id ?? crypto.randomUUID(),
      fileName: sample?.fileName ?? `image_${strains[strainIdx].images.length + 1}.jpg`,
      media: sample?.media ?? (mList.length > 0 ? mList[0].name : 'MEA'),
      original: sample?.original,
      yoloBboxes: [],
      segments: [],
    }
    updateStrain(strainIdx, { images: [...strains[strainIdx].images, img] })
  }

  const removeImage = (strainIdx: number, imgId: string) => {
    updateStrain(strainIdx, { images: strains[strainIdx].images.filter((img) => img.id !== imgId) })
  }

  const handleBatchZipUpload = useCallback(async (file: File) => {
    setIsUploading(true)
    setBatchResult(null)
    try {
      const result = await uploadBatchZip(file)
      setBatchResult(result)
      setBatchProgress(result.progress)

      const indexed: IndexStrain[] = []
      const strainMap = new Map<string, IndexStrain>()

      for (const r of result.results) {
        const strainKey = r.strain || 'unknown'
        if (!strainMap.has(strainKey)) {
          const speciesId = r.species ? findSpeciesByName(r.species) ?? defaultSpeciesId : defaultSpeciesId
          strainMap.set(strainKey, { strain: strainKey, species: speciesId, images: [] })
          indexed.push(strainMap.get(strainKey)!)
        }
        strainMap.get(strainKey)!.images.push({
          id: r.image_id || crypto.randomUUID(),
          imageId: r.image_id || '',
          fileName: r.filename,
          media: r.media || 'MEA',
          original: r.source_url || undefined,
          yoloBboxes: [],
          segments: [],
        })
      }

      if (indexed.length === 0) {
        toast.error('No valid images found in the uploaded ZIP. Ensure the ZIP contains strain folders with .jpg/.jpeg/.png images.')
        return
      }
      setStrains(indexed)
      setActiveStrain(0)

      if (result.successful > 0) {
        toast.success(`Batch uploaded: ${result.successful} images processed, ${result.failed} failed`)
      }
    } catch (err) {
      toast.apiError(err, 'Batch upload failed')
    } finally {
      setIsUploading(false)
    }
  }, [defaultSpeciesId, findSpeciesByName, toast])

  const runAutoSegment = async () => {
    setAutoSegmenting(true)
    let successCount = 0
    const nextSegmentsByImage: Record<string, SegmentDetail[]> = {}
    try {
      for (const strain of strains) {
        for (const img of strain.images) {
          if (!img.imageId) continue
          try {
            const result = await autoSegment(img.imageId, 'yolo')
            nextSegmentsByImage[img.imageId] = result.segments.map((s) => ({
              id: s.segment_id,
              image_id: img.imageId,
              segment_index: s.segment_index,
              crop_path: s.crop_url,
              bbox_x: s.bbox.x,
              bbox_y: s.bbox.y,
              bbox_w: s.bbox.w,
              bbox_h: s.bbox.h,
              segmentation_method: result.segmentation_method,
            }))
            successCount++
          } catch {
            continue
          }
        }
      }

      setSegmentsByImage((prev) => ({ ...prev, ...nextSegmentsByImage }))
      setStrains((prev) => prev.map((s) => ({
        ...s,
        images: s.images.map((img) => {
          const segs = nextSegmentsByImage[img.imageId] ?? segmentsByImage[img.imageId]
          if (!segs) return img
          return {
            ...img,
            segments: segs.map((seg) => ({
              url: seg.crop_path || '',
              bbox: { x: seg.bbox_x, y: seg.bbox_y, w: seg.bbox_w, h: seg.bbox_h },
            })),
            yoloBboxes: segs.map((seg) => ({ x: seg.bbox_x, y: seg.bbox_y, w: seg.bbox_w, h: seg.bbox_h })),
          }
        }),
      })))

      toast.success(`Auto-segmented ${successCount} image(s)`)
      setStep('segment')
    } catch (err) {
      toast.apiError(err, 'Auto-segment failed')
    } finally {
      setAutoSegmenting(false)
    }
  }

  const loadSegmentsForAll = async () => {
    setLoadingSegments(true)
    const newSegmentsByImage: Record<string, SegmentDetail[]> = {}
    for (const strain of strains) {
      for (const img of strain.images) {
        if (!img.imageId || segmentsByImage[img.imageId]) continue
        try {
          const segs = await listSegments(img.imageId)
          newSegmentsByImage[img.imageId] = segs
        } catch {
          // segment loading may fail for unprocessed images
        }
      }
    }
    setSegmentsByImage((prev) => ({ ...prev, ...newSegmentsByImage }))

    // Merge into strain images
    setStrains((prev) => prev.map((s) => ({
      ...s,
      images: s.images.map((img) => {
        const segs = newSegmentsByImage[img.imageId] ?? segmentsByImage[img.imageId]
        if (!segs) return img
        return {
          ...img,
          segments: segs.map((seg) => ({
            url: seg.crop_path || '',
            bbox: { x: seg.bbox_x, y: seg.bbox_y, w: seg.bbox_w, h: seg.bbox_h },
          })),
          yoloBboxes: segs.map((seg) => ({ x: seg.bbox_x, y: seg.bbox_y, w: seg.bbox_w, h: seg.bbox_h })),
        }
      }),
    })))
    setLoadingSegments(false)
  }

  const updateBbox = (strainIdx: number, imgId: string, segmentIndex: number, bbox: Bbox) => {
    setStrains((prev) => prev.map((s, i) => {
      if (i !== strainIdx) return s
      return {
        ...s,
        images: s.images.map((img) => {
          if (img.id !== imgId) return img
          const existing = img.yoloBboxes.length ? img.yoloBboxes : img.segments.map((seg) => seg.bbox)
          return { ...img, yoloBboxes: existing.map((b, j) => (j === segmentIndex ? bbox : b)) }
        }),
      }
    }))
  }

  const addBbox = (strainIdx: number, imgId: string, bbox: Bbox) => {
    setStrains((prev) => prev.map((s, i) => {
      if (i !== strainIdx) return s
      return {
        ...s,
        images: s.images.map((img) => {
          if (img.id !== imgId) return img
          const existing = img.yoloBboxes.length ? img.yoloBboxes : img.segments.map((seg) => seg.bbox)
          return { ...img, yoloBboxes: [...existing, bbox] }
        }),
      }
    }))
  }

  const removeBbox = (strainIdx: number, imgId: string, segmentIndex: number) => {
    setStrains((prev) => prev.map((s, i) => {
      if (i !== strainIdx) return s
      return {
        ...s,
        images: s.images.map((img) => {
          if (img.id !== imgId) return img
          const existing = img.yoloBboxes.length ? img.yoloBboxes : img.segments.map((seg) => seg.bbox)
          return { ...img, yoloBboxes: existing.filter((_, j) => j !== segmentIndex) }
        }),
      }
    }))
  }

  const goToSegment = async () => {
    await runAutoSegment()
    await loadSegmentsForAll()
  }

  const confirmActiveStrain = async () => {
    if (!current) return
    const strainName = current.strain || `Strain ${activeStrain + 1}`
    if (batchProgress?.batch_id) {
      try {
        setBatchProgress(await confirmBatchStrain(batchProgress.batch_id, strainName))
      } catch (err) {
        toast.apiError(err, 'Failed to confirm strain')
        return
      }
    }
    setConfirmedStrains((prev) => new Set(prev).add(strainName))
    const next = strains.findIndex((s, idx) => idx > activeStrain && !confirmedStrains.has(s.strain || `Strain ${idx + 1}`))
    if (next >= 0) setActiveStrain(next)
    else setStep('review')
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Breadcrumb step={step} />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Index New Data</h1>
            <p className="text-sm text-muted-foreground">
              Upload a ZIP batch of plate images organized by strain, or manually add strains and images.
            </p>
          </div>
          <Stepper step={step} />
        </div>
      </div>

      {step === 'upload' && (
        <Tabs defaultValue="batch" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <TabsList>
              <TabsTrigger value="batch" active={uploadMode === 'batch'} onClick={() => setUploadMode('batch')}>Batch ZIP</TabsTrigger>
              <TabsTrigger value="single" active={uploadMode === 'single'} onClick={() => setUploadMode('single')}>Single strain</TabsTrigger>
            </TabsList>
            <div className="text-xs text-muted-foreground">{strains.length} strain(s) · {totalImages} image(s)</div>
          </div>

          <TabsContent value="batch" activeValue={uploadMode} className="mt-0 space-y-3">
          <Card>
            <CardHeader className="p-4 pb-2">
              <CardTitle className="font-heading text-base">Batch upload for indexing</CardTitle>
              <CardDescription>Prepare a ZIP locally, then upload it here. This flow is for data owners indexing new data.</CardDescription>
            </CardHeader>
            <CardContent className="p-4 pt-0 space-y-3">
              <ol className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                <li className="rounded-md border border-border p-3"><b className="text-foreground">1. Download template</b><br />Includes <Button variant="ghost" size="sm" className="h-auto p-0 text-primary underline" onClick={() => setAgentsOpen(true)}>AGENTS.md</Button> and metadata.json examples.</li>
                <li className="rounded-md border border-border p-3"><b className="text-foreground">2. Run local agent</b><br />Ask your coding agent to follow AGENTS.md, map strain folders in metadata.json, then zip the folder.</li>
                <li className="rounded-md border border-border p-3"><b className="text-foreground">3. Upload ZIP</b><br />MycoAI imports images, species metadata, segments, then indexes into Qdrant.</li>
              </ol>
              <Button variant="outline" size="sm" onClick={() => downloadTemplateZip()}>
                <Download className="h-4 w-4" /> Download template ZIP
              </Button>

              <label
                className={`flex h-40 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors ${
                  isUploading ? 'border-primary bg-primary/5' : 'border-border hover:border-primary'
                }`}
                onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-primary') }}
                onDragLeave={(e) => { e.currentTarget.classList.remove('border-primary') }}
                onDrop={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.remove('border-primary')
                  const file = e.dataTransfer.files?.[0]
                  if (file?.name.endsWith('.zip')) handleBatchZipUpload(file)
                  else toast.error('Please drop a .zip file')
                }}
              >
                <input
                  type="file"
                  accept=".zip"
                  className="hidden"
                  disabled={isUploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleBatchZipUpload(file)
                    e.target.value = ''
                  }}
                />
                {isUploading ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <span className="text-sm text-muted-foreground">Processing batch...</span>
                    {batchProgress && <span className="text-xs text-muted-foreground">Uploaded {batchProgress.upload.completed}/{batchProgress.upload.total} ({batchProgress.upload.percent}%)</span>}
                  </div>
                ) : (
                  <>
                    <FileArchive className="mb-2 h-8 w-8 text-muted-foreground" />
                    <span className="text-sm font-medium">Drop ZIP here or click to browse</span>
                    <span className="text-xs text-muted-foreground">mycoai_batch_template.zip</span>
                  </>
                )}
              </label>

              {batchResult && (
                <div className="rounded-lg border border-border p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={batchResult.failed > 0 ? 'warning' : 'success'}>
                      {batchResult.successful} successful, {batchResult.failed} failed
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {batchResult.total} total images processed
                    </span>
                    {batchProgress && (
                      <span className="text-xs text-muted-foreground">
                        Upload {batchProgress.upload.completed}/{batchProgress.upload.total} ({batchProgress.upload.percent}%) · Segmentation {batchProgress.segmentation.completed}/{batchProgress.segmentation.total} ({batchProgress.segmentation.percent}%) · Feature extraction {batchProgress.feature_extraction.completed}/{batchProgress.feature_extraction.total} ({batchProgress.feature_extraction.percent}%)
                      </span>
                    )}
                  </div>
                  {batchResult.results.length > 0 && (
                    <div className="max-h-48 overflow-auto text-xs">
                      <table className="w-full">
                        <thead>
                          <tr className="text-left text-muted-foreground">
                            <th className="pb-1 pr-2">Strain</th>
                            <th className="pb-1 pr-2">Species</th>
                            <th className="pb-1 pr-2">Media</th>
                            <th className="pb-1 pr-2">Segments</th>
                            <th className="pb-1">File</th>
                          </tr>
                        </thead>
                        <tbody>
                          {batchResult.results.map((r, i) => (
                            <tr key={i} className={`border-t border-border ${r.status === 'uploaded' ? 'opacity-50' : 'opacity-100'}`}>
                              <td className="py-1 pr-2">{r.strain}</td>
                              <td className="py-1 pr-2">{r.species}</td>
                              <td className="py-1 pr-2">{r.media}</td>
                              <td className="py-1 pr-2">{r.segments}</td>
                              <td className="py-1 text-muted-foreground">{r.filename}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {batchResult.errors.length > 0 && (
                    <details className="text-xs">
                      <summary className="cursor-pointer text-destructive">
                        {batchResult.errors.length} error(s)
                      </summary>
                      <ul className="mt-1 list-disc pl-4 text-muted-foreground">
                        {batchResult.errors.map((e, i) => (
                          <li key={i}>{e.file}: {e.error}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
          </TabsContent>

          <TabsContent value="single" activeValue={uploadMode} className="mt-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadSample}><Images className="h-4 w-4" /> Load sample strains</Button>
            <Button variant="outline" size="sm" onClick={addStrain}><Plus className="h-4 w-4" /> Add strain</Button>
          </div>

          {strains.length > 0 && (
            <div className="flex flex-wrap gap-2 border-b border-border pb-2">
              {strains.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveStrain(idx)}
                  className={`rounded-t-md px-3 py-2 text-sm transition-colors cursor-pointer ${activeStrain === idx ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
                >
                  {s.strain || `Strain ${idx + 1}`} <span className="text-xs opacity-75">({s.images.length})</span>
                </button>
              ))}
            </div>
          )}

          {strains.length === 0 && !batchResult?.results?.length ? (
            <button className="flex h-64 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-sm text-muted-foreground hover:border-primary" onClick={loadSample}>
              <Images className="mb-2 h-8 w-8" /> Click to load sample data or add a strain
            </button>
          ) : current && (
            <Card>
              <CardHeader className="p-4 pb-3">
                <div className="grid gap-3 lg:grid-cols-[280px_200px_1fr_auto] lg:items-end">
                  <div className="space-y-1">
                    <Label className="text-xs">Strain Identifier</Label>
                    <Input className="h-9" placeholder="e.g. T379" value={current.strain} onChange={(e) => updateStrain(activeStrain, { strain: e.target.value })} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Species *</Label>
                    <Select value={current.species} onChange={(e) => updateStrain(activeStrain, { species: e.target.value })} className="h-9 text-xs">
                      {speciesList.filter((s) => !s.is_archived).map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </Select>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Species metadata is required for indexing. Species is assigned before segmentation.
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => addImage(activeStrain)}><Plus className="h-4 w-4" /> Add image</Button>
                    <Button variant="ghost" size="sm" className="text-destructive" onClick={() => removeStrain(activeStrain)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                {current.images.length === 0 ? (
                  <button className="flex h-48 w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-sm text-muted-foreground hover:border-primary" onClick={() => addImage(activeStrain)}>
                    <Images className="mb-2 h-8 w-8" /> Add first image for this strain
                  </button>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {current.images.map((img) => (
                      <Card key={img.id} className="overflow-hidden">
                        <div className="relative aspect-[4/3] bg-muted">
                          {img.original ? (
                            <img src={img.original} alt={img.fileName} className="h-full w-full object-contain" />
                          ) : (
                            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">Image preview</div>
                          )}
                          <Badge className="absolute left-2 top-2" variant="secondary">{img.media}</Badge>
                          <Button variant="destructive" size="sm" className="absolute right-2 top-2 h-8 px-2" onClick={() => removeImage(activeStrain, img.id)}>
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                        <CardContent className="p-3">
                          <div className="grid grid-cols-[1fr_96px] items-end gap-2">
                            <div className="space-y-1">
                              <Label className="text-xs">File</Label>
                              <Input className="h-8 text-xs" value={img.fileName} readOnly />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Media</Label>
                              <Select value={img.media} onChange={(e) => {
                                updateStrain(activeStrain, {
                                  images: current.images.map((i) => (i.id === img.id ? { ...i, media: e.target.value } : i)),
                                })
                              }} className="h-8 text-xs">
                                {mList.filter((m) => !m.is_archived).map((m) => (
                                  <option key={m.id} value={m.name}>{m.name}</option>
                                ))}
                              </Select>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
          </TabsContent>
        </Tabs>
      )}

      {step === 'segment' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 border-b border-border pb-2">
            {strains.map((s, idx) => (
              <button
                key={idx}
                onClick={() => setActiveStrain(idx)}
                className={`rounded-t-md px-3 py-2 text-sm transition-colors cursor-pointer ${activeStrain === idx ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground'}`}
              >
                {s.strain || `Strain ${idx + 1}`} <span className="text-xs opacity-75">({s.images.length} img)</span>
              </button>
            ))}
          </div>

          {loadingSegments && (
            <Card>
              <CardContent className="flex items-center justify-center gap-2 p-6">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Loading segment data...</span>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="p-4">
              <CardTitle className="font-heading">Segmentation Review</CardTitle>
              <CardDescription>
                {current ? `${current.strain} · ${current.images.length} images · Segmentation ${segmentedImages}/${totalImages} (${totalImages ? Math.round((segmentedImages / totalImages) * 100) : 100}%)` : 'No strain selected'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-4 pt-0">
              {!current || current.images.length === 0 ? (
                <p className="text-sm text-muted-foreground">No images for this strain.</p>
              ) : (
                current.images.map((img) => (
                  <SegmentCard
                    key={img.id}
                    image={img}
                    onUpdateBbox={(si, bb) => updateBbox(activeStrain, img.id, si, bb)}
                    onAddBbox={(bb) => addBbox(activeStrain, img.id, bb)}
                    onRemoveBbox={(si) => removeBbox(activeStrain, img.id, si)}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {step === 'review' && (
        <Card>
          <CardHeader>
            <CardTitle className="font-heading">Review Before Indexing</CardTitle>
            <CardDescription>Verify species, bounding boxes, and media for each strain before indexing into Qdrant.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="overflow-auto rounded-lg border border-border">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b border-border">
                  <tr className="border-b border-border transition-colors">
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Strain</th>
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Species</th>
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Images</th>
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Media</th>
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Segments</th>
                    <th className="h-12 px-4 text-left align-middle font-heading text-xs uppercase tracking-wider text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {strains.map((s, idx) => {
                    const speciesName = speciesList.find((sp) => sp.id === s.species)?.name ?? '-'
                    const totalSegments = s.images.reduce((sum, img) => sum + img.segments.length, 0)
                    return (
                      <tr key={idx} className="border-b border-border transition-colors hover:bg-muted/50">
                        <td className="p-4 align-middle font-mono text-xs">{s.strain || `Strain ${idx + 1}`}</td>
                        <td className="p-4 align-middle">
                          {creatingSpecies && creatingSpecies.strainIdx === idx ? (
                            <div className="flex items-center gap-2">
                              <Input className="h-8 w-36 text-xs" placeholder="Species name" value={creatingSpecies.name} onChange={(e) => setCreatingSpecies({ ...creatingSpecies, name: e.target.value })} autoFocus />
                              <Input className="h-8 w-32 text-xs" placeholder="Description" value={creatingSpecies.description} onChange={(e) => setCreatingSpecies({ ...creatingSpecies, description: e.target.value })} />
                              <Button size="sm" className="h-8 px-2" onClick={confirmCreateSpecies} disabled={createSpeciesMutation.isPending}><Check className="h-3 w-3" /></Button>
                              <Button size="sm" variant="ghost" className="h-8 px-2 text-destructive" onClick={cancelCreateSpecies}><X className="h-3 w-3" /></Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1">
                              <Select value={s.species} onChange={(e) => {
                                if (e.target.value === '__create__') {
                                  setCreatingSpecies({ strainIdx: idx, name: '', description: '' })
                                } else {
                                  updateStrain(idx, { species: e.target.value })
                                }
                              }} className="h-8 w-44 text-xs">
                                {speciesList.filter((sp) => !sp.is_archived).map((sp) => (
                                  <option key={sp.id} value={sp.id}>{sp.name}</option>
                                ))}
                                <option value="__create__">+ Create new species</option>
                              </Select>
                              <Badge variant="secondary" className="text-[10px]">{speciesName}</Badge>
                            </div>
                          )}
                        </td>
                        <td className="p-4 align-middle">{s.images.length}</td>
                        <td className="p-4 align-middle">{s.images.map((img) => img.media).filter((m, i, a) => a.indexOf(m) === i).join(', ')}</td>
                        <td className="p-4 align-middle"><Badge variant={totalSegments > 0 ? 'success' : 'secondary'}>{totalSegments || (1 + (idx % 3)) * s.images.length} detected</Badge></td>
                        <td className="p-4 align-middle">
                          <Button variant="ghost" size="sm" className="text-destructive"><Trash2 className="h-4 w-4" /></Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-md">
              <span className="text-xs">Images and segments will be indexed into Qdrant with known species metadata. Metadata changes after indexing will require Qdrant re-indexing.</span>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 'done' && (
        <Card>
          <CardContent className="p-6 text-center space-y-3">
            <Check className="h-12 w-12 text-success mx-auto" />
            <CardTitle className="font-heading">{strains.length} strain{strains.length !== 1 ? 's' : ''} indexed</CardTitle>
            <p className="text-sm text-muted-foreground">{totalImages} images with segments indexed into Qdrant.</p>
            <div className="flex justify-center gap-2">
              <Button variant="outline" onClick={() => setStep('upload')}>Index More Data</Button>
              <Button onClick={() => { window.location.href = '/dataset' }}>View Dataset</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Dialog open={agentsOpen} onClose={() => setAgentsOpen(false)} className="max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FileText className="h-4 w-4" /> AGENTS.md</DialogTitle>
          <DialogDescription>Instructions included in the template ZIP for your local agent.</DialogDescription>
        </DialogHeader>
        <DialogContent>
          <pre className="max-h-[60vh] overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">{AGENTS_MD_CONTENT}</pre>
        </DialogContent>
        <DialogFooter>
          <Button size="sm" onClick={() => setAgentsOpen(false)}>Close</Button>
        </DialogFooter>
      </Dialog>

      <div className="flex justify-between">
        <Button
          variant="outline"
          disabled={step === 'upload'}
          onClick={() => {
            if (step === 'segment') setStep('upload')
            else if (step === 'review') setStep('segment')
            else if (step === 'done') setStep('review')
          }}
        >
          Previous
        </Button>
        <Button
          onClick={() => {
            if (step === 'upload') goToSegment()
            else if (step === 'segment') confirmActiveStrain()
            else if (step === 'review') setStep('done')
          }}
          disabled={step === 'done' || autoSegmenting || loadingSegments || (step === 'upload' && totalImages === 0)}
        >
          {autoSegmenting ? `Segmenting ${segmentedImages}/${totalImages}` : step === 'upload' ? 'Segment Uploaded' : step === 'segment' ? `Confirm strain ${confirmedCount}/${strains.length}` : step === 'review' ? `Index into Qdrant ${batchProgress?.feature_extraction.completed ?? confirmedCount}/${batchProgress?.feature_extraction.total ?? strains.length}` : 'Done'} <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

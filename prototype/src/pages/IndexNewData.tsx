import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { speciesList, mediaList } from '@/lib/mock-data'
import { sampleStrains } from '@/lib/sample-assets'
import { ArrowRight, ChevronRight, Download, Images, Plus, Trash2, Check, X } from 'lucide-react'

type Step = 'upload' | 'review' | 'done'

interface StrainImage {
  id: string
  fileName: string
  media: string
  original?: string
}

interface IndexStrain {
  strain: string
  species: string
  images: StrainImage[]
}

function Breadcrumb({ step }: { step: Step }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
      <span>Index New Data</span>
      <ChevronRight className="h-3 w-3" />
      <span className={step === 'upload' ? 'text-foreground font-medium' : ''}>Upload</span>
      {step !== 'upload' && (
        <>
          <ChevronRight className="h-3 w-3" />
          <span className={step === 'review' ? 'text-foreground font-medium' : ''}>Review</span>
        </>
      )}
      {step === 'done' && (
        <>
          <ChevronRight className="h-3 w-3" />
          <span className="text-foreground font-medium">Indexed</span>
        </>
      )}
    </nav>
  )
}

export default function IndexNewDataPage() {
  const [step, setStep] = useState<Step>('upload')
  const [strains, setStrains] = useState<IndexStrain[]>([])
  const [activeStrain, setActiveStrain] = useState(0)
  const [creatingSpecies, setCreatingSpecies] = useState<{ strainIdx: number; name: string; description: string } | null>(null)

  const current = strains[activeStrain]
  const totalImages = strains.reduce((sum, s) => sum + s.images.length, 0)

  const addStrain = () => {
    setStrains([...strains, { strain: '', species: speciesList[0].species_id, images: [] }])
    setActiveStrain(strains.length)
  }

  const removeStrain = (idx: number) => {
    const next = strains.filter((_, i) => i !== idx)
    setStrains(next)
    setActiveStrain(Math.max(0, idx - 1))
  }

  const confirmCreateSpecies = () => {
    if (!creatingSpecies || !creatingSpecies.name.trim()) return
    const newId = `sp-new-${crypto.randomUUID().slice(0, 8)}`
    speciesList.push({
      species_id: newId,
      name: creatingSpecies.name.trim(),
      description: creatingSpecies.description || null,
      created_at: new Date().toISOString().split('T')[0],
      updated_at: new Date().toISOString().split('T')[0],
      is_archived: false,
    })
    updateStrain(creatingSpecies.strainIdx, { species: newId })
    setCreatingSpecies(null)
  }

  const cancelCreateSpecies = () => setCreatingSpecies(null)

  const updateStrain = (idx: number, field: Partial<IndexStrain>) => {
    setStrains(strains.map((s, i) => (i === idx ? { ...s, ...field } : s)))
  }

  const loadSample = () => {
    setStrains((sampleStrains as unknown as Array<{ strain: string; species: string; images: Array<{ id: string; fileName: string; media: string; original: string }> }>).map((s) => ({
      strain: s.strain,
      species: speciesList.find((sp) => sp.name === s.species)?.species_id ?? speciesList[0].species_id,
      images: s.images.map((img) => ({ id: img.id, fileName: img.fileName, media: img.media, original: img.original })),
    })))
    setActiveStrain(0)
  }

  const addImage = (strainIdx: number) => {
    const pool = (sampleStrains as unknown as Array<{ images: Array<{ id: string; fileName: string; media: string; original: string }> }>).flatMap((s) => s.images)
    const sample = pool[strains[strainIdx].images.length % pool.length]
    const img: StrainImage = {
      id: crypto.randomUUID(),
      fileName: sample?.fileName ?? `image_${strains[strainIdx].images.length + 1}.jpg`,
      media: sample?.media ?? mediaList[0].name,
      original: sample?.original,
    }
    updateStrain(strainIdx, { images: [...strains[strainIdx].images, img] })
  }

  const removeImage = (strainIdx: number, imgId: string) => {
    updateStrain(strainIdx, { images: strains[strainIdx].images.filter((img) => img.id !== imgId) })
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <Breadcrumb step={step} />
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-heading text-2xl font-bold text-foreground">Index New Data</h1>
            <p className="text-sm text-muted-foreground">
              Add reference data by strain with known species. Each strain has images across media. Species metadata is required for indexing — retrieval is bypassed.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {(['upload', 'review', 'done'] as const).map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full font-heading text-sm font-medium ${
                  step === s ? 'bg-primary text-primary-foreground' : step === 'done' && i < 2 ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
                }`}>
                  {step === 'done' && i < 2 ? <Check className="h-4 w-4" /> : i + 1}
                </div>
                <span className={`text-sm ${step === s ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                  {s === 'upload' ? 'Upload' : s === 'review' ? 'Review' : 'Indexed'}
                </span>
                {i < 2 && <div className="h-px w-8 bg-border" />}
              </div>
            ))}
          </div>
        </div>
      </div>

      {step === 'upload' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadSample}><Download className="h-4 w-4" /> Load Sample Data</Button>
            <Button variant="outline" size="sm" onClick={addStrain}><Plus className="h-4 w-4" /> Add Strain</Button>
            <div className="ml-auto text-xs text-muted-foreground">{strains.length} strain(s) · {totalImages} image(s)</div>
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

          {strains.length === 0 ? (
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
                        <option key={s.species_id} value={s.species_id}>{s.name}</option>
                      ))}
                    </Select>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Species metadata is required for indexing. Index New Data reuses upload and segmentation but bypasses species prediction.
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => addImage(activeStrain)}><Plus className="h-4 w-4" /> Add Image</Button>
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
                                {mediaList.filter((m) => !m.is_archived).map((m) => (
                                  <option key={m.media_id} value={m.name}>{m.name}</option>
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
                    const speciesName = speciesList.find((sp) => sp.species_id === s.species)?.name ?? '-'
                    return (
                      <tr key={idx} className="border-b border-border transition-colors hover:bg-muted/50">
                        <td className="p-4 align-middle font-mono text-xs">{s.strain || `Strain ${idx + 1}`}</td>
                        <td className="p-4 align-middle">
                          {creatingSpecies && creatingSpecies.strainIdx === idx ? (
                            <div className="flex items-center gap-2">
                              <Input
                                className="h-8 w-36 text-xs"
                                placeholder="Species name"
                                value={creatingSpecies.name}
                                onChange={(e) => setCreatingSpecies({ ...creatingSpecies, name: e.target.value })}
                                autoFocus
                              />
                              <Input
                                className="h-8 w-32 text-xs"
                                placeholder="Description"
                                value={creatingSpecies.description}
                                onChange={(e) => setCreatingSpecies({ ...creatingSpecies, description: e.target.value })}
                              />
                              <Button size="sm" className="h-8 px-2" onClick={confirmCreateSpecies}><Check className="h-3 w-3" /></Button>
                              <Button size="sm" variant="ghost" className="h-8 px-2 text-destructive" onClick={cancelCreateSpecies}><X className="h-3 w-3" /></Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1">
                              <Select
                                value={s.species}
                                onChange={(e) => {
                                  if (e.target.value === '__create__') {
                                    setCreatingSpecies({ strainIdx: idx, name: '', description: '' })
                                  } else {
                                    updateStrain(idx, { species: e.target.value })
                                  }
                                }}
                                className="h-8 w-44 text-xs"
                              >
                                {speciesList.filter((sp) => !sp.is_archived).map((sp) => (
                                  <option key={sp.species_id} value={sp.species_id}>{sp.name}</option>
                                ))}
                                <option value="__create__">+ Create new species</option>
                              </Select>
                              <Badge variant="secondary" className="text-[10px]">{speciesName}</Badge>
                            </div>
                          )}
                        </td>
                        <td className="p-4 align-middle">{s.images.length}</td>
                        <td className="p-4 align-middle">{s.images.map((img) => img.media).join(', ')}</td>
                        <td className="p-4 align-middle"><Badge variant="success">{(1 + (idx % 3)) * s.images.length} detected</Badge></td>
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

      <div className="flex justify-between">
        <Button variant="outline" disabled={step === 'upload'} onClick={() => setStep(step === 'done' ? 'review' : 'upload')}>Previous</Button>
        <Button onClick={() => setStep(step === 'upload' ? 'review' : 'done')} disabled={step === 'done'}>
          {step === 'upload' ? 'Review & Edit' : 'Index into Qdrant'} <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

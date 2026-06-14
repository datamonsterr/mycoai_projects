import { useState } from 'react'
import { resolveImageUrl } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { useSpeciesList, useMediaList } from '@/hooks/use-taxonomy'
import { useImagesList } from '@/hooks/use-images'
import { useAuth } from '@/lib/use-auth'
import {
  Search,
  Download,
  Archive,
  RotateCcw,
  Edit,
  ChevronDown,
  ChevronRight,
  Filter,
  X,
} from 'lucide-react'

export default function DatasetPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner' || user?.role === 'dataowner'
  const [search, setSearch] = useState('')
  const [filterSpecies, setFilterSpecies] = useState<string[]>([])
  const [filterMedia, setFilterMedia] = useState<string[]>([])
  const [filterStatus, setFilterStatus] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [editItem, setEditItem] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [fullscreenImage, setFullscreenImage] = useState<{ src: string; alt: string } | null>(null)

  const { data: speciesData } = useSpeciesList()
  const { data: mediaData } = useMediaList()
  const { data: imagesData, isLoading } = useImagesList({
    species_id: filterSpecies.length > 0 ? filterSpecies : undefined,
    media_id: filterMedia.length > 0 ? filterMedia : undefined,
    status: filterStatus || undefined,
    search: search || undefined,
  })

  const speciesList = speciesData?.items ?? []
  const mList = mediaData?.items ?? []
  const images = imagesData?.items ?? []
  const total = imagesData?.total ?? 0

  const toggleSpecies = (id: string) => {
    setFilterSpecies((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    )
  }

  const toggleMedia = (id: string) => {
    setFilterMedia((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id],
    )
  }

  const toggleExpand = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const clearFilters = () => {
    setSearch('')
    setFilterSpecies([])
    setFilterMedia([])
    setFilterStatus('')
  }

  const activeFilterCount =
    (filterSpecies.length > 0 ? 1 : 0) +
    (filterMedia.length > 0 ? 1 : 0) +
    (filterStatus ? 1 : 0) +
    (search ? 1 : 0)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">Dataset Browser</h1>
          <p className="text-sm text-muted-foreground mt-1">{total} records</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="h-4 w-4" /> Export CSV</Button>
          {isOwner && (
            <Button size="sm" onClick={() => { window.location.href = '/index' }}>Index New Data</Button>
          )}
        </div>
      </div>

      {/* Search bar + filter toggle */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by strain..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button
          variant={filtersOpen ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFiltersOpen(!filtersOpen)}
          className="gap-1.5"
        >
          <Filter className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-1 inline-flex items-center justify-center h-5 min-w-[20px] rounded-full bg-primary-foreground text-primary text-[11px] font-bold px-1.5">
              {activeFilterCount}
            </span>
          )}
        </Button>
        {activeFilterCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="gap-1 text-muted-foreground">
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        )}
      </div>

      {/* Collapsible filter panel */}
      {filtersOpen && (
        <Card>
          <CardContent className="p-4 space-y-4">
            {/* Species checkboxes */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Species</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 max-h-40 overflow-y-auto">
                {speciesList.filter((s) => !s.is_archived).map((s) => (
                  <label key={s.id} className="flex items-center gap-1.5 text-sm cursor-pointer hover:text-foreground transition-colors">
                    <input
                      type="checkbox"
                      checked={filterSpecies.includes(s.id)}
                      onChange={() => toggleSpecies(s.id)}
                      className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer"
                    />
                    {s.name}
                  </label>
                ))}
              </div>
            </div>

            {/* Media checkboxes */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Media</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 max-h-40 overflow-y-auto">
                {mList.filter((m) => !m.is_archived).map((m) => (
                  <label key={m.id} className="flex items-center gap-1.5 text-sm cursor-pointer hover:text-foreground transition-colors">
                    <input
                      type="checkbox"
                      checked={filterMedia.includes(m.id)}
                      onChange={() => toggleMedia(m.id)}
                      className="h-3.5 w-3.5 rounded border-border accent-primary cursor-pointer"
                    />
                    {m.name}
                  </label>
                ))}
              </div>
            </div>

            {/* Status radio-like */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Status</p>
              <div className="flex flex-wrap gap-x-4 gap-y-1.5">
                {[
                  { value: '', label: 'All' },
                  { value: 'current', label: 'Current' },
                  { value: 'updated_requires_reindex', label: 'Needs Reindex' },
                  { value: 'archived', label: 'Archived' },
                ].map((opt) => (
                  <label key={opt.value} className="flex items-center gap-1.5 text-sm cursor-pointer hover:text-foreground transition-colors">
                    <input
                      type="radio"
                      name="status"
                      checked={filterStatus === opt.value}
                      onChange={() => setFilterStatus(opt.value)}
                      className="h-3.5 w-3.5 accent-primary cursor-pointer"
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>

            <p className="text-xs text-muted-foreground">{images.length} results</p>
          </CardContent>
        </Card>
      )}

      {!filtersOpen && (
        <p className="text-xs text-muted-foreground">{images.length} results</p>
      )}

      {/* Table */}
      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10" />
                <TableHead>Plate</TableHead>
                <TableHead>Strain</TableHead>
                <TableHead>Species</TableHead>
                <TableHead>Media</TableHead>
                {isOwner && <TableHead>Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={`skel-${i}`}>
                    <TableCell><div className="h-4 w-4 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-10 w-10 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-24 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-32 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-12 rounded bg-muted animate-pulse" /></TableCell>
                    {isOwner && <TableCell><div className="h-4 w-16 rounded bg-muted animate-pulse" /></TableCell>}
                  </TableRow>
                ))
              ) : images.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={isOwner ? 6 : 5} className="text-center py-12 text-muted-foreground">
                    No images found
                  </TableCell>
                </TableRow>
              ) : (
                images.map((img) => {
                  const isArchived = img.data_update_status === 'archived'
                  const isExpanded = expandedRows.has(img.id)
                  return (
                    <>
                      <TableRow key={img.id} className={isArchived ? 'opacity-50' : ''}>
                        <TableCell>
                          <button
                            onClick={() => toggleExpand(img.id)}
                            className="cursor-pointer hover:bg-muted rounded p-0.5 transition-colors"
                            title={isExpanded ? 'Collapse details' : 'Expand details'}
                          >
                            {isExpanded
                              ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              : <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            }
                          </button>
                        </TableCell>
                        <TableCell>
                          <img
                            src={img.source_url || resolveImageUrl(img.file_path)}
                            alt=""
                            className="h-12 w-12 rounded object-cover border border-border"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                          />
                        </TableCell>
                        <TableCell className="font-mono text-xs">{img.strain_name}</TableCell>
                        <TableCell>{img.species_name}</TableCell>
                        <TableCell>{img.media_name}</TableCell>
                        {isOwner && (
                          <TableCell>
                            <div className="flex gap-1">
                              <Button variant="ghost" size="sm" onClick={() => setEditItem(img.id)}><Edit className="h-4 w-4" /></Button>
                              {isArchived ? (
                                <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                              ) : (
                                <Button variant="ghost" size="sm" className="text-destructive"><Archive className="h-4 w-4" /></Button>
                              )}
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                      {isExpanded && (
                        <TableRow key={`${img.id}-expanded`}>
                          <TableCell />
                          <TableCell colSpan={isOwner ? 5 : 4} className="bg-muted/30">
                            <div className="flex gap-4 py-2 min-h-64">
                              <div className="flex-shrink-0 w-72 self-stretch">
                                <img
                                  src={img.source_url || resolveImageUrl(img.file_path)}
                                  alt={img.strain_name ?? 'Plate'}
                                  className="w-full h-full object-cover rounded-md border border-border cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => setFullscreenImage({ src: img.source_url || resolveImageUrl(img.file_path), alt: img.strain_name ?? 'Plate' })}
                                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 py-1 text-xs">
                                  <div>
                                    <span className="text-muted-foreground">Image ID</span>
                                    <p className="font-mono mt-0.5 truncate max-w-[200px]" title={img.id}>{img.id}</p>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Segments</span>
                                    <p className="font-mono mt-0.5">{img.segments_count}</p>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Qdrant</span>
                                    <p className="mt-0.5">
                                      {img.indexed_in_qdrant
                                        ? <Badge variant="success">Indexed</Badge>
                                        : <Badge variant="secondary">No</Badge>}
                                    </p>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Status</span>
                                    <p className="mt-0.5">
                                      <Badge variant={
                                        img.data_update_status === 'current' ? 'success'
                                          : img.data_update_status === 'updated_requires_reindex' ? 'warning'
                                          : 'destructive'
                                      }>
                                        {img.data_update_status === 'updated_requires_reindex' ? 'Needs Reindex' : img.data_update_status}
                                      </Badge>
                                    </p>
                                  </div>
                                  {img.angle && (
                                    <div>
                                      <span className="text-muted-foreground">Angle</span>
                                      <p className="mt-0.5">{img.angle}</p>
                                    </div>
                                  )}
                                  <div>
                                    <span className="text-muted-foreground">Created</span>
                                    <p className="mt-0.5">{new Date(img.created_at).toLocaleDateString()}</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editItem !== null} onClose={() => setEditItem(null)}>
        <DialogHeader>
          <DialogTitle>Edit Image Metadata</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-3">
            <p className="text-xs font-mono">Image: {editItem}</p>
            {images.find((img) => img.id === editItem) && (
              <img
                src={resolveImageUrl(images.find((img) => img.id === editItem)!.file_path)}
                alt="Selected plate"
                className="w-full max-h-64 rounded-md object-contain border border-border bg-muted"
              />
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Species</label>
              <select className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
                {speciesList.filter((s) => !s.is_archived).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Strain</label>
              <Input defaultValue={images.find((img) => img.id === editItem)?.strain_name ?? ''} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Media</label>
              <select className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm">
                {mList.filter((m) => !m.is_archived).map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            <div className="p-3 bg-warning/10 border border-warning/20 rounded-md">
              <p className="text-xs">This update will mark the item as <strong>updated_requires_reindex</strong>. Qdrant re-indexing will be required before retrieval reflects this change.</p>
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={() => setEditItem(null)}>Cancel</Button>
          <Button onClick={() => setEditItem(null)}>Save Changes</Button>
        </DialogFooter>
      </Dialog>

      {/* Fullscreen image preview */}
      {fullscreenImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 cursor-pointer"
          onClick={() => setFullscreenImage(null)}
        >
          <img
            src={fullscreenImage.src}
            alt={fullscreenImage.alt}
            className="max-w-full max-h-full object-contain"
          />
          <button
            className="absolute top-4 right-4 text-white/80 hover:text-white p-2 rounded-full bg-black/40 hover:bg-black/60 transition-colors"
            onClick={() => setFullscreenImage(null)}
            aria-label="Close fullscreen preview"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
      )}
    </div>
  )
}

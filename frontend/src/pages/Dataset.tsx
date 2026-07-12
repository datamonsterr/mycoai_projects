import { Fragment, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { useSpeciesList, useMediaList } from '@/hooks/use-taxonomy'
import { useImageGroups } from '@/hooks/use-images'
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
  const { data: imagesData, isLoading } = useImageGroups({
    species_id: filterSpecies.length > 0 ? filterSpecies : undefined,
    media_id: filterMedia.length > 0 ? filterMedia : undefined,
    status: filterStatus || undefined,
    search: search || undefined,
    include_archived: filterStatus === 'archived',
  })

  const speciesList = speciesData?.items ?? []
  const mList = mediaData?.items ?? []
  const strainGroups = imagesData?.items ?? []
  const images = strainGroups.flatMap((group) => group.images)
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
          <p className="text-sm text-muted-foreground mt-1">{total} strains</p>
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

            <p className="text-xs text-muted-foreground">{strainGroups.length} results</p>
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
                <TableHead>Strain</TableHead>
                <TableHead>Species</TableHead>
                <TableHead>Media</TableHead>
                <TableHead>Images</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={`skel-${i}`}>
                    <TableCell><div className="h-4 w-4 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-24 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-32 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-20 rounded bg-muted animate-pulse" /></TableCell>
                    <TableCell><div className="h-4 w-12 rounded bg-muted animate-pulse" /></TableCell>
                  </TableRow>
                ))
              ) : strainGroups.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                    No strains found
                  </TableCell>
                </TableRow>
              ) : (
                strainGroups.map((group) => {
                  const isExpanded = expandedRows.has(group.strain_id)
                  return (
                    <Fragment key={group.strain_id}>
                      <TableRow>
                        <TableCell>
                          <button
                            onClick={() => toggleExpand(group.strain_id)}
                            className="cursor-pointer hover:bg-muted rounded p-0.5 transition-colors"
                            title={isExpanded ? 'Collapse images' : 'Expand images'}
                          >
                            {isExpanded
                              ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                          </button>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{group.strain_name}</TableCell>
                        <TableCell>{group.species_name}</TableCell>
                        <TableCell>{group.media_names.join(', ')}</TableCell>
                        <TableCell>{group.image_count}</TableCell>
                      </TableRow>
                      {isExpanded && (
                        <TableRow key={`${group.strain_id}-images`}>
                          <TableCell />
                          <TableCell colSpan={4} className="bg-muted/30 p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Image</TableHead>
                                  <TableHead>Created</TableHead>
                                  <TableHead>Status</TableHead>
                                  <TableHead>Qdrant</TableHead>
                                  {isOwner && <TableHead>Actions</TableHead>}
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {group.images.map((image) => (
                                  <TableRow key={image.id} className={image.is_archived ? 'opacity-50' : ''}>
                                    <TableCell>
                                      <img
                                        src={image.source_url}
                                        alt={`${group.strain_name} image`}
                                        className="h-16 w-16 rounded object-cover border border-border cursor-pointer"
                                        onClick={() => setFullscreenImage({ src: image.source_url, alt: `${group.strain_name} image` })}
                                      />
                                    </TableCell>
                                    <TableCell>{new Date(image.created_at).toLocaleDateString()}</TableCell>
                                    <TableCell>
                                      <Badge variant={image.data_update_status === 'current' ? 'success' : image.data_update_status === 'updated_requires_reindex' ? 'warning' : 'destructive'}>
                                        {image.data_update_status === 'updated_requires_reindex' ? 'Needs Reindex' : image.data_update_status}
                                      </Badge>
                                    </TableCell>
                                    <TableCell>
                                      {image.indexed_in_qdrant
                                        ? <Badge variant="success">Indexed</Badge>
                                        : <Badge variant="secondary">No</Badge>}
                                    </TableCell>
                                    {isOwner && (
                                      <TableCell>
                                        <div className="flex gap-1">
                                          <Button aria-label="Edit image" variant="ghost" size="sm" onClick={() => setEditItem(image.id)}><Edit className="h-4 w-4" /></Button>
                                          {image.is_archived
                                            ? <Button aria-label="Restore image" variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                                            : <Button aria-label="Archive image" variant="ghost" size="sm" className="text-destructive"><Archive className="h-4 w-4" /></Button>}
                                        </div>
                                      </TableCell>
                                    )}
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
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
            {(() => {
              const group = strainGroups.find((g) => g.images.some((img) => img.id === editItem))
              const image = group?.images.find((img) => img.id === editItem)
              return image && group ? (
                <img
                  src={image.source_url}
                  alt={`${group.strain_name} image`}
                  className="w-full max-h-64 rounded-md object-contain border border-border bg-muted"
                />
              ) : null
            })()}
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
              <Input defaultValue={strainGroups.find((g) => g.images.some((img) => img.id === editItem))?.strain_name ?? ''} />
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

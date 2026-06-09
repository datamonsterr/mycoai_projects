import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { datasetImages } from '@/lib/mock-data'
import { useSpeciesList, useMediaList } from '@/hooks/use-taxonomy'
import { useAuth } from '@/lib/use-auth'
import { Search, Download, Archive, RotateCcw, Edit } from 'lucide-react'

export default function DatasetPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner'
  const [search, setSearch] = useState('')
  const [filterSpecies, setFilterSpecies] = useState('')
  const [filterMedia, setFilterMedia] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [groupBy, setGroupBy] = useState('none')
  const [editItem, setEditItem] = useState<string | null>(null)

  const { data: speciesData } = useSpeciesList()
  const { data: mediaData } = useMediaList()
  const speciesList = speciesData?.items ?? []
  const mList = mediaData?.items ?? []

  const filtered = datasetImages.filter((img) => {
    if (search && !img.strain.toLowerCase().includes(search.toLowerCase())) return false
    if (filterSpecies && img.species_id !== filterSpecies) return false
    if (filterMedia && img.media_id !== filterMedia) return false
    if (filterStatus && img.data_update_status !== filterStatus) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">Dataset Browser</h1>
          <p className="text-sm text-muted-foreground mt-1">{datasetImages.length} records</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Download className="h-4 w-4" /> Export CSV</Button>
          {isOwner && (
            <Button size="sm" onClick={() => { window.location.href = '/index' }}>Index New Data</Button>
          )}
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-[200px] relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by strain..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={filterSpecies} onChange={(e) => setFilterSpecies(e.target.value)} className="w-48">
              <option value="">All Species</option>
              {speciesList.filter((s) => !s.is_archived).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
            <Select value={filterMedia} onChange={(e) => setFilterMedia(e.target.value)} className="w-40">
              <option value="">All Media</option>
              {mList.filter((m) => !m.is_archived).map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </Select>
            <Select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="w-44">
              <option value="">All Status</option>
              <option value="current">Current</option>
              <option value="updated_requires_reindex">Needs Reindex</option>
              <option value="archived">Archived</option>
            </Select>
            <Select value={groupBy} onChange={(e) => setGroupBy(e.target.value)} className="w-36">
              <option value="none">No Grouping</option>
              <option value="strain">Group by Strain</option>
              <option value="media">Group by Media</option>
              <option value="species">Group by Species</option>
            </Select>
          </div>
          <p className="text-xs text-muted-foreground">{filtered.length} results</p>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
                <TableRow>
                <TableHead>Plate</TableHead>
                <TableHead>Image ID</TableHead>
                <TableHead>Strain</TableHead>
                <TableHead>Species</TableHead>
                <TableHead>Media</TableHead>
                <TableHead>Segments</TableHead>
                <TableHead>Qdrant</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((img) => {
                const species = speciesList.find((s) => s.id === img.species_id)
                const media = mList.find((m) => m.id === img.media_id)
                const isArchived = img.data_update_status === 'archived'
                return (
                  <TableRow key={img.image_id} className={isArchived ? 'opacity-50' : ''}>
                    <TableCell>
                      <img src={img.file_path} alt="" className="h-12 w-12 rounded object-cover border border-border" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                    </TableCell>
                    <TableCell className="font-mono text-xs">{img.image_id}</TableCell>
                    <TableCell className="font-mono text-xs">{img.strain}</TableCell>
                    <TableCell>{species?.name ?? '-'}</TableCell>
                    <TableCell>{media?.name ?? '-'}</TableCell>
                    <TableCell>{img.segments.length}</TableCell>
                    <TableCell>{img.indexed_in_qdrant ? <Badge variant="success">Indexed</Badge> : <Badge variant="secondary">No</Badge>}</TableCell>
                    <TableCell>
                      <Badge variant={
                        img.data_update_status === 'current' ? 'success' :
                          img.data_update_status === 'updated_requires_reindex' ? 'warning' : 'destructive'
                      }>
                        {img.data_update_status === 'updated_requires_reindex' ? 'Needs Reindex' : img.data_update_status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {isOwner ? (
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditItem(img.image_id)}><Edit className="h-4 w-4" /></Button>
                          {isArchived ? (
                            <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                          ) : (
                            <Button variant="ghost" size="sm" className="text-destructive"><Archive className="h-4 w-4" /></Button>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
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
            {datasetImages.find((d) => d.image_id === editItem)?.file_path && (
              <div className="space-y-2">
                <img src={datasetImages.find((d) => d.image_id === editItem)?.file_path} alt="Selected plate" className="w-full max-h-64 rounded-md object-contain border border-border bg-muted" />
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {datasetImages.find((d) => d.image_id === editItem)?.segments.map((segment) => (
                    <img key={segment.segment_index} src={segment.crop_path} alt={`Segment ${segment.segment_index + 1}`} className="h-20 w-20 rounded object-cover border border-border" />
                  ))}
                </div>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium">Species</label>
              <Select defaultValue={datasetImages.find((d) => d.image_id === editItem)?.species_id ?? ''}>
                {speciesList.filter((s) => !s.is_archived).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Strain</label>
              <Input defaultValue={datasetImages.find((d) => d.image_id === editItem)?.strain ?? ''} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Media</label>
              <Select defaultValue={datasetImages.find((d) => d.image_id === editItem)?.media_id ?? ''}>
                {mList.filter((m) => !m.is_archived).map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </Select>
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
    </div>
  )
}

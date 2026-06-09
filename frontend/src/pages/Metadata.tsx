import { useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { Plus, Archive, RotateCcw, Edit, TagIcon, Beaker } from 'lucide-react'
import {
  useSpeciesList,
  useCreateSpecies,
  useUpdateSpecies,
  useArchiveSpecies,
  useMediaList,
  useCreateMedia,
  useUpdateMedia,
  useArchiveMedia,
} from '@/hooks/use-taxonomy'
import { useToast } from '@/hooks/use-toast'

export default function MetadataPage() {
  const [tab, setTab] = useState('species')
  const [createOpen, setCreateOpen] = useState(false)
  const [createType, setCreateType] = useState<'species' | 'media'>('species')
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')

  const { data: speciesData, isLoading: speciesLoading } = useSpeciesList()
  const { data: mediaData, isLoading: mediaLoading } = useMediaList()
  const speciesList = speciesData?.items ?? []
  const mList = mediaData?.items ?? []

  const createSpecies = useCreateSpecies()
  const updateSpecies = useUpdateSpecies()
  const archiveSpecies = useArchiveSpecies()
  const createMedia = useCreateMedia()
  const updateMedia = useUpdateMedia()
  const archiveMedia = useArchiveMedia()
  const toast = useToast()

  const openCreate = (type: 'species' | 'media') => {
    setCreateType(type)
    setNewName('')
    setNewDesc('')
    setCreateOpen(true)
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      if (createType === 'species') {
        await createSpecies.mutateAsync({ name: newName.trim(), description: newDesc || null })
      } else {
        await createMedia.mutateAsync({ name: newName.trim(), description: newDesc || null })
      }
      toast.success(`${createType === 'species' ? 'Species' : 'Media'} created`)
      setCreateOpen(false)
    } catch (err) {
      toast.apiError(err, `Failed to create ${createType}`)
    }
  }

  const openEdit = (type: 'species' | 'media', id: string, name: string, desc: string | null) => {
    setCreateType(type)
    setEditId(id)
    setEditName(name)
    setEditDesc(desc ?? '')
    setCreateOpen(true)
  }

  const handleUpdate = async () => {
    if (!editId || !editName.trim()) return
    try {
      if (createType === 'species') {
        await updateSpecies.mutateAsync({ id: editId, name: editName.trim(), description: editDesc || null })
      } else {
        await updateMedia.mutateAsync({ id: editId, name: editName.trim(), description: editDesc || null })
      }
      toast.success(`${createType === 'species' ? 'Species' : 'Media'} updated`)
      setCreateOpen(false)
      setEditId(null)
    } catch (err) {
      toast.apiError(err, `Failed to update ${createType}`)
    }
  }

  const handleArchive = async (type: 'species' | 'media', id: string) => {
    try {
      if (type === 'species') {
        await archiveSpecies.mutateAsync(id)
      } else {
        await archiveMedia.mutateAsync(id)
      }
      toast.success(`${type === 'species' ? 'Species' : 'Media'} archived`)
    } catch (err) {
      toast.apiError(err, `Failed to archive ${type}`)
    }
  }

  const closeDialog = () => {
    setCreateOpen(false)
    setEditId(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">Manage Metadata</h1>
          <p className="text-sm text-muted-foreground mt-1">Species and Media catalogs used by retrieval and indexing</p>
        </div>
      </div>

      <Tabs defaultValue="species">
        <TabsList>
          <TabsTrigger value="species" active={tab === 'species'} onClick={() => setTab('species')}>
            <TagIcon className="h-4 w-4" /> Species ({speciesList.length})
          </TabsTrigger>
          <TabsTrigger value="media" active={tab === 'media'} onClick={() => setTab('media')}>
            <Beaker className="h-4 w-4" /> Media ({mList.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="species" activeValue={tab}>
          <div className="flex justify-end mb-4">
            <Button size="sm" onClick={() => openCreate('species')}><Plus className="h-4 w-4" /> Add Species</Button>
          </div>
          <Card>
            <CardContent className="p-0">
              {speciesLoading ? (
                <div className="p-8 text-center text-sm text-muted-foreground">Loading...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {speciesList.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell className="font-heading font-medium">{s.name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{s.description ?? '-'}</TableCell>
                        <TableCell className="text-xs">{new Date(s.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          {s.is_archived ? <Badge variant="destructive">Archived</Badge> : <Badge variant="success">Active</Badge>}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEdit('species', s.id, s.name, s.description)}><Edit className="h-4 w-4" /></Button>
                            {s.is_archived ? (
                              <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                            ) : (
                              <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleArchive('species', s.id)}><Archive className="h-4 w-4" /></Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {speciesList.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-sm text-muted-foreground py-8">No species yet</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="media" activeValue={tab}>
          <div className="flex justify-end mb-4">
            <Button size="sm" onClick={() => openCreate('media')}><Plus className="h-4 w-4" /> Add Media</Button>
          </div>
          <Card>
            <CardContent className="p-0">
              {mediaLoading ? (
                <div className="p-8 text-center text-sm text-muted-foreground">Loading...</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mList.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell className="font-heading font-medium">{m.name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{m.description ?? '-'}</TableCell>
                        <TableCell className="text-xs">{new Date(m.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          {m.is_archived ? <Badge variant="destructive">Archived</Badge> : <Badge variant="success">Active</Badge>}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEdit('media', m.id, m.name, m.description)}><Edit className="h-4 w-4" /></Button>
                            {m.is_archived ? (
                              <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                            ) : (
                              <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleArchive('media', m.id)}><Archive className="h-4 w-4" /></Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {mList.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-sm text-muted-foreground py-8">No media yet</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onClose={closeDialog}>
        <DialogHeader>
          <DialogTitle>{editId ? 'Edit' : 'Create New'} {createType === 'species' ? 'Species' : 'Media'}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input value={editId ? editName : newName} onChange={(e) => editId ? setEditName(e.target.value) : setNewName(e.target.value)} placeholder={`Enter ${createType} name`} />
              <p className="text-xs text-muted-foreground">Must be unique (case-insensitive)</p>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={editId ? editDesc : newDesc} onChange={(e) => editId ? setEditDesc(e.target.value) : setNewDesc(e.target.value)} placeholder="Optional description" />
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={closeDialog}>Cancel</Button>
          <Button onClick={editId ? handleUpdate : handleCreate} disabled={createSpecies.isPending || createMedia.isPending || updateSpecies.isPending || updateMedia.isPending}>
            {editId ? 'Save' : 'Create'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}

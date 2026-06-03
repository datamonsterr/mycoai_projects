import { useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { speciesList, mediaList } from '@/lib/mock-data'
import { Plus, Archive, RotateCcw, Edit, TagIcon, Beaker } from 'lucide-react'

export default function MetadataPage() {
  const [tab, setTab] = useState('species')
  const [createOpen, setCreateOpen] = useState(false)
  const [createType, setCreateType] = useState<'species' | 'media'>('species')
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const openCreate = (type: 'species' | 'media') => {
    setCreateType(type)
    setNewName('')
    setNewDesc('')
    setCreateOpen(true)
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
            <Beaker className="h-4 w-4" /> Media ({mediaList.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="species" activeValue={tab}>
          <div className="flex justify-end mb-4">
            <Button size="sm" onClick={() => openCreate('species')}><Plus className="h-4 w-4" /> Add Species</Button>
          </div>
          <Card>
            <CardContent className="p-0">
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
                    <TableRow key={s.species_id}>
                      <TableCell className="font-heading font-medium">{s.name}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{s.description ?? '-'}</TableCell>
                      <TableCell className="text-xs">{new Date(s.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        {s.is_archived ? <Badge variant="destructive">Archived</Badge> : <Badge variant="success">Active</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm"><Edit className="h-4 w-4" /></Button>
                          {s.is_archived ? (
                            <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                          ) : (
                            <Button variant="ghost" size="sm" className="text-destructive"><Archive className="h-4 w-4" /></Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="media" activeValue={tab}>
          <div className="flex justify-end mb-4">
            <Button size="sm" onClick={() => openCreate('media')}><Plus className="h-4 w-4" /> Add Media</Button>
          </div>
          <Card>
            <CardContent className="p-0">
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
                  {mediaList.map((m) => (
                    <TableRow key={m.media_id}>
                      <TableCell className="font-heading font-medium">{m.name}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{m.description ?? '-'}</TableCell>
                      <TableCell className="text-xs">{new Date(m.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        {m.is_archived ? <Badge variant="destructive">Archived</Badge> : <Badge variant="success">Active</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm"><Edit className="h-4 w-4" /></Button>
                          {m.is_archived ? (
                            <Button variant="ghost" size="sm"><RotateCcw className="h-4 w-4" /></Button>
                          ) : (
                            <Button variant="ghost" size="sm" className="text-destructive"><Archive className="h-4 w-4" /></Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogHeader>
          <DialogTitle>Create New {createType === 'species' ? 'Species' : 'Media'}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={`Enter ${createType} name`} />
              <p className="text-xs text-muted-foreground">Must be unique (case-insensitive)</p>
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Optional description" />
            </div>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button onClick={() => setCreateOpen(false)}>Create</Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}

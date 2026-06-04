import { useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/misc'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/misc'
import { Label } from '@/components/ui/label'
import { feedbackItems } from '@/lib/mock-data'
import { Check, X, Clock, Search } from 'lucide-react'
import { datasetImages } from '@/lib/mock-data'

export default function FeedbackInboxPage() {
  const [tab, setTab] = useState('pending')
  const [search, setSearch] = useState('')
  const [reviewItem, setReviewItem] = useState<string | null>(null)
  const [reviewNote, setReviewNote] = useState('')

  const filtered = feedbackItems.filter((f) => {
    if (tab !== 'all' && f.status !== tab) return false
    if (search && !f.query_strain.toLowerCase().includes(search.toLowerCase()) && !f.predicted_species.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const currentReview = feedbackItems.find((f) => f.feedback_id === reviewItem)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">Feedback Inbox</h1>
        <p className="text-sm text-muted-foreground mt-1">Review feedback submitted by Users from retrieval results</p>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search by strain or species..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      </div>

      <Tabs defaultValue="pending">
        <TabsList>
          <TabsTrigger value="pending" active={tab === 'pending'} onClick={() => setTab('pending')}>
            Pending ({feedbackItems.filter((f) => f.status === 'pending').length})
          </TabsTrigger>
          <TabsTrigger value="accepted" active={tab === 'accepted'} onClick={() => setTab('accepted')}>Accepted</TabsTrigger>
          <TabsTrigger value="rejected" active={tab === 'rejected'} onClick={() => setTab('rejected')}>Rejected</TabsTrigger>
          <TabsTrigger value="deferred" active={tab === 'deferred'} onClick={() => setTab('deferred')}>Deferred</TabsTrigger>
          <TabsTrigger value="all" active={tab === 'all'} onClick={() => setTab('all')}>All</TabsTrigger>
        </TabsList>

        <TabsContent value={tab} activeValue={tab}>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Submitter</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Strain</TableHead>
                    <TableHead>Predicted</TableHead>
                    <TableHead>Suggested</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((f) => (
                    <TableRow key={f.feedback_id}>
                      <TableCell className="text-xs">{new Date(f.created_at).toLocaleDateString()}</TableCell>
                      <TableCell className="font-medium">{f.submitter_name}</TableCell>
                      <TableCell>
                        <Badge variant={f.feedback_type === 'wrong_prediction' ? 'warning' : f.feedback_type === 'contribution' ? 'success' : 'secondary'}>
                          {f.feedback_type === 'wrong_prediction' ? 'Wrong Pred.' : f.feedback_type === 'contribution' ? 'Contribution' : 'Issue'}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{f.query_strain}</TableCell>
                      <TableCell>{f.predicted_species}</TableCell>
                      <TableCell>{f.suggested_species || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={f.status === 'pending' ? 'warning' : f.status === 'accepted' ? 'success' : f.status === 'rejected' ? 'destructive' : 'secondary'}>
                          {f.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => { setReviewItem(f.feedback_id); setReviewNote('') }}>
                            <Search className="h-4 w-4" />
                          </Button>
                          {f.status === 'pending' && (
                            <>
                              <Button variant="ghost" size="sm" className="text-success"><Check className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="sm" className="text-destructive"><X className="h-4 w-4" /></Button>
                              <Button variant="ghost" size="sm"><Clock className="h-4 w-4" /></Button>
                            </>
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

      {/* Review Dialog */}
      <Dialog open={reviewItem !== null} onClose={() => setReviewItem(null)}>
        <DialogHeader>
          <DialogTitle>Review Feedback</DialogTitle>
        </DialogHeader>
        {currentReview && (
          <DialogContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">Submitter:</span> {currentReview.submitter_name}</div>
              <div><span className="text-muted-foreground">Date:</span> {new Date(currentReview.created_at).toLocaleString()}</div>
              <div><span className="text-muted-foreground">Type:</span> <Badge variant={currentReview.feedback_type === 'wrong_prediction' ? 'warning' : 'success'}>{currentReview.feedback_type}</Badge></div>
              <div><span className="text-muted-foreground">Status:</span> <Badge variant="warning">{currentReview.status}</Badge></div>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label>Strain</Label>
              <p className="font-mono text-sm">{currentReview.query_strain}</p>
            </div>
            <div className="space-y-2">
              <Label>Media</Label>
              <p className="text-sm">{currentReview.media}</p>
            </div>
            <div className="space-y-2">
              <Label>Predicted Species</Label>
              <p className="text-sm">{currentReview.predicted_species}</p>
            </div>
            {currentReview.suggested_species && (
              <div className="space-y-2">
                <Label>Suggested Species</Label>
                <p className="text-sm">{currentReview.suggested_species}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label>Description</Label>
              <p className="text-sm">{currentReview.description}</p>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label>Sample Images</Label>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {datasetImages
                  .filter((img) => img.strain === currentReview.query_strain)
                  .slice(0, 5)
                  .map((img) => (
                    <img
                      key={img.image_id}
                      src={img.file_path}
                      alt={`${currentReview.query_strain} plate`}
                      className="h-24 w-32 rounded-md object-contain border border-border bg-muted flex-shrink-0"
                    />
                  ))}
                {datasetImages.filter((img) => img.strain === currentReview.query_strain).length === 0 && (
                  <p className="text-xs text-muted-foreground">No sample images available for this strain.</p>
                )}
              </div>
            </div>
            {currentReview.status === 'pending' && (
              <>
                <Separator />
                <div className="space-y-2">
                  <Label>Review Note</Label>
                  <Textarea value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="Optional note for audit..." />
                </div>
              </>
            )}
          </DialogContent>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setReviewItem(null)}>Close</Button>
          {currentReview?.status === 'pending' && (
            <>
              <Button variant="destructive" onClick={() => setReviewItem(null)}>Reject</Button>
              <Button variant="secondary" onClick={() => setReviewItem(null)}>Defer</Button>
              <Button onClick={() => setReviewItem(null)}>Accept</Button>
            </>
          )}
        </DialogFooter>
      </Dialog>
    </div>
  )
}

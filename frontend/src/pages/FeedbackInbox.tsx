import { useState } from 'react'
import { resolveImageUrl } from '@/lib/utils'
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
import { useFeedbackInbox, useReviewFeedback } from '@/hooks/use-feedback'
import type { FeedbackResponse } from '@/services/types'
import { datasetImages } from '@/lib/mock-data'
import { Check, X, Clock, Search } from 'lucide-react'

export default function FeedbackInboxPage() {
  const [tab, setTab] = useState('pending')
  const [search, setSearch] = useState('')
  const [reviewItem, setReviewItem] = useState<FeedbackResponse | null>(null)
  const [reviewNote, setReviewNote] = useState('')

  const { data, isLoading, isError } = useFeedbackInbox({ status: tab === 'all' ? undefined : tab })
  const reviewMutation = useReviewFeedback()

  const allItems = data?.items ?? []

  const filtered = allItems.filter((f) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      (f.query_strain ?? '').toLowerCase().includes(q) ||
      (f.predicted_species ?? '').toLowerCase().includes(q)
    )
  })

  const handleReview = (status: 'accepted' | 'rejected' | 'deferred') => {
    if (!reviewItem) return
    reviewMutation.mutate(
      { id: reviewItem.id, data: { status, review_note: reviewNote || null } },
      { onSuccess: () => setReviewItem(null) },
    )
  }

  const handleQuickReview = (id: string, status: 'accepted' | 'rejected' | 'deferred') => {
    reviewMutation.mutate({ id, data: { status } })
  }

  const pendingCount = tab === 'all' ? allItems.filter((f) => f.status === 'pending').length : 0

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
            Pending ({tab === 'pending' ? filtered.length : pendingCount})
          </TabsTrigger>
          <TabsTrigger value="accepted" active={tab === 'accepted'} onClick={() => setTab('accepted')}>Accepted</TabsTrigger>
          <TabsTrigger value="rejected" active={tab === 'rejected'} onClick={() => setTab('rejected')}>Rejected</TabsTrigger>
          <TabsTrigger value="deferred" active={tab === 'deferred'} onClick={() => setTab('deferred')}>Deferred</TabsTrigger>
          <TabsTrigger value="all" active={tab === 'all'} onClick={() => setTab('all')}>All</TabsTrigger>
        </TabsList>

        <TabsContent value={tab} activeValue={tab}>
          <Card>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="py-8 text-center text-muted-foreground">Loading...</div>
              ) : isError ? (
                <div className="py-8 text-center text-destructive">Failed to load feedback inbox.</div>
              ) : (
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
                    {filtered.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground py-8">No feedback to review.</TableCell>
                      </TableRow>
                    ) : (
                      filtered.map((f) => (
                        <TableRow key={f.id}>
                          <TableCell className="text-xs">{new Date(f.submitted_at).toLocaleDateString()}</TableCell>
                          <TableCell className="font-medium">{f.submitter_id.slice(0, 8)}</TableCell>
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
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => { setReviewItem(f); setReviewNote('') }}
                                disabled={reviewMutation.isPending}
                              >
                                <Search className="h-4 w-4" />
                              </Button>
                              {f.status === 'pending' && (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-success"
                                    onClick={() => handleQuickReview(f.id, 'accepted')}
                                    disabled={reviewMutation.isPending}
                                  >
                                    <Check className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-destructive"
                                    onClick={() => handleQuickReview(f.id, 'rejected')}
                                    disabled={reviewMutation.isPending}
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleQuickReview(f.id, 'deferred')}
                                    disabled={reviewMutation.isPending}
                                  >
                                    <Clock className="h-4 w-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Review Dialog */}
      <Dialog open={reviewItem !== null} onClose={() => setReviewItem(null)}>
        <DialogHeader>
          <DialogTitle>Review Feedback</DialogTitle>
        </DialogHeader>
        {reviewItem && (
          <DialogContent className="space-y-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">Submitter:</span> {reviewItem.submitter_id.slice(0, 12)}</div>
              <div><span className="text-muted-foreground">Date:</span> {new Date(reviewItem.submitted_at).toLocaleString()}</div>
              <div><span className="text-muted-foreground">Type:</span> <Badge variant={reviewItem.feedback_type === 'wrong_prediction' ? 'warning' : 'success'}>{reviewItem.feedback_type}</Badge></div>
              <div><span className="text-muted-foreground">Status:</span> <Badge variant="warning">{reviewItem.status}</Badge></div>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label>Strain</Label>
              <p className="font-mono text-sm">{reviewItem.query_strain}</p>
            </div>
            <div className="space-y-2">
              <Label>Predicted Species</Label>
              <p className="text-sm">{reviewItem.predicted_species}</p>
            </div>
            {reviewItem.suggested_species && (
              <div className="space-y-2">
                <Label>Suggested Species</Label>
                <p className="text-sm">{reviewItem.suggested_species}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label>Description</Label>
              <p className="text-sm">{reviewItem.description}</p>
            </div>
            <Separator />
            <div className="space-y-2">
              <Label>Sample Images</Label>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {datasetImages
                  .filter((img) => img.strain === reviewItem.query_strain)
                  .slice(0, 5)
                  .map((img) => (
                    <img
                       key={img.image_id}
                       src={resolveImageUrl(img.file_path)}
                      alt={`${reviewItem.query_strain} plate`}
                      className="h-24 w-32 rounded-md object-contain border border-border bg-muted flex-shrink-0"
                    />
                  ))}
                {datasetImages.filter((img) => img.strain === reviewItem.query_strain).length === 0 && (
                  <p className="text-xs text-muted-foreground">No sample images available for this strain.</p>
                )}
              </div>
            </div>
            {reviewItem.status === 'pending' && (
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
          {reviewItem?.status === 'pending' && (
            <>
              <Button variant="destructive" onClick={() => handleReview('rejected')} disabled={reviewMutation.isPending}>Reject</Button>
              <Button variant="secondary" onClick={() => handleReview('deferred')} disabled={reviewMutation.isPending}>Defer</Button>
              <Button onClick={() => handleReview('accepted')} disabled={reviewMutation.isPending}>Accept</Button>
            </>
          )}
        </DialogFooter>
      </Dialog>
    </div>
  )
}

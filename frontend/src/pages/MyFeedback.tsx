import { useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { useMyFeedback } from '@/hooks/use-feedback'

export default function MyFeedbackPage() {
  const [tab, setTab] = useState<string>('all')

  const statusParam = tab === 'all' ? undefined : tab
  const { data, isLoading, isError } = useMyFeedback({ status: statusParam })

  const items = data?.items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">My Feedback</h1>
        <p className="text-sm text-muted-foreground mt-1">Feedback you have submitted from retrieval results</p>
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all" active={tab === 'all'} onClick={() => setTab('all')}>All</TabsTrigger>
          <TabsTrigger value="pending" active={tab === 'pending'} onClick={() => setTab('pending')}>Pending</TabsTrigger>
          <TabsTrigger value="accepted" active={tab === 'accepted'} onClick={() => setTab('accepted')}>Accepted</TabsTrigger>
          <TabsTrigger value="rejected" active={tab === 'rejected'} onClick={() => setTab('rejected')}>Rejected</TabsTrigger>
          <TabsTrigger value="deferred" active={tab === 'deferred'} onClick={() => setTab('deferred')}>Deferred</TabsTrigger>
        </TabsList>

        <TabsContent value={tab} activeValue={tab}>
          <Card>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="py-8 text-center text-muted-foreground">Loading...</div>
              ) : isError ? (
                <div className="py-8 text-center text-destructive">Failed to load feedback.</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Strain</TableHead>
                      <TableHead>Predicted</TableHead>
                      <TableHead>Suggested</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center text-muted-foreground py-8">No feedback submitted yet.</TableCell>
                      </TableRow>
                    ) : (
                      items.map((f) => (
                        <TableRow key={f.id}>
                          <TableCell className="text-xs">{new Date(f.submitted_at).toLocaleDateString()}</TableCell>
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
    </div>
  )
}

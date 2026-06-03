import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/misc'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { indexStatus, candidateModels } from '@/lib/mock-data'
import { AlertTriangle, RefreshCw, Upload, Check, X } from 'lucide-react'

export default function ModelIndexPage() {
  const [reindexOpen, setReindexOpen] = useState(false)
  const [retrainOpen, setRetrainOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">Model & Index Maintenance</h1>
        <p className="text-sm text-muted-foreground mt-1">Qdrant index management and feature-extractor model governance</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Index Status Card */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Qdrant Index Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm">Status</span>
              <Badge variant={indexStatus.qdrant_index_status === 'current' ? 'success' : 'warning'}>
                {indexStatus.qdrant_index_status === 'needs_reindex' ? 'Needs Re-index' : indexStatus.qdrant_index_status}
              </Badge>
            </div>
            <Separator />
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Items Updated</span>
                <span className="font-mono">{indexStatus.changes_since_last_index.items_updated}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Items Archived</span>
                <span className="font-mono">{indexStatus.changes_since_last_index.items_archived}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Feedback Accepted</span>
                <span className="font-mono">{indexStatus.changes_since_last_index.feedback_accepted}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Contributions Accepted</span>
                <span className="font-mono">{indexStatus.changes_since_last_index.contributions_accepted}</span>
              </div>
            </div>
            <Separator />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Current Model</span>
              <span className="font-mono">{indexStatus.current_model_version}</span>
            </div>
            <Button size="sm" className="w-full" onClick={() => setReindexOpen(true)}>
              <RefreshCw className="h-4 w-4" /> Re-index Qdrant
            </Button>
          </CardContent>
        </Card>

        {/* Re-index Pre-flight Dialog */}
        <Dialog open={reindexOpen} onClose={() => setReindexOpen(false)}>
          <DialogHeader>
            <DialogTitle>Pre-flight Summary</DialogTitle>
          </DialogHeader>
          <DialogContent className="space-y-3">
            <p className="text-sm">Review changes before triggering Qdrant re-index:</p>
            <div className="space-y-1 text-sm bg-muted p-3 rounded-md">
              <div className="flex justify-between"><span>Active items to re-extract</span> <span className="font-mono">{indexStatus.changes_since_last_index.items_updated}</span></div>
              <div className="flex justify-between"><span>Items to exclude (archived)</span> <span className="font-mono">{indexStatus.changes_since_last_index.items_archived}</span></div>
              <div className="flex justify-between"><span>Feedback-driven updates</span> <span className="font-mono">{indexStatus.changes_since_last_index.feedback_accepted}</span></div>
            </div>
            <p className="text-xs text-muted-foreground">Re-indexing will re-extract features for active changed segments, update Qdrant points, and remove archived items.</p>
          </DialogContent>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReindexOpen(false)}>Cancel</Button>
            <Button onClick={() => setReindexOpen(false)}>Start Re-index</Button>
          </DialogFooter>
        </Dialog>

        {/* Retraining Card */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Feature Extractor Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active Model</span>
              <span className="font-mono">{indexStatus.current_model_version}</span>
            </div>
            <Separator />

            {indexStatus.external_retraining_recommended && (
              <div className="flex items-start gap-2 p-3 bg-warning/10 border border-warning/20 rounded-md">
                <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-medium">External deep feature-extractor retraining is recommended</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Many reference-data changes have accumulated. Retraining should be performed externally, then the new model uploaded as a Candidate Model.
                  </p>
                  <Button variant="outline" size="sm" className="mt-2" onClick={() => setRetrainOpen(true)}>
                    View Retraining Guidance
                  </Button>
                </div>
              </div>
            )}

            {/* Candidate Models */}
            <div>
              <h4 className="text-sm font-medium mb-2">Candidate Models</h4>
              <div className="space-y-2">
                {candidateModels.map((cm) => (
                  <div key={cm.candidate_model_id} className="flex items-center justify-between p-3 border border-border rounded-md">
                    <div>
                      <p className="font-mono text-sm">{cm.version}</p>
                      <p className="text-xs text-muted-foreground">
                        {cm.candidate_metrics ? `Current F1: ${cm.current_metrics.f1} → Candidate F1: ${cm.candidate_metrics.f1}` : 'Awaiting evaluation'}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <Badge variant={cm.status === 'accepted' ? 'success' : cm.status === 'rejected' ? 'destructive' : cm.status === 'evaluating' ? 'warning' : 'secondary'}>
                        {cm.status}
                      </Badge>
                      {cm.status === 'evaluating' && (
                        <div className="flex gap-1 ml-2">
                          <Button variant="ghost" size="sm" className="text-success"><Check className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="sm" className="text-destructive"><X className="h-4 w-4" /></Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Button variant="outline" size="sm" className="w-full">
              <Upload className="h-4 w-4" /> Upload Candidate Model
            </Button>
          </CardContent>
        </Card>

        {/* Retraining Guidance Dialog */}
        <Dialog open={retrainOpen} onClose={() => setRetrainOpen(false)}>
          <DialogHeader>
            <DialogTitle>External Retraining Guidance</DialogTitle>
          </DialogHeader>
          <DialogContent className="space-y-3">
            <p className="text-sm text-muted-foreground">Deep feature-extractor retraining is performed outside MycoAI Retrieval. Use this Python guidance:</p>
            <div className="bg-muted p-3 rounded-md font-mono text-xs space-y-1 overflow-auto max-h-60">
              <p>1. Download active dataset via the Dataset Browser export</p>
              <p>2. Retrain feature extractor externally:</p>
              <p className="pl-4 text-muted-foreground">{`   python train.py --dataset ./export/ \\`}</p>
              <p className="pl-4 text-muted-foreground">{`     --model efficientnet-b1 \\`}</p>
              <p className="pl-4 text-muted-foreground">{`     --epochs 50 --lr 0.001`}</p>
              <p>3. Upload retrained model as Candidate Model</p>
              <p>4. Assess against fixed evaluation set</p>
              <p>5. Manually promote if metrics improve</p>
            </div>
            <p className="text-xs text-muted-foreground">System does not trigger deep retraining. Upload the retrained model artifact above as a Candidate Model.</p>
          </DialogContent>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRetrainOpen(false)}>Close</Button>
          </DialogFooter>
        </Dialog>
      </div>

      {/* Evaluation Metrics Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="font-heading text-base">Latest Evaluation Metrics</CardTitle>
          <CardDescription>From fixed evaluation set</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'F1 Score', value: '0.89', model: indexStatus.current_model_version },
              { label: 'Precision', value: '0.91', model: indexStatus.current_model_version },
              { label: 'Recall', value: '0.87', model: indexStatus.current_model_version },
              { label: 'Eval Set Size', value: '250', model: 'images' },
            ].map((m) => (
              <div key={m.label} className="text-center">
                <p className="text-2xl font-bold font-heading">{m.value}</p>
                <p className="text-xs text-muted-foreground">{m.label}</p>
                <p className="text-xs font-mono text-muted-foreground">{m.model}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/misc'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { AlertTriangle, RefreshCw, Upload, Check, X, ShieldAlert } from 'lucide-react'
import { useTrainingStatus, useTrainingJobs, useTriggerTraining, useCancelJob, useDeployModel } from '@/hooks/use-training'
import { useIndexStatus, useTriggerReindex } from '@/hooks/use-index'
import { useAuth } from '@/lib/use-auth'

function statusBadgeVariant(status: string) {
  if (status === 'current' || status === 'completed') return 'success' as const
  if (status === 'failed' || status === 'rejected') return 'destructive' as const
  if (status === 'running' || status === 'evaluating') return 'warning' as const
  return 'secondary' as const
}

export default function ModelIndexPage() {
  const { user } = useAuth()
  const isOwner = user?.role === 'owner' || user?.role === 'dataowner'
  const [reindexOpen, setReindexOpen] = useState(false)
  const [retrainOpen, setRetrainOpen] = useState(false)

  const { data: trainingStatus, isLoading: tsLoading } = useTrainingStatus()
  const { data: jobs = [], isLoading: jobsLoading } = useTrainingJobs()
  const { data: indexStatus, isLoading: isLoading } = useIndexStatus()
  const triggerTraining = useTriggerTraining()
  const triggerReindex = useTriggerReindex()
  const cancelJob = useCancelJob()
  const deployModel = useDeployModel()

  const currentModel = trainingStatus
    ? `${trainingStatus.model_name} ${trainingStatus.version}`
    : '—'

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
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : indexStatus ? (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Status</span>
                  <Badge variant={statusBadgeVariant(indexStatus.qdrant_index_status)}>
                    {indexStatus.qdrant_index_status === 'needs_reindex' ? 'Needs Re-index' : indexStatus.qdrant_index_status}
                  </Badge>
                </div>
                <Separator />
                <div className="space-y-2 text-sm">
                  {Object.entries(indexStatus.changes_since_last ?? {}).map(([key, count]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="font-mono">{count}</span>
                    </div>
                  ))}
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Current Model</span>
                  <span className="font-mono">{currentModel}</span>
                </div>
                {isOwner ? (
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => setReindexOpen(true)}
                    disabled={triggerReindex.isPending}
                  >
                    <RefreshCw className="h-4 w-4" /> Re-index Qdrant
                  </Button>
                ) : (
                  <p className="text-xs text-muted-foreground text-center py-2">
                    <ShieldAlert className="h-3 w-3 inline mr-1" />
                    Data Owner access required for re-indexing
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Index status unavailable</p>
            )}
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
              {indexStatus ? (
                Object.entries(indexStatus.changes_since_last ?? {}).map(([key, count]) => (
                  <div key={key} className="flex justify-between">
                    <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-mono">{count}</span>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">No change data available</p>
              )}
            </div>
            <p className="text-xs text-muted-foreground">Re-indexing will re-extract features for changed segments, update Qdrant points, and remove archived items.</p>
          </DialogContent>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReindexOpen(false)}>Cancel</Button>
            <Button
              onClick={() => {
                triggerReindex.mutate('changed', {
                  onSuccess: () => setReindexOpen(false),
                })
              }}
              disabled={triggerReindex.isPending}
            >
              Start Re-index
            </Button>
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
              <span className="font-mono">{tsLoading ? 'Loading…' : currentModel}</span>
            </div>
            <Separator />

            {indexStatus?.external_retraining_recommended && (
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

            {/* Training Jobs */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium">Training Jobs</h4>
                {isOwner && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => triggerTraining.mutate(undefined)}
                    disabled={triggerTraining.isPending}
                  >
                    {triggerTraining.isPending ? 'Starting…' : 'Trigger Training'}
                  </Button>
                )}
              </div>
              {jobsLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : jobs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No training jobs</p>
              ) : (
                <div className="space-y-2">
                  {jobs.map((job) => (
                    <div key={job.id} className="flex items-center justify-between p-3 border border-border rounded-md">
                      <div>
                        <p className="font-mono text-sm">{job.id}</p>
                        <p className="text-xs text-muted-foreground">
                          {job.completed_at
                            ? `Completed ${new Date(job.completed_at).toLocaleDateString()}`
                            : job.started_at
                              ? `Started ${new Date(job.started_at).toLocaleDateString()}`
                              : 'Queued'}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Badge variant={statusBadgeVariant(job.status)}>
                          {job.status}
                        </Badge>
                        {isOwner && job.status === 'running' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => cancelJob.mutate(job.id)}
                            disabled={cancelJob.isPending}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                        {isOwner && job.status === 'completed' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-success"
                            onClick={() => deployModel.mutate({ jobId: job.id })}
                            disabled={deployModel.isPending}
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {isOwner && (
              <Button variant="outline" size="sm" className="w-full">
                <Upload className="h-4 w-4" /> Upload Candidate Model
              </Button>
            )}
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
              { label: 'F1 Score', value: '0.89', model: currentModel },
              { label: 'Precision', value: '0.91', model: currentModel },
              { label: 'Recall', value: '0.87', model: currentModel },
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

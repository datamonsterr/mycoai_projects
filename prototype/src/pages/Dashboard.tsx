import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/misc'
import { speciesList, mediaList, datasetImages, indexStatus, users } from '@/lib/mock-data'
import { FlaskConical, Database, AlertTriangle, Image, Tags, Users } from 'lucide-react'

const COLORS = ['#3B82F6', '#D97706', '#16A34A', '#DC2626', '#8B5CF6', '#06B6D4', '#F59E0B', '#EC4899', '#6366F1', '#10B981']

function PieChart({ data }: { data: Array<{ name: string; count: number }> }) {
  const [showPercent, setShowPercent] = useState(false)
  const total = useMemo(() => data.reduce((s, d) => s + d.count, 0), [data])

  const segments = useMemo(() => {
    if (total === 0) return []
    let cumulative = 0
    return data.map((d) => {
      const startAngle = (cumulative / total) * 360
      cumulative += d.count
      const endAngle = (cumulative / total) * 360
      return { ...d, startAngle, endAngle }
    })
  }, [data, total])

  const toCoords = (angle: number, r: number, cx: number, cy: number) => ({
    x: cx + r * Math.cos((angle - 90) * (Math.PI / 180)),
    y: cy + r * Math.sin((angle - 90) * (Math.PI / 180)),
  })

  const describeArc = (start: number, end: number, r: number, cx: number, cy: number) => {
    const large = end - start > 180 ? 1 : 0
    const s = toCoords(start, r, cx, cy)
    const e = toCoords(end, r, cx, cy)
    return `M ${cx} ${cy} L ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y} Z`
  }

  const labelArc = (start: number, end: number, r: number, cx: number, cy: number) => {
    const mid = (start + end) / 2
    return toCoords(mid, r * 0.65, cx, cy)
  }

  const cx = 140; const cy = 140; const r = 110

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className="relative cursor-pointer select-none"
        onClick={() => setShowPercent(!showPercent)}
        title="Click to toggle percent / quantity"
      >
        <svg width={280} height={280} viewBox="0 0 280 280">
          {segments.map((seg, i) => (
            <path
              key={seg.name}
              d={describeArc(seg.startAngle, seg.endAngle, r, cx, cy)}
              fill={COLORS[i % COLORS.length]}
              stroke="var(--color-card)"
              strokeWidth={2}
              className="transition-all duration-300 hover:opacity-80"
            />
          ))}
          <circle cx={cx} cy={cy} r={r * 0.55} fill="var(--color-card)" />
          <text x={cx} y={cy - 8} textAnchor="middle" className="fill-foreground font-heading text-lg font-bold" fontSize={18}>
            {total}
          </text>
          <text x={cx} y={cy + 14} textAnchor="middle" className="fill-muted-foreground" fontSize={11}>
            {showPercent ? 'percent' : 'images'}
          </text>
          {segments.map((seg) => {
            const pos = labelArc(seg.startAngle, seg.endAngle, r, cx, cy)
            const pct = ((seg.count / total) * 100).toFixed(0)
            return (
              <g key={`label-${seg.name}`}>
                <rect
                  x={pos.x - (showPercent ? 18 : 14)}
                  y={pos.y - 10}
                  width={showPercent ? 36 : 28}
                  height={18}
                  rx={4}
                  fill="var(--color-card)"
                  opacity={0.9}
                />
                <text
                  x={pos.x}
                  y={pos.y + 4}
                  textAnchor="middle"
                  className="fill-foreground"
                  fontSize={10}
                  fontFamily="monospace"
                >
                  {showPercent ? `${pct}%` : seg.count}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 w-full">
        {segments.map((seg, i) => (
          <div key={seg.name} className="flex items-center gap-2 text-xs">
            <span className="h-3 w-3 rounded-sm flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
            <span className="truncate">{seg.name}</span>
            <span className="font-mono ml-auto">
              {showPercent ? `${((seg.count / total) * 100).toFixed(0)}%` : seg.count}
            </span>
          </div>
        ))}
      </div>
      <p className="text-[10px] text-muted-foreground">Click chart to toggle percent / quantity</p>
    </div>
  )
}

export default function DashboardPage() {
  const strainCount = new Set(datasetImages.map((d) => d.strain)).size
  const metrics = [
    { label: 'Total Strains', value: strainCount, icon: FlaskConical, color: 'text-primary' },
    { label: 'Total Images', value: datasetImages.length, icon: Image, color: 'text-secondary' },
    { label: 'Images / Strain', value: (datasetImages.length / strainCount).toFixed(1), icon: Image, color: 'text-secondary' },
    { label: 'Total Species', value: speciesList.filter((s) => !s.is_archived).length, icon: Tags, color: 'text-success' },
    { label: 'Media Types', value: mediaList.filter((m) => !m.is_archived).length, icon: Database, color: 'text-warning' },
    { label: 'Active Users', value: users.filter((u) => u.account_status === 'active').length, icon: Users, color: 'text-primary' },
    { label: 'Needs Reindex', value: indexStatus.changes_since_last_index.items_updated, icon: AlertTriangle, color: 'text-destructive' },
  ]

  const speciesData = speciesList
    .filter((s) => !s.is_archived)
    .map((species) => ({
      name: species.name,
      count: datasetImages.filter((d) => d.species_id === species.species_id && d.data_update_status !== 'archived').length,
    }))
    .filter((d) => d.count > 0)

  const mediaData = mediaList
    .filter((m) => !m.is_archived)
    .map((media) => ({
      name: media.name,
      count: datasetImages.filter((d) => d.media_id === media.media_id && d.data_update_status !== 'archived').length,
    }))
    .filter((d) => d.count > 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Dataset and index overview</p>
      </div>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((m) => (
          <Card key={m.label} className="flex items-stretch">
            <CardContent className="p-4 flex items-center gap-4 w-full">
              <m.icon className={`h-8 w-8 flex-shrink-0 ${m.color}`} />
              <div>
                <p className="text-2xl font-bold font-heading">{m.value}</p>
                <p className="text-xs text-muted-foreground">{m.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Index Status */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Index Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Qdrant Index</span>
              <Badge variant={indexStatus.qdrant_index_status === 'current' ? 'success' : 'warning'}>
                {indexStatus.qdrant_index_status === 'needs_reindex' ? 'Needs Re-index' : indexStatus.qdrant_index_status}
              </Badge>
            </div>
            <Separator />
            <div className="space-y-1 text-sm">
              <div className="flex justify-between"><span>Items Updated</span> <span className="font-mono">{indexStatus.changes_since_last_index.items_updated}</span></div>
              <div className="flex justify-between"><span>Items Archived</span> <span className="font-mono">{indexStatus.changes_since_last_index.items_archived}</span></div>
              <div className="flex justify-between"><span>Feedback Accepted</span> <span className="font-mono">{indexStatus.changes_since_last_index.feedback_accepted}</span></div>
              <div className="flex justify-between"><span>Contributions Accepted</span> <span className="font-mono">{indexStatus.changes_since_last_index.contributions_accepted}</span></div>
            </div>
            <Separator />
            <div>
              <span className="text-sm">Current Model:</span>
              <span className="ml-2 font-mono text-sm">{indexStatus.current_model_version}</span>
            </div>
            {indexStatus.external_retraining_recommended && (
              <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-md">
                <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0" />
                <p className="text-xs text-foreground">
                  External deep feature-extractor retraining is recommended. Many reference-data changes have accumulated.
                </p>
              </div>
            )}
            <Button size="sm" className="w-full">Re-index Qdrant</Button>
          </CardContent>
        </Card>

        {/* Species Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Species Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {speciesData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No species data available.</p>
            ) : (
              <PieChart data={speciesData} />
            )}
          </CardContent>
        </Card>

        {/* Media Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Media Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {mediaData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No media data available.</p>
            ) : (
              <PieChart data={mediaData} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Data Update Status */}
      <Card>
        <CardHeader>
          <CardTitle className="font-heading text-base">Data Update Status</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Image ID</TableHead>
                <TableHead>Strain</TableHead>
                <TableHead>Species</TableHead>
                <TableHead>Media</TableHead>
                <TableHead>Segments</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datasetImages.map((img) => {
                const species = speciesList.find((s) => s.species_id === img.species_id)
                const media = mediaList.find((m) => m.media_id === img.media_id)
                return (
                  <TableRow key={img.image_id}>
                    <TableCell className="font-mono text-xs">{img.image_id}</TableCell>
                    <TableCell className="font-mono text-xs">{img.strain}</TableCell>
                    <TableCell>{species?.name ?? '-'}</TableCell>
                    <TableCell>{media?.name ?? '-'}</TableCell>
                    <TableCell>{img.segments.length}</TableCell>
                    <TableCell>
                      <Badge variant={
                        img.data_update_status === 'current' ? 'success' :
                          img.data_update_status === 'updated_requires_reindex' ? 'warning' : 'destructive'
                      }>
                        {img.data_update_status === 'updated_requires_reindex' ? 'Needs Reindex' : img.data_update_status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/misc'
import {
  useDashboardStats,
  useSpeciesDistribution,
  useMediaDistribution,
  useStrainDistribution,
  useQdrantStatus,
} from '@/hooks/use-dashboard'
import { useAuth } from '@/lib/use-auth'
import { FlaskConical, Database, AlertTriangle, Image, Tags } from 'lucide-react'

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
  const { user } = useAuth()
  const isOwner = user?.role === 'owner' || user?.role === 'dataowner'
  const { data: stats, isLoading: statsLoading } = useDashboardStats()
  const { data: qdrantStatus, isLoading: qdrantLoading } = useQdrantStatus()
  const { data: speciesDist, isLoading: speciesLoading } = useSpeciesDistribution()
  const { data: mediaDist, isLoading: mediaLoading } = useMediaDistribution()
  const { data: strainDist, isLoading: strainLoading } = useStrainDistribution()

  const metrics = [
    { label: 'Total Strains', value: statsLoading ? '…' : stats?.total_strains ?? '-', icon: FlaskConical, color: 'text-primary' },
    { label: 'Total Images', value: statsLoading ? '…' : stats?.total_images ?? '-', icon: Image, color: 'text-secondary' },
    {
      label: 'Images / Strain',
      value: statsLoading || !stats || stats.total_strains === 0
        ? '…'
        : (stats.total_images / stats.total_strains).toFixed(1),
      icon: Image,
      color: 'text-secondary',
    },
    { label: 'Total Species', value: statsLoading ? '…' : stats?.total_species ?? '-', icon: Tags, color: 'text-success' },
    { label: 'Media Types', value: statsLoading ? '…' : stats?.total_media ?? '-', icon: Database, color: 'text-warning' },
    {
      label: 'Needs Reindex',
      value: qdrantLoading ? '…' : qdrantStatus?.qdrant_index_status !== 'current' ? 'Yes' : 'No',
      icon: AlertTriangle,
      color: 'text-destructive',
    },
  ]

  const speciesData = useMemo(
    () =>
      speciesDist?.map((d) => ({
        name: d.species_name ?? 'Unknown',
        count: d.image_count,
      })).filter((d) => d.count > 0) ?? [],
    [speciesDist],
  )

  const mediaData = useMemo(
    () =>
      mediaDist?.map((d) => ({
        name: d.media_name ?? 'Unknown',
        count: d.image_count,
      })).filter((d) => d.count > 0) ?? [],
    [mediaDist],
  )

  const strainData = useMemo(
    () =>
      strainDist?.map((d) => ({
        name: d.strain_name ?? 'Unknown',
        count: d.image_count,
      })).filter((d) => d.count > 0) ?? [],
    [strainDist],
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Dataset and index overview</p>
      </div>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 auto-rows-fr">
        {metrics.map((m) => (
          <Card key={m.label} className="h-full">
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

      {/* Index Status — dedicated row */}
      <Card>
        <CardHeader>
          <CardTitle className="font-heading text-base">Index Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {qdrantLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : qdrantStatus ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm">Qdrant Index</span>
                <Badge variant={qdrantStatus.qdrant_index_status === 'current' ? 'success' : 'warning'}>
                  {qdrantStatus.qdrant_index_status}
                </Badge>
              </div>
              <Separator />
              <div className="space-y-1 text-sm">
                {Object.entries(qdrantStatus.changes_since_last ?? {}).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-mono">{val}</span>
                  </div>
                ))}
              </div>
              {qdrantStatus.external_retraining_recommended && (
                <>
                  <Separator />
                  <div className="flex items-center gap-2 p-3 bg-warning/10 border border-warning/20 rounded-md">
                    <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0" />
                    <p className="text-xs text-foreground">
                      External deep feature-extractor retraining is recommended. Many reference-data changes have accumulated.
                    </p>
                  </div>
                </>
              )}
              {isOwner && (
                <Button size="sm" className="w-full">Re-index Qdrant</Button>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No index status available.</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Species Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Species Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {speciesLoading ? (
              <p className="text-sm text-muted-foreground text-center py-8">Loading...</p>
            ) : speciesData.length === 0 ? (
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
            {mediaLoading ? (
              <p className="text-sm text-muted-foreground text-center py-8">Loading...</p>
            ) : mediaData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No media data available.</p>
            ) : (
              <PieChart data={mediaData} />
            )}
          </CardContent>
        </Card>

        {/* Strain Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="font-heading text-base">Strain Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {strainLoading ? (
              <p className="text-sm text-muted-foreground text-center py-8">Loading...</p>
            ) : strainData.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No strain data available.</p>
            ) : (
              <PieChart data={strainData} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useAuditLog } from '@/hooks/use-admin'
import type { AuditLogResponse } from '@/services/types'
import { Search, Loader2 } from 'lucide-react'

export default function AuditLogPage() {
  const [search, setSearch] = useState('')

  const { data, isLoading, isError } = useAuditLog()
  const logs = data?.items ?? []

  const filtered = logs.filter((a) =>
    !search ||
    a.action.toLowerCase().includes(search.toLowerCase()) ||
    a.entity_type.toLowerCase().includes(search.toLowerCase()) ||
    (a.entity_id?.toLowerCase().includes(search.toLowerCase())) ||
    a.user_id.toLowerCase().includes(search.toLowerCase())
  )

  const formatDetails = (changes: Record<string, unknown> | null): string => {
    if (!changes) return '-'
    try {
      return JSON.stringify(changes)
    } catch {
      return '-'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-foreground">Audit Log</h1>
        <p className="text-sm text-muted-foreground mt-1">Complete record of all Data Owner mutations</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search audit entries..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading audit log...</span>
          </CardContent>
        </Card>
      ) : isError ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <p className="text-sm text-destructive">Failed to load audit log. Please try again.</p>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <p className="text-sm text-muted-foreground">No audit entries found.</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((a: AuditLogResponse) => (
                  <TableRow key={a.id}>
                    <TableCell className="text-xs font-mono whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</TableCell>
                    <TableCell className="text-sm">{a.user_id}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {a.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {a.entity_type}{a.entity_id ? ` #${a.entity_id}` : ''}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                      {formatDetails(a.changes)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

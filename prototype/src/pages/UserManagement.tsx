import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { users } from '@/lib/mock-data'
import { UserPlus, Shield, ShieldOff, Ban, CheckCircle, Search } from 'lucide-react'

export default function UserManagementPage() {
  const [search, setSearch] = useState('')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [promoteOpen, setPromoteOpen] = useState<string | null>(null)

  const filtered = users.filter((u) =>
    !search || u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">User Management</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage users and role assignments</p>
        </div>
        <Button size="sm" onClick={() => setInviteOpen(true)}>
          <UserPlus className="h-4 w-4" /> Invite User
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((u) => (
                <TableRow key={u.user_id} className={u.account_status === 'inactive' ? 'opacity-50' : ''}>
                  <TableCell className="font-medium">{u.name}</TableCell>
                  <TableCell className="text-sm">{u.email}</TableCell>
                  <TableCell>
                    <Badge variant={u.role === 'owner' ? 'default' : 'secondary'}>
                      {u.role === 'owner' ? 'Data Owner' : 'User'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.account_status === 'active' ? 'success' : 'destructive'}>
                      {u.account_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs">{new Date(u.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {u.role === 'user' ? (
                        <Button variant="ghost" size="sm" onClick={() => setPromoteOpen(u.user_id)} title="Promote to Data Owner">
                          <Shield className="h-4 w-4 text-warning" />
                        </Button>
                      ) : (
                        <Button variant="ghost" size="sm" title="Demote to User" disabled={users.filter((x) => x.role === 'owner' && x.account_status === 'active').length <= 1}>
                          <ShieldOff className="h-4 w-4" />
                        </Button>
                      )}
                      {u.account_status === 'active' ? (
                        <Button variant="ghost" size="sm" className="text-destructive" title="Deactivate" disabled={u.role === 'owner' && users.filter((x) => x.role === 'owner' && x.account_status === 'active').length <= 1}>
                          <Ban className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button variant="ghost" size="sm" className="text-success" title="Reactivate">
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Invite Dialog */}
      <Dialog open={inviteOpen} onClose={() => setInviteOpen(false)}>
        <DialogHeader>
          <DialogTitle>Invite User</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground mb-3">Send an onboarding email to invite a new User.</p>
          <Input placeholder="user@example.com" type="email" />
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={() => setInviteOpen(false)}>Cancel</Button>
          <Button onClick={() => setInviteOpen(false)}>Send Invitation</Button>
        </DialogFooter>
      </Dialog>

      {/* Promote Dialog */}
      <Dialog open={promoteOpen !== null} onClose={() => setPromoteOpen(null)}>
        <DialogHeader>
          <DialogTitle>Promote to Data Owner</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground">
            This will grant {users.find((u) => u.user_id === promoteOpen)?.name} full governance capabilities including metadata management, dataset control, feedback review, and user management.
          </p>
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={() => setPromoteOpen(null)}>Cancel</Button>
          <Button onClick={() => setPromoteOpen(null)}>Promote</Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}

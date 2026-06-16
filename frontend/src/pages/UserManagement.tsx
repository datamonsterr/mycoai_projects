import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '@/components/ui/dialog'
import { useUsersList, useUpdateUserRole, useUpdateUserStatus } from '@/hooks/use-admin'
import { inviteUser } from '@/services/admin'
import { useToast } from '@/hooks/use-toast'
import type { AdminUserResponse } from '@/services/types'
import { UserPlus, Shield, ShieldOff, Ban, CheckCircle, Search, Loader2 } from 'lucide-react'

export default function UserManagementPage() {
  const [search, setSearch] = useState('')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviting, setInviting] = useState(false)
  const [pendingUserId, setPendingUserId] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<'promote' | 'demote' | 'activate' | 'deactivate' | null>(null)

  const { data, isLoading, isError } = useUsersList()
  const roleMutation = useUpdateUserRole()
  const statusMutation = useUpdateUserStatus()
  const toast = useToast()

  const users = data?.items ?? []

  const filtered = users.filter((u) =>
    !search || u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase())
  )

  const activeOwners = users.filter((u) => (u.role === 'owner' || u.role === 'dataowner') && u.is_active).length

  const pendingUser = users.find((u) => u.id === pendingUserId) ?? null

  const openConfirm = (userId: string, action: 'promote' | 'demote' | 'activate' | 'deactivate') => {
    setPendingUserId(userId)
    setPendingAction(action)
  }

  const closeConfirm = () => {
    setPendingUserId(null)
    setPendingAction(null)
  }

  const handleConfirm = () => {
    if (!pendingUserId || !pendingAction) return
    if (pendingAction === 'promote') {
      roleMutation.mutate({ userId: pendingUserId, data: { role: 'owner' } })
    } else if (pendingAction === 'demote') {
      roleMutation.mutate({ userId: pendingUserId, data: { role: 'user' } })
    } else if (pendingAction === 'activate') {
      statusMutation.mutate({ userId: pendingUserId, data: { is_active: true } })
    } else if (pendingAction === 'deactivate') {
      statusMutation.mutate({ userId: pendingUserId, data: { is_active: false } })
    }
    closeConfirm()
  }

  const dialogTitle =
    pendingAction === 'promote' ? 'Promote to Data Owner' :
    pendingAction === 'demote' ? 'Demote to User' :
    pendingAction === 'activate' ? 'Reactivate User' :
    pendingAction === 'deactivate' ? 'Deactivate User' : ''

  const dialogBody =
    pendingAction === 'promote'
      ? `Grant ${pendingUser?.name ?? ''} full governance capabilities including metadata management, dataset control, feedback review, and user management.`
    : pendingAction === 'demote'
      ? `Downgrade ${pendingUser?.name ?? ''} to regular User. They will lose Data Owner privileges.`
    : pendingAction === 'activate'
      ? `Reactivate ${pendingUser?.name ?? ''}'s account. They will be able to log in again.`
    : pendingAction === 'deactivate'
      ? `Deactivate ${pendingUser?.name ?? ''}'s account. They will not be able to log in.`
    : ''

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      const result = await inviteUser(inviteEmail.trim())
      setInviteOpen(false)
      setInviteEmail('')
      toast.success(`Invite sent to ${result.email}. Link: ${result.invite_link}`)
    } catch (err) {
      toast.apiError(err, 'Failed to invite user')
    } finally {
      setInviting(false)
    }
  }

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

      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading users...</span>
          </CardContent>
        </Card>
      ) : isError ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <p className="text-sm text-destructive">Failed to load users. Please try again.</p>
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <p className="text-sm text-muted-foreground">No users found.</p>
          </CardContent>
        </Card>
      ) : (
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
                {filtered.map((u: AdminUserResponse) => (
                  <TableRow key={u.id} className={!u.is_active ? 'opacity-50' : ''}>
                    <TableCell className="font-medium">{u.name}</TableCell>
                    <TableCell className="text-sm">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={u.role === 'owner' || u.role === 'dataowner' ? 'default' : 'secondary'}>
                        {u.role === 'owner' || u.role === 'dataowner' ? 'Data Owner' : 'User'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? 'success' : 'destructive'}>
                        {u.is_active ? 'active' : 'inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">{new Date(u.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {u.role === 'user' ? (
                          <Button variant="ghost" size="sm" onClick={() => openConfirm(u.id, 'promote')} title="Promote to Data Owner">
                            <Shield className="h-4 w-4 text-warning" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Demote to User"
                            disabled={activeOwners <= 1}
                            onClick={() => openConfirm(u.id, 'demote')}
                          >
                            <ShieldOff className="h-4 w-4" />
                          </Button>
                        )}
                        {u.is_active ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            title="Deactivate"
                            disabled={(u.role === 'owner' || u.role === 'dataowner') && activeOwners <= 1}
                            onClick={() => openConfirm(u.id, 'deactivate')}
                          >
                            <Ban className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button variant="ghost" size="sm" className="text-success" title="Reactivate" onClick={() => openConfirm(u.id, 'activate')}>
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
      )}

      {/* Invite Dialog */}
      <Dialog open={inviteOpen} onClose={() => { setInviteOpen(false); setInviteEmail('') }}>
        <DialogHeader>
          <DialogTitle>Invite User</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground mb-3">Send an onboarding email to invite a new User.</p>
          <Input
            placeholder="user@example.com"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setInviteOpen(false); setInviteEmail('') }}>Cancel</Button>
          <Button onClick={handleInvite} disabled={inviting || !inviteEmail.trim()}>
            {inviting ? <><Loader2 className="h-4 w-4 animate-spin mr-1" /> Sending...</> : 'Send Invitation'}
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Confirm Dialog */}
      <Dialog open={pendingUserId !== null} onClose={closeConfirm}>
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
        </DialogHeader>
        <DialogContent>
          <p className="text-sm text-muted-foreground">{dialogBody}</p>
        </DialogContent>
        <DialogFooter>
          <Button variant="outline" onClick={closeConfirm}>Cancel</Button>
          <Button onClick={handleConfirm} disabled={roleMutation.isPending || statusMutation.isPending}>
            {roleMutation.isPending || statusMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-1" /> Saving...
              </>
            ) : (
              'Confirm'
            )}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}

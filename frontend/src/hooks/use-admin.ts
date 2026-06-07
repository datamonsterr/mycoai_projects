import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { listUsers, updateUserRole, updateUserStatus, getAuditLog } from '@/services/admin'
import type { UserRoleUpdate, UserStatusUpdate } from '@/services/types'

interface UsersListParams {
  offset?: number
  limit?: number
  role?: string
  is_active?: boolean
}

interface AuditLogParams {
  entity_type?: string
  entity_id?: string
  user_id?: string
  offset?: number
  limit?: number
}

export function useUsersList(params?: UsersListParams) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => listUsers(params),
  })
}

export function useUpdateUserRole() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserRoleUpdate }) =>
      updateUserRole(userId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success('User role updated')
    },
    onError: () => {
      toast.error('Failed to update user role')
    },
  })
}

export function useUpdateUserStatus() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserStatusUpdate }) =>
      updateUserStatus(userId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'users'] })
      toast.success('User status updated')
    },
    onError: () => {
      toast.error('Failed to update user status')
    },
  })
}

export function useAuditLog(params?: AuditLogParams) {
  return useQuery({
    queryKey: ['admin', 'audit-log', params],
    queryFn: () => getAuditLog(params),
  })
}

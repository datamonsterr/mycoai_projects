import { api } from '@/services/api-client'
import type {
  AdminUserResponse,
  AuditLogResponse,
  InviteUserResponse,
  PaginatedResponse,
  UserRoleUpdate,
  UserStatusUpdate,
} from '@/services/types'

interface ListUsersParams {
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

export function listUsers(
  params?: ListUsersParams,
): Promise<PaginatedResponse<AdminUserResponse>> {
  return api.get<PaginatedResponse<AdminUserResponse>>('/admin/users', { params: params as Record<string, string | number | boolean | undefined> })
}

export function updateUserRole(
  userId: string,
  data: UserRoleUpdate,
): Promise<AdminUserResponse> {
  return api.patch<AdminUserResponse>(`/admin/users/${userId}/role`, data)
}

export function updateUserStatus(
  userId: string,
  data: UserStatusUpdate,
): Promise<AdminUserResponse> {
  return api.patch<AdminUserResponse>(`/admin/users/${userId}/status`, data)
}

export function getAuditLog(
  params?: AuditLogParams,
): Promise<PaginatedResponse<AuditLogResponse>> {
  return api.get<PaginatedResponse<AuditLogResponse>>('/admin/audit-log', { params: params as Record<string, string | number | boolean | undefined> })
}

export function inviteUser(
  email: string,
): Promise<InviteUserResponse> {
  return api.post<InviteUserResponse>('/admin/users/invite', { email })
}

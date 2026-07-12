import { api } from './api-client'
import type { DeleteImpact, PaginatedResponse, StrainCreateRequest, StrainItem } from './types'

export const strains = {
  list(params?: {
    offset?: number
    limit?: number
    species_id?: string
    is_archived?: boolean
    search?: string
  }) {
    return api.get<PaginatedResponse<StrainItem>>('/strains', { params })
  },

  create(data: StrainCreateRequest) {
    return api.post<StrainItem>('/strains', data)
  },

  get(id: string) {
    return api.get<StrainItem>(`/strains/${id}`)
  },

  archive(id: string) {
    return api.delete(`/strains/${id}`)
  },

  getDeleteImpact(id: string) {
    return api.get<DeleteImpact>(`/strains/${id}/delete-impact`)
  },
}

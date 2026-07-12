import { api } from './api-client'
import type { DeleteImpact, SpeciesCreate, SpeciesItem, SpeciesUpdate } from './types'

export type SpeciesListResponse = {
  items: SpeciesItem[]
  total: number
}

export const species = {
  list(archived = false, offset = 0, limit = 50) {
    return api.get<SpeciesListResponse>('/species', {
      params: { is_archived: archived, offset, limit },
    })
  },

  create(data: SpeciesCreate) {
    return api.post<SpeciesItem>('/species', data)
  },

  get(id: string) {
    return api.get<SpeciesItem>(`/species/${id}`)
  },

  update(id: string, data: SpeciesUpdate) {
    return api.patch<SpeciesItem>(`/species/${id}`, data)
  },

  archive(id: string) {
    return api.delete(`/species/${id}`)
  },

  getDeleteImpact(id: string) {
    return api.get<DeleteImpact>(`/species/${id}/delete-impact`)
  },

  restore(id: string) {
    return api.post<SpeciesItem>(`/species/${id}/restore`)
  },

  clean(id: string) {
    return api.delete(`/species/${id}/clean`)
  },
}

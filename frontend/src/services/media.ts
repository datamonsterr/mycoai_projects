import { api } from './api-client'
import type { DeleteImpact, MediaCreate, MediaItem, MediaUpdate } from './types'

export type MediaListResponse = {
  items: MediaItem[]
  total: number
}

export const media = {
  list(archived = false, offset = 0, limit = 50) {
    return api.get<MediaListResponse>('/media', {
      params: { is_archived: archived, offset, limit },
    })
  },

  create(data: MediaCreate) {
    return api.post<MediaItem>('/media', data)
  },

  get(id: string) {
    return api.get<MediaItem>(`/media/${id}`)
  },

  update(id: string, data: MediaUpdate) {
    return api.patch<MediaItem>(`/media/${id}`, data)
  },

  archive(id: string) {
    return api.delete(`/media/${id}`)
  },

  getDeleteImpact(id: string) {
    return api.get<DeleteImpact>(`/media/${id}/delete-impact`)
  },

  restore(id: string) {
    return api.post<MediaItem>(`/media/${id}/restore`)
  },

  clean(id: string) {
    return api.delete(`/media/${id}/clean`)
  },
}

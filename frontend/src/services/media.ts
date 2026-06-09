import { api } from './api-client'
import type { MediaCreate, MediaItem, MediaUpdate } from './types'

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
}

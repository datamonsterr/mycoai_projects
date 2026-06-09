import { api } from '@/services/api-client'
import type {
  ImageUploadResponse,
  ImageDetail,
  ImageListResponse,
  SegmentDetail,
} from '@/services/types'

export interface ImageListParams {
  species_id?: string[]
  media_id?: string[]
  status?: string
  search?: string
  include_archived?: boolean
  offset?: number
  limit?: number
}

export function listImages(params?: ImageListParams): Promise<ImageListResponse> {
  const sp = new URLSearchParams()
  sp.set('offset', String(params?.offset ?? 0))
  sp.set('limit', String(params?.limit ?? 50))
  if (params?.include_archived) sp.set('include_archived', 'true')
  if (params?.status) sp.set('status', params.status)
  if (params?.search) sp.set('search', params.search)
  params?.species_id?.forEach((sid) => sp.append('species_id', sid))
  params?.media_id?.forEach((mid) => sp.append('media_id', mid))
  return api.get<ImageListResponse>(`/images?${sp.toString()}`)
}

export function uploadImage(
  image: File,
  strain: string,
  media: string,
  maxColonies?: number,
): Promise<ImageUploadResponse> {
  const formData = new FormData()
  formData.append('image', image)
  formData.append('strain', strain)
  formData.append('media', media)
  if (maxColonies !== undefined) {
    formData.append('max_colonies', String(maxColonies))
  }
  return api.post<ImageUploadResponse>('/images/upload', formData)
}

export function batchUpload(): Promise<{ job_id: string; status: string }> {
  return api.post<{ job_id: string; status: string }>('/images/batch')
}

export function getImage(imageId: string): Promise<ImageDetail> {
  return api.get<ImageDetail>(`/images/${imageId}`)
}

export function deleteImage(imageId: string): Promise<void> {
  return api.delete(`/images/${imageId}`)
}

export function listSegments(imageId: string): Promise<SegmentDetail[]> {
  return api.get<SegmentDetail[]>(`/images/${imageId}/segments`)
}

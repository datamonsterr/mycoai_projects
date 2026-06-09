import { api } from '@/services/api-client'
import type {
  ImageUploadResponse,
  ImageDetail,
  SegmentDetail,
} from '@/services/types'

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

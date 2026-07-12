import { api } from '@/services/api-client'
import type {
  ImageUploadResponse,
  ImageDetail,
  ImageGroupResponse,
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

function imageListSearchParams(params?: ImageListParams) {
  const sp = new URLSearchParams()
  sp.set('offset', String(params?.offset ?? 0))
  sp.set('limit', String(params?.limit ?? 50))
  if (params?.include_archived) sp.set('include_archived', 'true')
  if (params?.status) sp.set('status', params.status)
  if (params?.search) sp.set('search', params.search)
  params?.species_id?.forEach((sid) => sp.append('species_id', sid))
  params?.media_id?.forEach((mid) => sp.append('media_id', mid))
  return sp
}

export function listImages(params?: ImageListParams): Promise<ImageListResponse> {
  return api.get<ImageListResponse>(`/images?${imageListSearchParams(params).toString()}`)
}

export function listImageGroups(params?: ImageListParams): Promise<ImageGroupResponse> {
  return api.get<ImageGroupResponse>(`/images/groups?${imageListSearchParams(params).toString()}`)
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

export type ProgressCount = {
  completed: number
  total: number
  percent: number
}

export type BatchImageStatus = {
  filename: string
  strain: string
  media: string
  species: string
  status: string
  image_id?: string | null
  segments: number
  error?: string | null
  source_url?: string | null
  segment_urls?: string[]
}

export type BatchStrainStatus = {
  strain: string
  confirmed: boolean
  upload: ProgressCount
  segmentation: ProgressCount
  feature_extraction: ProgressCount
}

export type BatchProgress = {
  batch_id: string
  status: string
  batch_name: string
  upload: ProgressCount
  segmentation: ProgressCount
  feature_extraction: ProgressCount
  strains: BatchStrainStatus[]
  images: BatchImageStatus[]
}

export type BatchZipResult = {
  status: string
  batch_id: string
  batch_name: string
  total: number
  successful: number
  failed: number
  results: Array<{
    image_id: string
    strain: string
    media: string
    species: string
    segments: number
    filename: string
    source_url: string
    status?: string
  }>
  errors: Array<{ file: string; error: string }>
  progress: BatchProgress
}

export function uploadBatchZip(
  zipFile: File,
  options?: { defaultMedia?: string; defaultSpecies?: string; method?: string },
): Promise<BatchZipResult> {
  const formData = new FormData()
  formData.append('zipfile', zipFile)
  if (options?.defaultMedia) formData.append('default_media', options.defaultMedia)
  if (options?.defaultSpecies) formData.append('default_species', options.defaultSpecies)
  formData.append('method', options?.method ?? 'yolo')
  return api.post<BatchZipResult>('/images/batch-zip', formData)
}

export function getBatchProgress(batchId: string): Promise<BatchProgress> {
  return api.get<BatchProgress>(`/images/batches/${batchId}/progress`)
}

export function confirmBatchStrain(batchId: string, strain: string): Promise<BatchProgress> {
  return api.post<BatchProgress>(`/images/batches/${batchId}/strains/${encodeURIComponent(strain)}/confirm`, {})
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

export interface AutoSegmentResult {
  image_id: string
  source_url: string
  segments: Array<{
    segment_id: string
    segment_index: number
    bbox: { x: number; y: number; w: number; h: number }
    crop_url: string
    pipeline_url: string
  }>
  segmentation_method: string
}

export interface AutoSegmentRequest {
  method: string
}

export function autoSegment(imageId: string, method: string = 'yolo'): Promise<AutoSegmentResult> {
  return api.post<AutoSegmentResult>(`/images/${imageId}/segment`, { method })
}

export type SegmentPatchRequest = {
  segments: Array<{
    segment_index: number
    bbox: { x: number; y: number; w: number; h: number }
  }>
  deleted_segments: number[]
}

export function patchImageSegments(imageId: string, payload: SegmentPatchRequest): Promise<ImageDetail> {
  return api.patch<ImageDetail>(`/images/${imageId}/segments`, payload)
}

export type ImageMediaUpdateResponse = {
  image_id: string
  media: string
}

export function updateImageMedia(imageId: string, media: string): Promise<ImageMediaUpdateResponse> {
  return api.patch<ImageMediaUpdateResponse>(`/images/${imageId}/media`, { media })
}

export type ImageReindexResponse = {
  image_id: string
  indexed_segments: number
}

export function reindexImage(imageId: string): Promise<ImageReindexResponse> {
  return api.post<ImageReindexResponse>(`/images/${imageId}/reindex`)
}

export type StrainReindexResponse = {
  strain_id: string
  images: number
  indexed_segments: number
}

export function reindexStrainImages(strainId: string): Promise<StrainReindexResponse> {
  return api.post<StrainReindexResponse>(`/images/strains/${strainId}/reindex`)
}

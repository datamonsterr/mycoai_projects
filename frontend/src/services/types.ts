export type UserRole = 'user' | 'owner' | 'dataowner'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RegisterData {
  email: string
  password: string
  name: string
}

export interface LoginData {
  email: string
  password: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}

export interface ImageUploadResponse {
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

export interface SegmentDetail {
  id: string
  image_id: string
  segment_index: number
  crop_path: string
  bbox_x: number
  bbox_y: number
  bbox_w: number
  bbox_h: number
  segmentation_method: string
}

export interface ImageDetail {
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

export interface ImageListItem {
  id: string
  strain_name: string
  species_id: string
  species_name: string
  media_id: string
  media_name: string
  file_path: string
  source_url: string
  angle: string | null
  segments_count: number
  data_update_status: string
  indexed_in_qdrant: boolean
  is_archived: boolean
  created_at: string
}

export interface ImageListResponse {
  items: ImageListItem[]
  total: number
}

export interface RetrievalQueryRequest {
  image_id: string
  k: number
  aggregation: string
  environment_strategy: string
}

export interface RetrievalJobResponse {
  job_id: string
  status: string
  estimated_seconds: number
}

export interface RetrievalNeighbor {
  strain: string
  species: string
  similarity: number
  media: string
  image_thumbnail_url: string
}

export interface RetrievalRanking {
  rank: number
  species: string
  score: number
  neighbors: RetrievalNeighbor[]
}

export interface ThresholdConfidence {
  formula: string
  confidence: number
  threshold: number
  is_known: boolean
}

export interface RetrievalResultsResponse {
  job_id: string
  status: string
  strain: string
  rankings: RetrievalRanking[]
  threshold?: ThresholdConfidence | null
}

export interface SpeciesItem {
  id: string
  name: string
  description: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface SpeciesCreate {
  name: string
  description?: string | null
}

export interface SpeciesUpdate {
  name?: string | null
  description?: string | null
}

export interface MediaItem {
  id: string
  name: string
  description: string | null
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface MediaCreate {
  name: string
  description?: string | null
}

export interface MediaUpdate {
  name?: string | null
  description?: string | null
}

export interface StrainItem {
  id: string
  name: string
  species_id: string
  source: string
  is_archived: boolean
  images: string[]
}

export interface StrainCreateRequest {
  name: string
  species_id: string
  source: string
  images: string[]
}

export type FeedbackType = 'wrong_prediction' | 'issue' | 'contribution'
export type FeedbackStatus = 'pending' | 'accepted' | 'rejected' | 'deferred'

export interface FeedbackCreate {
  retrieval_result_id?: string | null
  feedback_type: FeedbackType
  suggested_species?: string | null
  description: string
  query_strain?: string | null
  image_id?: string | null
  predicted_species?: string | null
}

export interface FeedbackUpdate {
  status: 'accepted' | 'rejected' | 'deferred'
  review_note?: string | null
}

export interface FeedbackResponse {
  id: string
  submitter_id: string
  reviewer_id: string | null
  source: string
  feedback_type: FeedbackType
  query_strain: string | null
  result_id: string | null
  predicted_species: string | null
  suggested_species: string | null
  description: string
  status: FeedbackStatus
  review_note: string | null
  submitted_at: string
  reviewed_at: string | null
}

export interface FeedbackBatchRequest {
  feedback_ids: string[]
  status: 'accepted' | 'rejected' | 'deferred'
  review_note?: string | null
}

export interface DashboardStats {
  total_images: number
  total_strains: number
  total_species: number
  total_media: number
  total_environments?: number
}

export interface DistributionItem {
  species_name?: string
  media_name?: string
  strain_name?: string
  environment_name?: string
  image_count: number
}

export interface TrainingStatus {
  model_name: string
  version: string
  status: string
  deployed_at: string | null
}

export interface TrainingJobItem {
  id: string
  status: string
  started_at: string | null
  completed_at: string | null
}

export interface IndexStatus {
  qdrant_index_status: string
  changes_since_last: Record<string, number>
  external_retraining_recommended: boolean
}

export interface ReindexRequest {
  scope: 'changed' | 'full_active'
}

export interface AdminUserResponse {
  id: string
  email: string
  name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserRoleUpdate {
  role: UserRole
}

export interface UserStatusUpdate {
  is_active: boolean
}

export interface AuditLogResponse {
  id: number
  user_id: string
  action: string
  entity_type: string
  entity_id: string | null
  changes: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface InviteUserResponse {
  user_id: string
  email: string
  invite_token: string
  invite_link: string
}

export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail: string
  instance: string
  errors?: { field: string; message: string }[]
}

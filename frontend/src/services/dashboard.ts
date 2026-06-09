import { api } from '@/services/api-client'
import type { DashboardStats, DistributionItem, IndexStatus } from '@/services/types'

export function getStats(): Promise<DashboardStats> {
  return api.get<DashboardStats>('/dashboard/stats')
}

export function getSpeciesDistribution(): Promise<DistributionItem[]> {
  return api.get<DistributionItem[]>('/dashboard/charts/species-distribution')
}

export function getMediaDistribution(): Promise<DistributionItem[]> {
  return api.get<DistributionItem[]>('/dashboard/charts/media-distribution')
}

export function getTimeline(): Promise<unknown[]> {
  return api.get<unknown[]>('/dashboard/charts/timeline')
}

export function getQdrantStatus(): Promise<IndexStatus> {
  return api.get<IndexStatus>('/dashboard/qdrant-status')
}

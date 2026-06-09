import { useQuery } from '@tanstack/react-query'
import {
  getStats,
  getSpeciesDistribution,
  getMediaDistribution,
  getQdrantStatus,
} from '@/services/dashboard'
import type { DashboardStats, DistributionItem, IndexStatus } from '@/services/types'

export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: getStats,
  })
}

export function useSpeciesDistribution() {
  return useQuery<DistributionItem[]>({
    queryKey: ['dashboard', 'charts', 'species-distribution'],
    queryFn: getSpeciesDistribution,
  })
}

export function useMediaDistribution() {
  return useQuery<DistributionItem[]>({
    queryKey: ['dashboard', 'charts', 'media-distribution'],
    queryFn: getMediaDistribution,
  })
}

export function useQdrantStatus() {
  return useQuery<IndexStatus>({
    queryKey: ['dashboard', 'qdrant-status'],
    queryFn: getQdrantStatus,
  })
}

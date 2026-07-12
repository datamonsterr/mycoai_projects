import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { species } from '@/services/species'
import { media } from '@/services/media'
import { strains } from '@/services/strains'
import type { SpeciesCreate, SpeciesUpdate, MediaCreate, MediaUpdate, StrainCreateRequest } from '@/services/types'

type ArchiveFn = (id: string) => Promise<unknown>

function useArchiveMutation(
  key: string[],
  fn: ArchiveFn,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

function useCreateMutation<TData, TVars>(
  key: string[],
  fn: (data: TVars) => Promise<TData>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

function useUpdateMutation<TData, TVars extends { id: string }>(
  key: string[],
  fn: (id: string, data: Omit<TVars, 'id'>) => Promise<TData>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: TVars) => fn(id, data as Omit<TVars, 'id'>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: key })
    },
  })
}

// ── Species ──

export function useSpeciesList(archived = false, offset = 0, limit = 50) {
  return useQuery({
    queryKey: ['species', { archived, offset, limit }],
    queryFn: () => species.list(archived, offset, limit),
  })
}

export function useCreateSpecies() {
  return useCreateMutation(['species'], (data: SpeciesCreate) => species.create(data))
}

export function useUpdateSpecies() {
  return useUpdateMutation<SpeciesCreate, SpeciesUpdate & { id: string }>(
    ['species'],
    (id, data) => species.update(id, data),
  )
}

export function useArchiveSpecies() {
  return useArchiveMutation(['species'], (id: string) => species.archive(id))
}

export function useRestoreSpecies() {
  return useArchiveMutation(['species'], (id: string) => species.restore(id))
}

export function useCleanSpecies() {
  return useArchiveMutation(['species'], (id: string) => species.clean(id))
}

// ── Media ──

export function useMediaList(archived = false, offset = 0, limit = 50) {
  return useQuery({
    queryKey: ['media', { archived, offset, limit }],
    queryFn: () => media.list(archived, offset, limit),
  })
}

export function useCreateMedia() {
  return useCreateMutation(['media'], (data: MediaCreate) => media.create(data))
}

export function useUpdateMedia() {
  return useUpdateMutation<MediaCreate, MediaUpdate & { id: string }>(
    ['media'],
    (id, data) => media.update(id, data),
  )
}

export function useArchiveMedia() {
  return useArchiveMutation(['media'], (id: string) => media.archive(id))
}

export function useRestoreMedia() {
  return useArchiveMutation(['media'], (id: string) => media.restore(id))
}

export function useCleanMedia() {
  return useArchiveMutation(['media'], (id: string) => media.clean(id))
}

// ── Strains ──

export function useStrainsList(params?: {
  offset?: number
  limit?: number
  species_id?: string
  is_archived?: boolean
  search?: string
}) {
  return useQuery({
    queryKey: ['strains', params],
    queryFn: () => strains.list(params),
  })
}

export function useCreateStrain() {
  return useCreateMutation(['strains'], (data: StrainCreateRequest) => strains.create(data))
}

export function useStrain(id: string) {
  return useQuery({
    queryKey: ['strains', id],
    queryFn: () => strains.get(id),
    enabled: !!id,
  })
}

export function useArchiveStrain() {
  return useArchiveMutation(['strains'], (id: string) => strains.archive(id))
}

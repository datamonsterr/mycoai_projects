import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  uploadImage,
  batchUpload,
  getImage,
  deleteImage,
  listSegments,
  listImages,
} from '@/services/images'
import type { ImageListParams } from '@/services/images'
import { useToast } from '@/hooks/use-toast'

const imagesKeys = {
  all: ['images'] as const,
  detail: (imageId: string) => [...imagesKeys.all, 'detail', imageId] as const,
  segments: (imageId: string) => [...imagesKeys.all, 'segments', imageId] as const,
  list: (params?: ImageListParams) => [...imagesKeys.all, 'list', params] as const,
}

export function useImageUpload() {
  const queryClient = useQueryClient()
  const { success, apiError } = useToast()

  return useMutation({
    mutationFn: ({
      image,
      strain,
      media,
      maxColonies,
    }: {
      image: File
      strain: string
      media: string
      maxColonies?: number
    }) => uploadImage(image, strain, media, maxColonies),
    onSuccess: (data) => {
      success(`Image ${data.image_id} uploaded`)
      queryClient.invalidateQueries({ queryKey: imagesKeys.list() })
    },
    onError: (err) => {
      apiError(err, 'Upload failed')
    },
  })
}

export function useBatchUpload() {
  const queryClient = useQueryClient()
  const { success, apiError } = useToast()

  return useMutation({
    mutationFn: () => batchUpload(),
    onSuccess: () => {
      success('Batch upload started')
      queryClient.invalidateQueries({ queryKey: imagesKeys.list() })
    },
    onError: (err) => {
      apiError(err, 'Batch upload failed')
    },
  })
}

export function useImage(imageId: string) {
  return useQuery({
    queryKey: imagesKeys.detail(imageId),
    queryFn: () => getImage(imageId),
    enabled: !!imageId,
  })
}

export function useDeleteImage() {
  const queryClient = useQueryClient()
  const { success, apiError } = useToast()

  return useMutation({
    mutationFn: (imageId: string) => deleteImage(imageId),
    onSuccess: (_data, imageId) => {
      success(`Image ${imageId} deleted`)
      queryClient.invalidateQueries({ queryKey: imagesKeys.list() })
    },
    onError: (err) => {
      apiError(err, 'Delete failed')
    },
  })
}

export function useSegments(imageId: string) {
  return useQuery({
    queryKey: imagesKeys.segments(imageId),
    queryFn: () => listSegments(imageId),
    enabled: !!imageId,
  })
}

export function useImagesList(params?: ImageListParams) {
  return useQuery({
    queryKey: imagesKeys.list(params),
    queryFn: () => listImages(params),
  })
}

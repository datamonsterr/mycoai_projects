import { toast } from 'sonner'
import { ApiError } from '@/services/api-client'

const toastApi = {
  success: (message: string) => toast.success(message),
  error: (message: string) => toast.error(message),
  apiError: (err: unknown, fallback = 'Something went wrong') => {
    if (err instanceof ApiError) {
      const msg = typeof err.detail === 'string'
        ? err.detail
        : (err.detail as Record<string, string>)?.detail ?? err.message
      toast.error(msg || fallback)
    } else if (err instanceof Error) {
      toast.error(err.message || fallback)
    } else {
      toast.error(fallback)
    }
  },
  info: (message: string) => toast(message),
}

export function useToast() {
  return toastApi
}

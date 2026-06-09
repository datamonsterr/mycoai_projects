import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authService } from '@/services/auth'
import { useToast } from '@/hooks/use-toast'
import type { LoginData, RegisterData, User } from '@/services/types'

export function useLogin() {
  const queryClient = useQueryClient()
  const { apiError } = useToast()

  return useMutation({
    mutationFn: (data: LoginData) => authService.login(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
    onError: (err: Error) => apiError(err, 'Login failed'),
  })
}

export function useRegister() {
  const queryClient = useQueryClient()
  const { apiError } = useToast()

  return useMutation({
    mutationFn: (data: RegisterData) => authService.register(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
    onError: (err: Error) => apiError(err, 'Registration failed'),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => {
      const refreshToken = localStorage.getItem('refresh_token') ?? ''
      return authService.logout(refreshToken)
    },
    onSuccess: () => {
      queryClient.clear()
    },
  })
}

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ['auth', 'me'],
    queryFn: () => authService.me(),
    retry: false,
    staleTime: 5 * 60_000,
  })
}

export function useRefreshToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => {
      const refreshToken = localStorage.getItem('refresh_token') ?? ''
      return authService.refresh(refreshToken)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] })
    },
  })
}

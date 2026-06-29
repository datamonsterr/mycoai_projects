import { api, setToken, clearToken } from './api-client'
import type {
  TokenResponse,
  LoginData,
  RegisterData,
  User,
} from './types'

export const authService = {
  async login(data: LoginData): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>('/auth/login', data)
    setToken(res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    return res
  },

  async register(data: RegisterData): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>('/auth/register', data)
    setToken(res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    return res
  },

  async registerWithToken(data: RegisterData & { token: string }): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>('/auth/register-with-token', data)
    setToken(res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    return res
  },

  async refresh(refreshToken: string): Promise<TokenResponse> {
    const res = await api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
    setToken(res.access_token)
    if (res.refresh_token) {
      localStorage.setItem('refresh_token', res.refresh_token)
    }
    return res
  },

  async logout(refreshToken: string): Promise<void> {
    await api.post('/auth/logout', { refresh_token: refreshToken })
    clearToken()
  },

  async me(): Promise<User> {
    return api.get<User>('/auth/me')
  },
}

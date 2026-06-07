import { createContext } from 'react'
import type { User } from '@/services/types'

export interface AuthState {
  user: User | null
  login: (email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState>({
  user: null,
  login: async () => false,
  logout: async () => {},
})

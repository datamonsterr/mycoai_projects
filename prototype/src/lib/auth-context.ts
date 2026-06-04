import { createContext } from 'react'
import type { Role, UserAccount } from '@/lib/mock-data'

export interface AuthState {
  user: UserAccount | null
  login: (email: string, password: string) => boolean
  logout: () => void
  switchRole: (role: Role) => void
}

export const AuthContext = createContext<AuthState>({
  user: null,
  login: () => false,
  logout: () => {},
  switchRole: () => {},
})

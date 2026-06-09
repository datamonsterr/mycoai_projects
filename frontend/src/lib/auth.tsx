import { useState, useEffect, useCallback, type ReactNode } from 'react'
import type { Role, UserAccount } from '@/lib/mock-data'
import { me, users } from '@/lib/mock-data'
import { AuthContext } from '@/lib/auth-context'

interface MycoAIWindow {
  __mycoai_logout?: () => void
  __mycoai_switchRole?: (role: Role) => void
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserAccount | null>(me)

  const login = (email: string, password: string) => {
    const found = password ? users.find((u) => u.email === email && u.account_status === 'active') : undefined
    if (found) { setUser(found); return true }
    return false
  }

  const logout = useCallback(() => setUser(null), [])

  const switchRole = useCallback((role: Role) => {
    setUser((prev) => prev ? { ...prev, role } : null)
  }, [])

  useEffect(() => {
    const win = window as unknown as MycoAIWindow
    win.__mycoai_logout = logout
    win.__mycoai_switchRole = switchRole
    return () => {
      delete win.__mycoai_logout
      delete win.__mycoai_switchRole
    }
  }, [logout, switchRole])

  return (
    <AuthContext.Provider value={{ user, login, logout, switchRole }}>
      {children}
    </AuthContext.Provider>
  )
}

import { useState, useEffect, type ReactNode } from 'react'
import type { Role, UserAccount } from '@/lib/mock-data'
import { me, users } from '@/lib/mock-data'
import { AuthContext } from '@/lib/auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserAccount | null>(me)

  const login = (email: string, password: string) => {
    const found = password ? users.find((u) => u.email === email && u.account_status === 'active') : undefined
    if (found) { setUser(found); return true }
    return false
  }

  const logout = () => setUser(null)

  const switchRole = (role: Role) => {
    if (!user) return
    setUser({ ...user, role })
  }

  useEffect(() => {
    ;(window as any).__mycoai_logout = logout
    ;(window as any).__mycoai_switchRole = switchRole
    return () => {
      delete (window as any).__mycoai_logout
      delete (window as any).__mycoai_switchRole
    }
  }, [user])

  return (
    <AuthContext.Provider value={{ user, login, logout, switchRole }}>
      {children}
    </AuthContext.Provider>
  )
}

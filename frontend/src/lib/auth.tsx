import { useState, useCallback, useEffect, useSyncExternalStore, type ReactNode } from 'react'
import { authService } from '@/services/auth'
import { clearToken } from '@/services/api-client'
import { AuthContext } from '@/lib/auth-context'
import type { User } from '@/services/types'

function authStore() {
  let user: User | null = null
  let loaded = false
  let snapshot: { user: User | null; loaded: boolean } = { user, loaded }
  const listeners = new Set<() => void>()

  const emit = () => {
    if (snapshot.user !== user || snapshot.loaded !== loaded) {
      snapshot = { user, loaded }
    }
    for (const l of listeners) l()
  }

  return {
    getSnapshot: () => snapshot,
    subscribe: (cb: () => void) => {
      listeners.add(cb)
      return () => { listeners.delete(cb) }
    },
    init: async () => {
      const token = localStorage.getItem('access_token')
      if (!token) {
        loaded = true
        emit()
        return
      }
      try {
        user = await authService.me()
      } catch {
        clearToken()
        user = null
      }
      loaded = true
      emit()
    },
    login: async (email: string, password: string): Promise<boolean> => {
      try {
        await authService.login({ email, password })
        user = await authService.me()
        emit()
        return true
      } catch {
        return false
      }
    },
    logout: async () => {
      try {
        const refreshToken = localStorage.getItem('refresh_token') ?? ''
        await authService.logout(refreshToken)
      } catch { /* ignore */ }
      clearToken()
      user = null
      emit()
    },
  }
}

const store = authStore()

interface MycoAIWindow {
  __mycoai_logout?: () => void
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    store.init().then(() => setReady(true))
  }, [])

  const auth = useSyncExternalStore(store.subscribe, store.getSnapshot)

  const login = useCallback(async (email: string, password: string) => {
    return store.login(email, password)
  }, [])

  const logout = useCallback(async () => {
    return store.logout()
  }, [])

  useEffect(() => {
    const win = window as unknown as MycoAIWindow
    win.__mycoai_logout = () => { store.logout() }
    return () => {
      delete win.__mycoai_logout
    }
  }, [])

  if (!ready) return null

  return (
    <AuthContext.Provider value={{ user: auth.user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

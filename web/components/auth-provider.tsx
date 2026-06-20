"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import { fetchMe } from "@/lib/api"
import { getToken, logout as authLogout } from "@/lib/auth"
import type { AuthUser } from "@/lib/types"

type AuthContextType = {
  user: AuthUser | null
  loading: boolean
  refresh: () => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  refresh: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const profile = await fetchMe()
      setUser({
        id: profile.id,
        email: profile.email,
        display_name: profile.display_name,
        role: profile.role,
      })
    } catch {
      // Ungültiges/abgelaufenes Token: als ausgeloggt behandeln.
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const logout = useCallback(() => {
    setUser(null)
    authLogout()
  }, [])

  const value = useMemo(
    () => ({ user, loading, refresh, logout }),
    [user, loading, refresh, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

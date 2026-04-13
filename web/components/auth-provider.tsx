"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import type { Session, User } from "@supabase/supabase-js"
import { getSessionWithTimeout, supabase } from "@/lib/supabase"

const DEBUG_ENDPOINT = "http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d"
const DEBUG_SESSION_ID = "af5e93"

function debugLog(location: string, message: string, data: Record<string, unknown>) {
  // #region agent log
  fetch(DEBUG_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Debug-Session-Id": DEBUG_SESSION_ID },
    body: JSON.stringify({
      sessionId: DEBUG_SESSION_ID,
      runId: "frontend-round3",
      hypothesisId: "H12",
      location,
      message,
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {})
  // #endregion
}

type AuthContextType = {
  user: User | null
  session: Session | null
  loading: boolean
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(Boolean(supabase))

  useEffect(() => {
    if (!supabase) {
      // #region agent log
      debugLog("web/components/auth-provider.tsx:useEffect", "supabase missing", {})
      // #endregion
      setLoading(false)
      return
    }

    let cancelled = false

    // #region agent log
    debugLog("web/components/auth-provider.tsx:useEffect", "getSession start", {})
    // #endregion
    void getSessionWithTimeout().then((nextSession) => {
      if (cancelled) return
      // #region agent log
      debugLog("web/components/auth-provider.tsx:useEffect", "getSession resolved", {
        hasSession: Boolean(nextSession),
      })
      // #endregion
      setSession(nextSession)
      setUser(nextSession?.user ?? null)
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      // #region agent log
      debugLog("web/components/auth-provider.tsx:onAuthStateChange", "auth state changed", {
        hasSession: Boolean(nextSession),
      })
      // #endregion
      setSession(nextSession)
      setUser(nextSession?.user ?? null)
      setLoading(false)
    })

    return () => {
      cancelled = true
      listener.subscription.unsubscribe()
    }
  }, [])

  const value = useMemo(
    () => ({
      user,
      session,
      loading,
    }),
    [user, session, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

import type {
  Ad,
  AdSearch,
  AIAnalysisLog,
  AppSetting,
  ErrorLog,
  PaginatedAds,
  ScrapeRun,
  UserProfile,
  UserSettings,
} from "./types"
import { supabase } from "./supabase"

// Use relative URL by default so the static export can be served
// from the same origin as the FastAPI backend.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""

export class ApiAuthError extends Error {}

async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getAccessToken()
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}
  const customHeaders = options?.headers ?? {}
  const fullUrl = `${BASE_URL}${path}`
  // #region agent log
  if (typeof fetch !== "undefined") {
    fetch("http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Debug-Session-Id": "ef93ff",
      },
      body: JSON.stringify({
        sessionId: "ef93ff",
        location: "web/lib/api.ts:apiFetch",
        message: "pre_fetch",
        data: {
          hypothesisId: "H1-H3-H-KA",
          fullUrl,
          baseUrlLen: BASE_URL.length,
          path,
          method: options?.method ?? "GET",
          pageOrigin:
            typeof window !== "undefined" ? window.location.origin : "ssr",
          hasAuthHeader: Boolean(token),
        },
        timestamp: Date.now(),
        runId: "pre-fix",
      }),
    }).catch(() => {})
  }
  // #endregion
  let res: Response
  try {
    res = await fetch(fullUrl, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...(customHeaders as Record<string, string>),
      },
      ...options,
    })
  } catch (err: unknown) {
    // #region agent log
    const errInfo =
      err instanceof Error
        ? { name: err.name, message: err.message }
        : { name: "non_error", message: String(err) }
    if (typeof fetch !== "undefined") {
      fetch("http://127.0.0.1:7779/ingest/bfe3bd6e-2abc-4ac9-b804-18a979d98c6d", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Debug-Session-Id": "ef93ff",
        },
        body: JSON.stringify({
          sessionId: "ef93ff",
          location: "web/lib/api.ts:apiFetch",
          message: "fetch_threw",
          data: {
            hypothesisId: "H1-H2-H4-H-KA",
            fullUrl,
            ...errInfo,
            baseUrlLen: BASE_URL.length,
            path,
            pageOrigin:
              typeof window !== "undefined" ? window.location.origin : "ssr",
          },
          timestamp: Date.now(),
          runId: "pre-fix",
        }),
      }).catch(() => {})
    }
    // #endregion
    throw new Error("Keine Verbindung zum Server — bitte Internetverbindung prüfen.")
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    if (res.status === 401) {
      await supabase?.auth.signOut()
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
      throw new ApiAuthError("Sitzung abgelaufen oder ungültig. Bitte erneut einloggen.")
    }
    if (res.status >= 500) {
      throw new Error(body.detail || "Serverfehler — bitte später erneut versuchen.")
    }
    throw new Error(body.detail || `Anfrage fehlgeschlagen (${res.status})`)
  }
  // 204 No Content has no body — do not call res.json()
  if (res.status === 204) return undefined as T
  return res.json()
}

// AdSearches
export const fetchSearches = () => apiFetch<AdSearch[]>("/api/adsearches/")
export const fetchSearch = (id: number) => apiFetch<AdSearch>(`/api/adsearches/${id}`)
export const createSearch = (data: Partial<AdSearch>) =>
  apiFetch<AdSearch>("/api/adsearches/", { method: "POST", body: JSON.stringify(data) })
export const updateSearch = (id: number, data: Partial<AdSearch>) =>
  apiFetch<AdSearch>(`/api/adsearches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteSearch = (id: number) =>
  apiFetch<void>(`/api/adsearches/${id}`, { method: "DELETE" })
export const triggerScrape = (id: number) =>
  apiFetch<{ status: string }>(`/api/adsearches/${id}/scrape`, { method: "POST" })

// Ads
export const fetchAds = async (params?: { adsearch_id?: number; is_analyzed?: boolean }): Promise<Ad[]> => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.is_analyzed !== undefined) searchParams.set("is_analyzed", String(params.is_analyzed))
  searchParams.set("limit", "100")
  const qs = searchParams.toString()
  const res = await apiFetch<PaginatedAds>(`/api/ads/?${qs}`)
  return res.items
}

export const fetchAdsPaginated = (params: {
  adsearch_id?: number
  min_score?: number
  is_analyzed?: boolean
  sort?: string
  limit?: number
  offset?: number
}) => {
  const sp = new URLSearchParams()
  if (params.adsearch_id) sp.set("adsearch_id", String(params.adsearch_id))
  if (params.min_score && params.min_score > 0) sp.set("min_score", String(params.min_score))
  if (params.is_analyzed !== undefined) sp.set("is_analyzed", String(params.is_analyzed))
  if (params.sort) sp.set("sort", params.sort)
  if (params.limit) sp.set("limit", String(params.limit))
  if (params.offset) sp.set("offset", String(params.offset))
  return apiFetch<PaginatedAds>(`/api/ads/?${sp.toString()}`)
}
export const fetchAd = (id: number) => apiFetch<Ad>(`/api/ads/${id}`)
export const deleteAd = (id: number) =>
  apiFetch<void>(`/api/ads/${id}`, { method: "DELETE" })

// ScrapeRuns
export const fetchScrapeRuns = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ScrapeRun[]>(`/api/scraperuns/${qs ? `?${qs}` : ""}`)
}
export const clearScrapeRuns = () =>
  apiFetch<void>("/api/scraperuns/", { method: "DELETE" })

// ErrorLogs
export const fetchErrorLogs = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ErrorLog[]>(`/api/errorlogs/${qs ? `?${qs}` : ""}`)
}
export const clearErrorLogs = () =>
  apiFetch<void>("/api/errorlogs/", { method: "DELETE" })

// AIAnalysisLogs
export const fetchAIAnalysisLogs = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<AIAnalysisLog[]>(`/api/aianalysislogs/${qs ? `?${qs}` : ""}`)
}
export const clearAIAnalysisLogs = () =>
  apiFetch<void>("/api/aianalysislogs/", { method: "DELETE" })

// Settings
export const fetchSettings = () => apiFetch<AppSetting[]>("/api/settings/")
export const fetchSetting = (key: string) => apiFetch<AppSetting>(`/api/settings/${key}`)
export const fetchTelegramConfigured = () =>
  apiFetch<{ configured: boolean }>("/api/settings/telegram-configured")
export const updateSetting = (key: string, value: string) =>
  apiFetch<AppSetting>(`/api/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  })

// Version (from backend / pyproject.toml)
export const fetchVersion = () =>
  apiFetch<{ version: string }>("/api/version/")

// User / Account
export const fetchMe = () => apiFetch<UserProfile>("/api/users/me/")
export const updateMe = (data: { display_name: string }) =>
  apiFetch<UserProfile>("/api/users/me/", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const fetchMySettings = () => apiFetch<UserSettings>("/api/users/me/settings")
export const updateMySettings = (data: Partial<UserSettings>) =>
  apiFetch<UserSettings>("/api/users/me/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const changePassword = (newPassword: string) =>
  apiFetch<void>("/api/users/me/change-password", {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  })
export const deleteMyAccount = () =>
  apiFetch<void>("/api/users/me/", {
    method: "DELETE",
  })

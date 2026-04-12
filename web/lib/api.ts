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

// Leer = gleicher Origin (nur sinnvoll bei Reverse-Proxy); lokal/Vercel: z. B. http://127.0.0.1:8000 bzw. https://api.example.com
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""

export class ApiAuthError extends Error {}

/** FastAPI kann `detail` als String, Array von Validation-Error-Objekten oder Objekt liefern. */
function formatFastApiDetail(detail: unknown): string {
  if (detail == null) return ""
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: unknown }).msg)
      }
      try {
        return JSON.stringify(item)
      } catch {
        return String(item)
      }
    })
    return parts.filter(Boolean).join(" ")
  }
  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail)
    } catch {
      return String(detail)
    }
  }
  return String(detail)
}

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
    const detailText = formatFastApiDetail(
      (body as { detail?: unknown }).detail,
    )
    if (res.status >= 500) {
      throw new Error(
        detailText || "Serverfehler — bitte später erneut versuchen.",
      )
    }
    throw new Error(detailText || `Anfrage fehlgeschlagen (${res.status})`)
  }
  // 204 No Content has no body — do not call res.json()
  if (res.status === 204) return undefined as T
  return res.json()
}

// AdSearches
export const fetchSearches = () => apiFetch<AdSearch[]>("/adsearches/")
export const fetchSearch = (id: number) => apiFetch<AdSearch>(`/adsearches/${id}`)
export const createSearch = (data: Partial<AdSearch>) =>
  apiFetch<AdSearch>("/adsearches/", { method: "POST", body: JSON.stringify(data) })
export const updateSearch = (id: number, data: Partial<AdSearch>) =>
  apiFetch<AdSearch>(`/adsearches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteSearch = (id: number) =>
  apiFetch<void>(`/adsearches/${id}`, { method: "DELETE" })

// Ads
export const fetchAds = async (params?: { adsearch_id?: number; is_analyzed?: boolean }): Promise<Ad[]> => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.is_analyzed !== undefined) searchParams.set("is_analyzed", String(params.is_analyzed))
  searchParams.set("limit", "100")
  const qs = searchParams.toString()
  const res = await apiFetch<PaginatedAds>(`/ads/?${qs}`)
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
  return apiFetch<PaginatedAds>(`/ads/?${sp.toString()}`)
}
export const fetchAd = (id: number) => apiFetch<Ad>(`/ads/${id}`)
export const deleteAd = (id: number) =>
  apiFetch<void>(`/ads/${id}`, { method: "DELETE" })

// ScrapeRuns
export const fetchScrapeRuns = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ScrapeRun[]>(`/scraperuns/${qs ? `?${qs}` : ""}`)
}
export const clearScrapeRuns = () =>
  apiFetch<void>("/scraperuns/", { method: "DELETE" })

// ErrorLogs
export const fetchErrorLogs = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ErrorLog[]>(`/errorlogs/${qs ? `?${qs}` : ""}`)
}
export const clearErrorLogs = () =>
  apiFetch<void>("/errorlogs/", { method: "DELETE" })

// AIAnalysisLogs
export const fetchAIAnalysisLogs = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<AIAnalysisLog[]>(`/aianalysislogs/${qs ? `?${qs}` : ""}`)
}
export const clearAIAnalysisLogs = () =>
  apiFetch<void>("/aianalysislogs/", { method: "DELETE" })

// Settings
export const fetchSettings = () => apiFetch<AppSetting[]>("/settings/")
export const fetchSetting = (key: string) => apiFetch<AppSetting>(`/settings/${key}`)
export const fetchTelegramConfigured = () =>
  apiFetch<{ configured: boolean }>("/settings/telegram-configured")
export const updateSetting = (key: string, value: string) =>
  apiFetch<AppSetting>(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  })

// Version (from backend / pyproject.toml)
export const fetchVersion = () =>
  apiFetch<{ version: string }>("/version/")

// User / Account
export const fetchMe = () => apiFetch<UserProfile>("/users/me/")
export const updateMe = (data: { display_name: string }) =>
  apiFetch<UserProfile>("/users/me/", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const fetchMySettings = () => apiFetch<UserSettings>("/users/me/settings")
export const updateMySettings = (data: Partial<UserSettings>) =>
  apiFetch<UserSettings>("/users/me/settings", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const changePassword = (oldPassword: string, newPassword: string) =>
  apiFetch<void>("/users/me/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
export const deleteMyAccount = (confirmEmail: string) =>
  apiFetch<void>("/users/me/", {
    method: "DELETE",
    body: JSON.stringify({ confirm_email: confirmEmail }),
  })

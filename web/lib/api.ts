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
import { getSessionWithTimeout, supabase } from "./supabase"

// Leer = gleicher Origin (nur sinnvoll bei Reverse-Proxy); lokal/Vercel: z. B. http://127.0.0.1:8000 bzw. https://api.example.com
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""
const API_TIMEOUT_MS = 60000

export class ApiAuthError extends Error {}
export class ApiAbortError extends Error {
  override name = "ApiAbortError" as const
}
let accessTokenInFlight: Promise<string | null> | null = null
const inFlightGetRequests = new Map<string, Promise<unknown>>()

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
  if (!accessTokenInFlight) {
    accessTokenInFlight = getSessionWithTimeout().then((session) => {
      return session?.access_token ?? null
    }).finally(() => {
      accessTokenInFlight = null
    })
  }
  return accessTokenInFlight
}

type SignalOpt = { signal?: AbortSignal }

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? "GET"
  const userSignal = options?.signal
  const fullUrl = `${BASE_URL}${path}`
  // Gleiche GET-URL ohne AbortSignal: ein laufender Request reicht (verhindert Doppel-Requests
  // z. B. bei React Strict Mode oder Refetch, solange der erste noch „pending“ ist). Kein
  // TTL: Bei langsamer API wuerde sonst nach wenigen Sekunden ein zweiter paralleler Call
  // starten und Last/Pool unnötig verdoppeln.
  const dedupeKey =
    method === "GET" && !userSignal && !options?.body ? `${method}:${fullUrl}` : null
  if (dedupeKey) {
    const existing = inFlightGetRequests.get(dedupeKey)
    if (existing) {
      return existing as Promise<T>
    }
  }

  const requestPromise = apiFetchInternal<T>(path, options, fullUrl, userSignal)
  if (dedupeKey) {
    inFlightGetRequests.set(dedupeKey, requestPromise)
    requestPromise.finally(() => {
      inFlightGetRequests.delete(dedupeKey)
    })
  }
  return requestPromise
}

async function apiFetchInternal<T>(
  path: string,
  options: RequestInit | undefined,
  fullUrl: string,
  userSignal: AbortSignal | undefined,
): Promise<T> {
  const token = await getAccessToken()
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}
  const customHeaders = options?.headers ?? {}
  const controller = new AbortController()
  let timedOut = false
  const timeoutId = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, API_TIMEOUT_MS)
  const onAbort = () => controller.abort()
  if (userSignal) {
    if (userSignal.aborted) {
      controller.abort()
    } else {
      userSignal.addEventListener("abort", onAbort, { once: true })
    }
  }
  let res: Response
  try {
    res = await fetch(fullUrl, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...(customHeaders as Record<string, string>),
      },
      signal: controller.signal,
      ...options,
    })
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      if (timedOut) {
        throw new Error("Zeitüberschreitung beim Laden. Bitte erneut versuchen.")
      }
      throw new ApiAbortError("Request abgebrochen")
    }
    throw new Error("Keine Verbindung zum Server — bitte Internetverbindung prüfen.")
  } finally {
    window.clearTimeout(timeoutId)
    if (userSignal) {
      userSignal.removeEventListener("abort", onAbort)
    }
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
export const fetchSearches = (opts?: SignalOpt) => apiFetch<AdSearch[]>("/adsearches/", opts)
export const fetchSearch = (id: number, opts?: SignalOpt) => apiFetch<AdSearch>(`/adsearches/${id}`, opts)
export const createSearch = (data: Partial<AdSearch>) =>
  apiFetch<AdSearch>("/adsearches/", { method: "POST", body: JSON.stringify(data) })
export const updateSearch = (id: number, data: Partial<AdSearch>) =>
  apiFetch<AdSearch>(`/adsearches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteSearch = (id: number) =>
  apiFetch<void>(`/adsearches/${id}`, { method: "DELETE" })

// Ads
export const fetchAds = async (params?: { adsearch_id?: number; is_analyzed?: boolean; signal?: AbortSignal }): Promise<Ad[]> => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.is_analyzed !== undefined) searchParams.set("is_analyzed", String(params.is_analyzed))
  searchParams.set("limit", "100")
  const qs = searchParams.toString()
  const res = await apiFetch<PaginatedAds>(`/ads/?${qs}`, { signal: params?.signal })
  return res.items
}

export const fetchAdsPaginated = (params: {
  adsearch_id?: number
  min_score?: number
  is_analyzed?: boolean
  sort?: string
  limit?: number
  offset?: number
  signal?: AbortSignal
}) => {
  const sp = new URLSearchParams()
  if (params.adsearch_id) sp.set("adsearch_id", String(params.adsearch_id))
  if (params.min_score && params.min_score > 0) sp.set("min_score", String(params.min_score))
  if (params.is_analyzed !== undefined) sp.set("is_analyzed", String(params.is_analyzed))
  if (params.sort) sp.set("sort", params.sort)
  if (params.limit) sp.set("limit", String(params.limit))
  if (params.offset) sp.set("offset", String(params.offset))
  return apiFetch<PaginatedAds>(`/ads/?${sp.toString()}`, { signal: params.signal })
}
export const fetchAd = (id: number, opts?: SignalOpt) => apiFetch<Ad>(`/ads/${id}`, opts)
export const deleteAd = (id: number) =>
  apiFetch<void>(`/ads/${id}`, { method: "DELETE" })

// ScrapeRuns
export const fetchScrapeRuns = (params?: { adsearch_id?: number; limit?: number; signal?: AbortSignal }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ScrapeRun[]>(`/scraperuns/${qs ? `?${qs}` : ""}`, { signal: params?.signal })
}
export const clearScrapeRuns = () =>
  apiFetch<void>("/scraperuns/", { method: "DELETE" })

// ErrorLogs
export const fetchErrorLogs = (params?: { adsearch_id?: number; limit?: number; signal?: AbortSignal }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ErrorLog[]>(`/errorlogs/${qs ? `?${qs}` : ""}`, { signal: params?.signal })
}
export const clearErrorLogs = () =>
  apiFetch<void>("/errorlogs/", { method: "DELETE" })

// AIAnalysisLogs
export const fetchAIAnalysisLogs = (params?: { adsearch_id?: number; limit?: number; signal?: AbortSignal }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<AIAnalysisLog[]>(`/aianalysislogs/${qs ? `?${qs}` : ""}`, { signal: params?.signal })
}
export const clearAIAnalysisLogs = () =>
  apiFetch<void>("/aianalysislogs/", { method: "DELETE" })

// Settings
export const fetchSettings = (opts?: SignalOpt) => apiFetch<AppSetting[]>("/settings/", opts)
export const fetchSetting = (key: string, opts?: SignalOpt) => apiFetch<AppSetting>(`/settings/${key}`, opts)
export const fetchTelegramConfigured = (opts?: SignalOpt) =>
  apiFetch<{ configured: boolean }>("/settings/telegram-configured", opts)
export const updateSetting = (key: string, value: string) =>
  apiFetch<AppSetting>(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  })

// Version (from backend / pyproject.toml)
export const fetchVersion = (opts?: SignalOpt) =>
  apiFetch<{ version: string }>("/version/", opts)

// User / Account
export const fetchMe = (opts?: SignalOpt) => apiFetch<UserProfile>("/users/me/", opts)
export const updateMe = (data: { display_name: string }) =>
  apiFetch<UserProfile>("/users/me/", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const fetchMySettings = (opts?: SignalOpt) => apiFetch<UserSettings>("/users/me/settings", opts)
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

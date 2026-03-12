import type { Ad, AdSearch, AppSetting, ErrorLog, AIAnalysisLog, PaginatedAds, ScrapeRun } from "./types"

// Use relative URL by default so the static export can be served
// from the same origin as the FastAPI backend.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    })
  } catch {
    throw new Error("Keine Verbindung zum Server — bitte Internetverbindung prüfen.")
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
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

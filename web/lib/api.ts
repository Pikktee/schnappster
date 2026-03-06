import type { Ad, AdSearch, AppSetting, ErrorLog, ScrapeRun } from "./types"

// Use relative URL by default so the static export can be served
// from the same origin as the FastAPI backend.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error: ${res.status}`)
  }
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

// Ads
export const fetchAds = (params?: { adsearch_id?: number; is_analyzed?: boolean }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.is_analyzed !== undefined) searchParams.set("is_analyzed", String(params.is_analyzed))
  const qs = searchParams.toString()
  return apiFetch<Ad[]>(`/api/ads/${qs ? `?${qs}` : ""}`)
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

// ErrorLogs
export const fetchErrorLogs = (params?: { adsearch_id?: number; limit?: number }) => {
  const searchParams = new URLSearchParams()
  if (params?.adsearch_id) searchParams.set("adsearch_id", String(params.adsearch_id))
  if (params?.limit) searchParams.set("limit", String(params.limit))
  const qs = searchParams.toString()
  return apiFetch<ErrorLog[]>(`/api/errorlogs/${qs ? `?${qs}` : ""}`)
}

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

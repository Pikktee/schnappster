import type {
  Ad,
  AdminUser,
  AdminUserCreate,
  AdminUserUpdate,
  AdSearch,
  AIAnalysisLog,
  AppSetting,
  Deal,
  DealWatch,
  DealWatchCreate,
  ErrorLog,
  FeedPage,
  GiftWatch,
  GiftWatchCreate,
  GiftWatchUpdate,
  NegotiationMessage,
  Notification,
  PaginatedAds,
  PricePoint,
  PriceWatch,
  PriceWatchCreate,
  PriceWatchPreview,
  ScrapeRun,
  SearchOrder,
  SearchOrderCreate,
  SearchOrderUpdate,
  UserProfile,
  UserSettings,
} from "./types"
import { clearToken, getToken } from "./auth"

// Leer = gleicher Origin (nur sinnvoll bei Reverse-Proxy); lokal/Vercel: z. B. http://127.0.0.1:8000 bzw. https://api.example.com
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""
const API_TIMEOUT_MS = 15000
// Preis-Alarm-Abrufe gehen über Proxy + JS-Rendering (ScrapingAnt) und dauern 15–30s.
const PROXY_FETCH_TIMEOUT_MS = 90000

export class ApiAuthError extends Error {}

/** FastAPI kann `detail` als String, Array von Validation-Error-Objekten oder Objekt liefern. */
export function formatFastApiDetail(detail: unknown): string {
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

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  timeoutMs: number = API_TIMEOUT_MS,
): Promise<T> {
  const token = getToken()
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}
  const customHeaders = options?.headers ?? {}
  const fullUrl = `${BASE_URL}${path}`
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => {
    controller.abort()
  }, timeoutMs)
  const userSignal = options?.signal
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
      throw new Error("Zeitüberschreitung beim Laden. Bitte erneut versuchen.")
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
      clearToken()
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
// KI-Verhandlungsnachricht – kann wie andere KI-Aufrufe länger dauern.
export const generateNegotiationMessage = (id: number) =>
  apiFetch<NegotiationMessage>(
    `/ads/${id}/negotiation-message`,
    { method: "POST" },
    PROXY_FETCH_TIMEOUT_MS,
  )

// PriceWatches (Preis-Alarme)
export const previewPriceWatch = (url: string) =>
  apiFetch<PriceWatchPreview>(
    "/price-watches/preview",
    { method: "POST", body: JSON.stringify({ url }) },
    PROXY_FETCH_TIMEOUT_MS,
  )
export const fetchPriceWatches = () => apiFetch<PriceWatch[]>("/price-watches/")
export const fetchPriceWatch = (id: number) => apiFetch<PriceWatch>(`/price-watches/${id}`)
export const createPriceWatch = (data: PriceWatchCreate) =>
  apiFetch<PriceWatch>(
    "/price-watches/",
    { method: "POST", body: JSON.stringify(data) },
    PROXY_FETCH_TIMEOUT_MS,
  )
export const updatePriceWatch = (id: number, data: Partial<PriceWatch>) =>
  apiFetch<PriceWatch>(`/price-watches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deletePriceWatch = (id: number) =>
  apiFetch<void>(`/price-watches/${id}`, { method: "DELETE" })
export const fetchPriceHistory = (id: number) =>
  apiFetch<PricePoint[]>(`/price-watches/${id}/history`)
export const checkPriceWatchNow = (id: number) =>
  apiFetch<PriceWatch>(
    `/price-watches/${id}/check-now`,
    { method: "POST" },
    PROXY_FETCH_TIMEOUT_MS,
  )

// SearchOrders (vereinheitlichte Suchaufträge über Kleinanzeigen/eBay/MyDealz)
export const fetchSearchOrders = () => apiFetch<SearchOrder[]>("/search-orders/")
export const fetchSearchOrder = (id: number) => apiFetch<SearchOrder>(`/search-orders/${id}`)
export const createSearchOrder = (data: SearchOrderCreate) =>
  apiFetch<SearchOrder>("/search-orders/", { method: "POST", body: JSON.stringify(data) })
export const updateSearchOrder = (id: number, data: SearchOrderUpdate) =>
  apiFetch<SearchOrder>(`/search-orders/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteSearchOrder = (id: number) =>
  apiFetch<void>(`/search-orders/${id}`, { method: "DELETE" })
export const checkSearchOrderNow = (id: number) =>
  apiFetch<SearchOrder>(`/search-orders/${id}/check-now`, { method: "POST" })

// GiftWatches (Fundgrube — Verschenken-Beobachtung mit eigenem Regelwerk)
export const fetchGiftWatches = () => apiFetch<GiftWatch[]>("/gift-watches/")
export const fetchGiftWatch = (id: number) => apiFetch<GiftWatch>(`/gift-watches/${id}`)
export const createGiftWatch = (data: GiftWatchCreate) =>
  apiFetch<GiftWatch>("/gift-watches/", { method: "POST", body: JSON.stringify(data) })
export const updateGiftWatch = (id: number, data: GiftWatchUpdate) =>
  apiFetch<GiftWatch>(`/gift-watches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteGiftWatch = (id: number) =>
  apiFetch<void>(`/gift-watches/${id}`, { method: "DELETE" })
export const checkGiftWatchNow = (id: number) =>
  apiFetch<GiftWatch>(`/gift-watches/${id}/check-now`, { method: "POST" })

// Feed (Ergebnis-Stream der Startseite)
export const fetchFeed = (params: {
  limit?: number
  offset?: number
  source?: string
  min_score?: number
  search_order_id?: number
  sort?: string
}) => {
  const sp = new URLSearchParams()
  if (params.limit) sp.set("limit", String(params.limit))
  if (params.offset) sp.set("offset", String(params.offset))
  if (params.source && params.source !== "all") sp.set("source", params.source)
  if (params.min_score && params.min_score > 0) sp.set("min_score", String(params.min_score))
  if (params.search_order_id) sp.set("search_order_id", String(params.search_order_id))
  if (params.sort && params.sort !== "date") sp.set("sort", params.sort)
  const qs = sp.toString()
  return apiFetch<FeedPage>(`/feed/${qs ? `?${qs}` : ""}`)
}

// DealWatches (Deal-Alarme, MyDealz-Schlagwort-Watcher)
export const previewDealWatch = (query: string) =>
  apiFetch<{ deals: Deal[] }>(
    "/deal-watches/preview",
    { method: "POST", body: JSON.stringify({ query }) },
    PROXY_FETCH_TIMEOUT_MS,
  )
export const fetchDealWatches = () => apiFetch<DealWatch[]>("/deal-watches/")
export const fetchDealWatch = (id: number) => apiFetch<DealWatch>(`/deal-watches/${id}`)
export const fetchDealWatchDeals = (id: number) =>
  apiFetch<Deal[]>(`/deal-watches/${id}/deals`)
export const createDealWatch = (data: DealWatchCreate) =>
  apiFetch<DealWatch>("/deal-watches/", { method: "POST", body: JSON.stringify(data) })
export const updateDealWatch = (id: number, data: Partial<DealWatch>) =>
  apiFetch<DealWatch>(`/deal-watches/${id}`, { method: "PATCH", body: JSON.stringify(data) })
export const deleteDealWatch = (id: number) =>
  apiFetch<void>(`/deal-watches/${id}`, { method: "DELETE" })
export const checkDealWatchNow = (id: number) =>
  apiFetch<DealWatch>(
    `/deal-watches/${id}/check-now`,
    { method: "POST" },
    PROXY_FETCH_TIMEOUT_MS,
  )

// Notifications (In-App-Benachrichtigungen)
export const fetchNotifications = (unreadOnly = false) =>
  apiFetch<Notification[]>(`/notifications/${unreadOnly ? "?unread_only=true" : ""}`)
export const fetchUnreadCount = () =>
  apiFetch<{ count: number }>("/notifications/unread-count")
export const markNotificationsRead = (ids: number[]) =>
  apiFetch<void>("/notifications/mark-read", { method: "POST", body: JSON.stringify({ ids }) })
export const markAllNotificationsRead = () =>
  apiFetch<void>("/notifications/mark-all-read", { method: "POST" })

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

// Admin / Benutzerverwaltung (nur role=admin)
export const fetchUsers = () => apiFetch<AdminUser[]>("/admin/users/")
export const createUser = (data: AdminUserCreate) =>
  apiFetch<AdminUser>("/admin/users/", {
    method: "POST",
    body: JSON.stringify(data),
  })
export const updateUser = (id: string, data: AdminUserUpdate) =>
  apiFetch<AdminUser>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
export const deleteUser = (id: string) =>
  apiFetch<void>(`/admin/users/${id}`, { method: "DELETE" })
export const resetUserPassword = (id: string, newPassword: string) =>
  apiFetch<void>(`/admin/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  })

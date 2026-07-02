export interface AdSearch {
  id: number
  name: string
  /** Quelle/Plattform des Suchauftrags ("kleinanzeigen" | "ebay"). */
  platform: string
  url: string
  /** Keyword-basierte Suche (Alternative zur direkten URL). */
  search_query: string | null
  postal_code: string | null
  radius_km: number | null
  prompt_addition: string | null
  min_price: number | null
  max_price: number | null
  blacklist_keywords: string | null
  is_exclude_images: boolean
  is_active: boolean
  scrape_interval_minutes: number
  created_at: string
  last_scraped_at: string | null
}

export interface Ad {
  id: number
  external_id: string
  title: string
  description: string | null
  price: number | null
  postal_code: string | null
  city: string | null
  url: string
  /** Einzelbild-URL von der API (wird von Backend berechnet). */
  image_url: string | null
  image_urls: string | null
  condition: string | null
  shipping_cost: string | null
  seller_name: string | null
  seller_url: string | null
  seller_rating: number | null
  seller_is_friendly: boolean
  seller_is_reliable: boolean
  seller_type: string | null
  seller_active_since: string | null
  adsearch_id: number
  bargain_score: number | null
  ai_summary: string | null
  ai_reasoning: string | null
  estimated_market_price: number | null
  market_price_confidence: number | null
  price_delta_percent: number | null
  comparison_count: number | null
  comparison_summary: string | null
  is_analyzed: boolean
  first_seen_at: string
}

export interface ScrapeRun {
  id: number
  adsearch_id: number
  started_at: string
  finished_at: string | null
  ads_found: number
  ads_filtered: number
  ads_new: number
}

/** Ein Preis-Alarm: überwacht eine beliebige Webseite auf Preisänderungen. */
export interface PriceWatch {
  id: number
  name: string
  url: string
  currency: string | null
  selected_label: string | null
  scrape_interval_minutes: number
  notify_threshold: number | null
  is_active: boolean
  last_price: number | null
  initial_price: number | null
  last_checked_at: string | null
  last_error: string | null
  created_at: string
}

/** Ein beim Anlegen vorgeschlagener Preis (aus der /preview-Extraktion). */
export interface PriceCandidate {
  value: number
  currency: string | null
  label: string
  source: string
  locator: Record<string, unknown>
  raw: string | null
  context: string | null
  recommended: boolean
}

/** Antwort des /preview-Endpoints. */
export interface PriceWatchPreview {
  title: string | null
  candidates: PriceCandidate[]
}

/** Eingabe zum Anlegen eines Preis-Alarms. */
export interface PriceWatchCreate {
  name?: string
  url: string
  locator: Record<string, unknown>
  currency?: string | null
  selected_label?: string | null
  initial_price?: number | null
  scrape_interval_minutes?: number
  notify_threshold?: number | null
  is_active?: boolean
}

/** Ein Preis-Datenpunkt für den Verlaufsgraphen. */
export interface PricePoint {
  price: number
  currency: string | null
  recorded_at: string
}

/** Eine In-App-Benachrichtigung. */
export interface Notification {
  id: number
  type: string
  title: string
  body: string | null
  link: string | null
  is_read: boolean
  created_at: string
}

export interface ErrorLog {
  id: number
  adsearch_id: number | null
  error_type: string
  message: string
  details: string | null
  created_at: string
}

export interface AIAnalysisLog {
  id: number
  ad_id: number
  adsearch_id: number
  created_at: string
  prompt_text: string
  ad_title: string
  score: number
  ai_summary: string | null
  ai_reasoning: string | null
  estimated_market_price: number | null
  market_price_confidence: number | null
  price_delta_percent: number | null
  comparison_count: number | null
  comparison_summary: string | null
}

export interface PaginatedAds {
  items: Ad[]
  total: number
}

/** KI-generierte Verhandlungsnachricht an den Verkäufer + faires Gegenangebot. */
export interface NegotiationMessage {
  message: string
  suggested_offer: number | null
  reasoning: string | null
}

/** Ein Deal-Alarm: überwacht einen Suchbegriff auf MyDealz auf neue (heiße) Deals. */
export interface DealWatch {
  id: number
  name: string
  query: string
  source: string
  /** Optionale Temperatur-Schwelle (Grad); nur Deals darüber lösen einen Alarm aus. */
  min_temperature: number | null
  scrape_interval_minutes: number
  is_active: boolean
  last_checked_at: string | null
  last_error: string | null
  created_at: string
}

/** Eingabe zum Anlegen eines Deal-Alarms. */
export interface DealWatchCreate {
  name?: string
  query: string
  min_temperature?: number | null
  scrape_interval_minutes?: number
  is_active?: boolean
}

/** Ein auf einem Deal-Alarm gefundener Deal (bzw. Vorschau-Deal). */
export interface Deal {
  id?: number
  external_id: string
  title: string
  url: string
  temperature: number | null
  price: number | null
  next_best_price: number | null
  merchant: string | null
  image_url?: string | null
  published_at?: number | null
  first_seen_at?: string
}

export interface AppSetting {
  key: string
  value: string
}

export interface UserProfile {
  id: string
  email: string | null
  display_name: string
  avatar_url: string | null
  role: string
}

/** Eingeloggter Nutzer im Auth-Context (aus GET /users/me/). */
export interface AuthUser {
  id: string
  email: string | null
  display_name: string
  role: string
}

/** Datensatz in der Admin-Benutzerverwaltung (GET /admin/users/). */
export interface AdminUser {
  id: string
  email: string
  role: string
  is_active: boolean
  display_name: string
  created_at: string
}

export interface AdminUserCreate {
  email: string
  password: string
  role: string
  is_active: boolean
}

export interface AdminUserUpdate {
  is_active?: boolean
  role?: string
}

export interface UserSettings {
  user_id: string
  display_name: string
  telegram_chat_id: string | null
  notify_telegram: boolean
  notify_min_score: number
  notify_price_telegram: boolean
  deletion_pending: boolean
}

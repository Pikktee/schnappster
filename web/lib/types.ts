export interface AdSearch {
  id: number
  name: string
  url: string
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
  is_analyzed: boolean
  first_seen_at: string
}

export interface ScrapeRun {
  id: number
  adsearch_id: number
  started_at: string
  finished_at: string | null
  ads_found: number
  ads_new: number
  status: string
}

export interface ErrorLog {
  id: number
  adsearch_id: number | null
  error_type: string
  message: string
  details: string | null
  created_at: string
}

export interface AppSetting {
  key: string
  value: string
}

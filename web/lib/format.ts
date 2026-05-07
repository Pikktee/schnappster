import { formatDistanceToNow } from "date-fns"
import { de } from "date-fns/locale"

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Noch nie"
  try {
    const normalized = dateStr.includes("+") || dateStr.endsWith("Z") ? dateStr : dateStr + "Z"
    const date = new Date(normalized)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    if (diffMs >= 0 && diffMs < 60 * 1000) return "kürzlich"
    return formatDistanceToNow(date, { addSuffix: true, includeSeconds: true, locale: de })
  } catch {
    return "Unbekannt"
  }
}

export function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "Preis n.v."
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatScore(score: number | null): string {
  if (score === null || score === undefined) return "-"
  return String(Math.round(score))
}

export function getScoreColor(score: number | null): string {
  if (score === null || score === undefined) return "bg-muted text-muted-foreground"
  if (score >= 8) return "bg-emerald-500 text-white"
  if (score >= 6) return "bg-amber-500 text-white"
  return "bg-red-500 text-white"
}

export function getScoreColorText(score: number | null): string {
  if (score === null || score === undefined) return "text-muted-foreground"
  if (score >= 8) return "text-emerald-600"
  if (score >= 6) return "text-amber-600"
  return "text-red-600"
}

export function getSellerRatingLabel(rating: number | null): { label: string; color: string } {
  switch (rating) {
    case 2:
      return { label: "TOP", color: "bg-emerald-100 text-emerald-700 border-emerald-200" }
    case 1:
      return { label: "OK", color: "bg-amber-100 text-amber-700 border-amber-200" }
    case 0:
      return { label: "Na ja", color: "bg-red-100 text-red-700 border-red-200" }
    default:
      return { label: "Unbekannt", color: "bg-muted text-muted-foreground" }
  }
}

export function parseImageUrls(imageUrls: string | null): string[] {
  if (!imageUrls) return []
  return imageUrls.split(",").map((url) => url.trim()).filter(Boolean)
}

/** Liefert alle Bild-URLs einer Anzeige (API sendet image_url, ggf. zukünftig image_urls). */
export function getAdImageUrls(ad: { image_url?: string | null; image_urls?: string | null }): string[] {
  if (ad.image_url) return [ad.image_url]
  return parseImageUrls(ad.image_urls ?? null)
}

/**
 * Formatiert scrape_interval_minutes lesbar: Minuten, Stunden oder Tage.
 * z.B. 30 → "alle 30 Minuten", 60 → "alle 60 Minuten", 360 → "alle 6 Stunden", 1440 → "täglich"
 */
export function formatScrapeInterval(minutes: number): string {
  if (minutes >= 1440 && minutes % 1440 === 0) {
    const days = minutes / 1440
    return days === 1 ? "täglich" : `alle ${days} Tage`
  }
  if (minutes > 60 && minutes % 60 === 0) {
    const hours = minutes / 60
    return hours === 1 ? "alle 1 Stunde" : `alle ${hours} Stunden`
  }
  return minutes === 1 ? "alle 1 Minute" : `alle ${minutes} Minuten`
}

export function formatSearchPriceRange(search: {
  min_price: number | null
  max_price: number | null
}): string {
  if (search.min_price === null && search.max_price === null) return "Alle Preise"
  if (search.min_price !== null && search.max_price !== null) {
    return `${formatPrice(search.min_price)} bis ${formatPrice(search.max_price)}`
  }
  if (search.min_price !== null) return `ab ${formatPrice(search.min_price)}`
  return `bis ${formatPrice(search.max_price)}`
}

export function truncateUrl(url: string, maxLength = 50): string {
  try {
    const parsed = new URL(url)
    const display = parsed.hostname + parsed.pathname
    if (display.length > maxLength) {
      return display.slice(0, maxLength) + "…"
    }
    return display
  } catch {
    return url.length > maxLength ? url.slice(0, maxLength) + "…" : url
  }
}

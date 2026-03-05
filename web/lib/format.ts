import { formatDistanceToNow } from "date-fns"
import { de } from "date-fns/locale"

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Noch nie"
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: de })
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
  return score.toFixed(1).replace(".", ",")
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

export function getStatusInfo(status: string): { label: string; color: string } {
  switch (status) {
    case "completed":
      return { label: "Abgeschlossen", color: "bg-emerald-100 text-emerald-700 border-emerald-200" }
    case "running":
      return { label: "Laeuft", color: "bg-blue-100 text-blue-700 border-blue-200" }
    case "failed":
      return { label: "Fehlgeschlagen", color: "bg-red-100 text-red-700 border-red-200" }
    default:
      return { label: status, color: "bg-muted text-muted-foreground" }
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

export function truncateUrl(url: string, maxLength = 50): string {
  try {
    const parsed = new URL(url)
    const display = parsed.hostname + parsed.pathname
    if (display.length > maxLength) {
      return display.slice(0, maxLength) + "..."
    }
    return display
  } catch {
    return url.length > maxLength ? url.slice(0, maxLength) + "..." : url
  }
}

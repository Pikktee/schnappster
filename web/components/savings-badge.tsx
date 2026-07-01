import { TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

/** Ab dieser Ersparnis (in %) ggü. dem geschätzten Marktwert lohnt sich der Hinweis. */
export const MIN_SAVINGS_PERCENT = 5

interface SavingsBadgeProps {
  /** `price_delta_percent` der Anzeige: positiv = unter Marktwert (= Ersparnis). */
  deltaPercent: number | null | undefined
  size?: "sm" | "md"
  /** "solid" für die Anzeige über Bildern, "soft" für ruhige Flächen. */
  tone?: "solid" | "soft"
  className?: string
}

/**
 * Zeigt die Ersparnis gegenüber dem KI-geschätzten Marktwert als Pille.
 * Rendert nichts, wenn keine belastbare Ersparnis vorliegt – so bleibt das Badge ehrlich.
 */
export function SavingsBadge({ deltaPercent, size = "md", tone = "soft", className }: SavingsBadgeProps) {
  if (deltaPercent == null || deltaPercent < MIN_SAVINGS_PERCENT) return null

  const percent = Math.round(deltaPercent)
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[11px] gap-1" : "px-2.5 py-1 text-xs gap-1.5"
  const toneClasses =
    tone === "solid"
      ? "bg-emerald-600 text-white shadow-sm"
      : "bg-emerald-500/15 text-emerald-600 ring-1 ring-emerald-600/20"

  return (
    <span
      className={cn("inline-flex items-center rounded-full font-semibold", sizeClasses, toneClasses, className)}
      aria-label={`${percent} Prozent unter geschätztem Marktwert`}
    >
      <TrendingDown className={size === "sm" ? "size-3" : "size-3.5"} aria-hidden />
      {percent}% unter Wert
    </span>
  )
}

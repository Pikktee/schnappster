"use client"

import { useState } from "react"
import { ExternalLink, Flame, ImageOff, Zap } from "lucide-react"
import { Card } from "@/components/ui/card"
import type { Deal } from "@/lib/types"
import { formatPrice, timeToHot } from "@/lib/format"
import { cn } from "@/lib/utils"

/** Bis zu dieser Zeit-bis-heiß gilt ein Deal als schneller Aufsteiger (Hervorhebung). */
const FAST_RISER_MINUTES = 120

/** Farbe der Temperatur je Hitze (MyDealz: >300° = heiß, >150° = warm). */
function tempTone(temp: number | null): string {
  if (temp == null) return "bg-muted text-muted-foreground"
  if (temp >= 300) return "bg-red-500/15 text-red-600"
  if (temp >= 150) return "bg-amber-500/15 text-amber-600"
  return "bg-muted text-muted-foreground"
}

export function DealCard({ deal }: { deal: Deal }) {
  const [imageFailed, setImageFailed] = useState(false)
  const showImage = !!deal.image_url && !imageFailed
  const heatSpeed = timeToHot(deal.published_at, deal.hot_date)
  const isFastRiser = heatSpeed != null && heatSpeed.minutes <= FAST_RISER_MINUTES

  return (
    <Card className="group relative flex flex-col gap-0 overflow-hidden p-0 transition-shadow hover:shadow-md">
      <a
        href={deal.url}
        target="_blank"
        rel="noopener noreferrer"
        className="absolute inset-0 z-10 rounded-xl"
        aria-label={`${deal.title} auf MyDealz öffnen`}
      />

      {/* Produktbild mit überlagerter Temperatur */}
      <div className="relative aspect-[4/3] w-full overflow-hidden border-b border-border/60 bg-muted/40">
        {showImage ? (
          // eslint-disable-next-line @next/next/no-img-element -- externe CDN-Bilder, kein Next-Loader
          <img
            src={deal.image_url ?? undefined}
            alt=""
            loading="lazy"
            onError={() => setImageFailed(true)}
            className="size-full object-contain transition-transform duration-200 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-muted-foreground/40">
            <ImageOff className="size-8" aria-hidden />
          </div>
        )}

        <span
          className={cn(
            "absolute left-2 top-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums shadow-sm backdrop-blur-sm",
            tempTone(deal.temperature),
          )}
          title="Community-Temperatur"
        >
          <Flame className="size-3.5" aria-hidden />
          {deal.temperature != null ? `${Math.round(deal.temperature)}°` : "—"}
        </span>
        <ExternalLink
          className="absolute right-2 top-2 size-3.5 text-muted-foreground/50 group-hover:text-muted-foreground"
          aria-hidden
        />

        {heatSpeed && (
          <span
            className={cn(
              "absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium shadow-sm backdrop-blur-sm",
              isFastRiser
                ? "bg-violet-600/90 text-white"
                : "bg-background/80 text-muted-foreground",
            )}
            title={'Aufheiz-Tempo: Zeit von der Veröffentlichung bis „heiß"'}
          >
            <Zap className={cn("size-3", isFastRiser && "fill-current")} aria-hidden />
            {heatSpeed.label}
          </span>
        )}
      </div>

      {/* Titel + Preis */}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3
          className="line-clamp-2 text-sm font-medium leading-snug text-foreground"
          title={deal.title}
        >
          {deal.title}
        </h3>

        <div className="mt-auto flex items-center gap-2 pt-1 text-sm">
          {deal.price != null ? (
            <span className="font-bold text-foreground">{formatPrice(deal.price)}</span>
          ) : (
            <span className="text-xs text-muted-foreground">ohne Preisangabe</span>
          )}
          {deal.next_best_price != null && deal.price != null && (
            <span className="text-xs text-muted-foreground line-through">
              {formatPrice(deal.next_best_price)}
            </span>
          )}
          {deal.merchant && (
            <span className="ml-auto truncate text-xs text-muted-foreground" title={deal.merchant}>
              {deal.merchant}
            </span>
          )}
        </div>
      </div>
    </Card>
  )
}

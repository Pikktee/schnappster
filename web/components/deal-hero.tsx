"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Package, Sparkles, ArrowRight, MapPin } from "lucide-react"
import { Card } from "@/components/ui/card"
import { ScoreBadge } from "@/components/score-badge"
import { SavingsBadge } from "@/components/savings-badge"
import { formatPrice, timeAgo, getAdImageUrls } from "@/lib/format"
import type { Ad } from "@/lib/types"

interface DealHeroProps {
  ad: Ad
}

/**
 * Große "Top-Fund"-Karte oben im Dashboard: hebt das beste aktuelle Schnäppchen hervor.
 * Die ganze Karte ist ein Link auf die Detailseite; die "Ansehen"-Pille ist nur visuell.
 */
export function DealHero({ ad }: DealHeroProps) {
  const images = getAdImageUrls(ad)
  const [imgError, setImgError] = useState(false)
  const hasImage = images.length > 0 && !imgError
  const location = [ad.postal_code, ad.city].filter(Boolean).join(" ")

  return (
    <Card className="group relative overflow-hidden border-primary/20 bg-gradient-to-br from-background via-background to-primary/[0.06] p-0 shadow-sm transition-all hover:shadow-md">
      <Link
        href={`/ads/${ad.id}`}
        className="absolute inset-0 z-10"
        aria-label={`Top-Fund ansehen: ${ad.title}`}
        prefetch={false}
      />
      <div className="flex flex-col sm:flex-row">
        {/* Bild */}
        <div className="relative h-52 w-full shrink-0 overflow-hidden bg-gradient-to-br from-muted/50 to-muted sm:h-auto sm:w-72 sm:min-h-[17rem]">
          {hasImage ? (
            <Image
              src={images[0]}
              alt={ad.title}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-105"
              unoptimized
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <Package className="size-10 text-muted-foreground/40" aria-hidden />
            </div>
          )}
          <div className="absolute top-3 right-3 z-20">
            <ScoreBadge score={ad.bargain_score} size="md" />
          </div>
        </div>

        {/* Inhalt */}
        <div className="flex min-w-0 flex-1 flex-col gap-3 p-5 sm:p-6">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
            <Sparkles className="size-4" aria-hidden />
            Top-Fund
          </div>

          <h2
            className="line-clamp-2 text-lg font-semibold leading-snug tracking-tight text-foreground sm:text-xl"
            title={ad.title}
          >
            {ad.title}
          </h2>

          {ad.ai_summary && (
            <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground" title={ad.ai_summary}>
              {ad.ai_summary}
            </p>
          )}

          <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="text-2xl font-bold text-foreground">{formatPrice(ad.price)}</span>
            <SavingsBadge deltaPercent={ad.price_delta_percent} tone="soft" />
            {ad.estimated_market_price !== null && (
              <span className="text-xs text-muted-foreground">
                Marktwert ~{formatPrice(ad.estimated_market_price)}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
              {location && (
                <>
                  <MapPin className="size-3.5 shrink-0" aria-hidden />
                  <span className="truncate">{location}</span>
                  <span className="text-muted-foreground/40">•</span>
                </>
              )}
              <span className="shrink-0">{timeAgo(ad.first_seen_at)}</span>
            </div>
            <span
              className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground shadow-sm"
              aria-hidden
            >
              Ansehen
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}

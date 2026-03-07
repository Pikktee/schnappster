"use client"

import Link from "next/link"
import Image from "next/image"
import { Package } from "lucide-react"
import type { Ad } from "@/lib/types"
import { formatPrice, timeAgo, getAdImageUrls } from "@/lib/format"
import { ScoreBadge } from "@/components/score-badge"

interface LatestDealsProps {
  ads: Ad[]
}

export function LatestDeals({ ads }: LatestDealsProps) {
  if (ads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Package className="size-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground mt-3">Noch keine Schnäppchen gefunden.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col divide-y divide-border">
      {ads.map((ad) => {
        const images = getAdImageUrls(ad)
        return (
          <Link
            key={ad.id}
            href={`/ads/${ad.id}`}
            className="flex items-center gap-4 py-4 px-2 -mx-2 rounded-lg transition-all hover:bg-accent/50 hover:shadow-sm cursor-pointer group"
            prefetch={false}
          >
            <div className="size-16 rounded-lg bg-muted flex items-center justify-center overflow-hidden shrink-0">
              {images.length > 0 ? (
                <Image
                  src={images[0]}
                  alt={ad.title}
                  width={64}
                  height={64}
                  className="size-full object-cover"
                  unoptimized
                />
              ) : (
                <Package className="size-6 text-muted-foreground/40" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-foreground truncate group-hover:text-primary transition-colors" title={ad.title}>
                {ad.title}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {ad.postal_code} {ad.city} &middot; {timeAgo(ad.first_seen_at)}
              </p>
              {ad.ai_summary && (
                <p className="text-xs text-muted-foreground mt-1 line-clamp-1" title={ad.ai_summary}>{ad.ai_summary}</p>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="font-bold text-foreground text-lg">{formatPrice(ad.price)}</span>
              <ScoreBadge score={ad.bargain_score} size="sm" />
            </div>
          </Link>
        )
      })}
    </div>
  )
}

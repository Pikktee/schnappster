"use client"

import Link from "next/link"
import Image from "next/image"
import { Package, ArrowRight, SearchX } from "lucide-react"
import type { Ad } from "@/lib/types"
import { formatPrice, timeAgo, getAdImageUrls } from "@/lib/format"
import { ScoreBadge } from "@/components/score-badge"
import { Button } from "@/components/ui/button"

interface LatestDealsProps {
  ads: Ad[]
}

export function LatestDeals({ ads }: LatestDealsProps) {
  if (ads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <SearchX className="size-12 text-muted-foreground/50 mb-4" />
        <p className="text-sm font-medium text-foreground">Noch keine Schnäppchen gefunden</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          Sobald deine Suchaufträge aktive Angebote finden, werden die besten Deals hier angezeigt.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col divide-y divide-border/50">
      {ads.map((ad, index) => {
        const images = getAdImageUrls(ad)
        return (
          <Link
            key={ad.id}
            href={`/ads/${ad.id}`}
            className="flex items-center gap-4 py-4 px-3 -mx-3 rounded-xl transition-all hover:bg-accent/40 hover:shadow-sm cursor-pointer group"
            style={{ animationDelay: `${index * 0.05}s` }}
            prefetch={false}
          >
            <div className="size-20 rounded-xl bg-gradient-to-br from-muted to-muted/80 flex items-center justify-center overflow-hidden shrink-0 ring-1 ring-black/5">
              {images.length > 0 ? (
                <Image
                  src={images[0]}
                  alt={ad.title}
                  width={80}
                  height={80}
                  className="size-full object-cover group-hover:scale-105 transition-transform duration-300"
                  unoptimized
                />
              ) : (
                <Package className="size-7 text-muted-foreground/40" />
              )}
            </div>
            <div className="flex-1 min-w-0 flex flex-col gap-1">
              <p className="font-semibold text-foreground truncate" title={ad.title}>
                {ad.title}
              </p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{ad.postal_code} {ad.city}</span>
                <span className="text-muted-foreground/40">•</span>
                <span>{timeAgo(ad.first_seen_at)}</span>
              </div>
              {ad.ai_summary && (
                <p className="text-xs text-muted-foreground line-clamp-1" title={ad.ai_summary}>{ad.ai_summary}</p>
              )}
            </div>
            <div className="flex flex-col items-end gap-2 shrink-0">
              <span className="font-bold text-foreground text-xl">{formatPrice(ad.price)}</span>
              <ScoreBadge score={ad.bargain_score} size="sm" />
            </div>
          </Link>
        )
      })}
      <div className="flex justify-end pt-4 mt-2">
        <Link href="/ads/" className="group">
          <Button variant="ghost" size="sm" className="cursor-pointer group-hover:bg-primary/10">
            Alle Angebote anzeigen
            <ArrowRight className="size-4 ml-1 group-hover:translate-x-0.5 transition-transform" />
          </Button>
        </Link>
      </div>
    </div>
  )
}

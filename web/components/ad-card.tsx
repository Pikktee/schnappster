"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Package, MapPin } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { ScoreBadge } from "@/components/score-badge"
import { SellerRatingTag } from "@/components/seller-rating-tag"
import { formatPrice, timeAgo, getAdImageUrls } from "@/lib/format"
import type { Ad } from "@/lib/types"

interface AdCardProps {
  ad: Ad
}

export function AdCard({ ad }: AdCardProps) {
  const images = getAdImageUrls(ad)
  const [imgError, setImgError] = useState(false)

  return (
    <Card className="group relative transition-all hover:shadow-md hover:-translate-y-1 card-lift cursor-pointer overflow-hidden p-0 flex flex-col">
      <Link href={`/ads/${ad.id}`} className="absolute inset-0 z-10" aria-label={`Details für ${ad.title}`} prefetch={false} />

      {/* Standardized image container with fixed height */}
      <div className="h-48 relative bg-gradient-to-br from-muted/50 to-muted overflow-hidden">
        {images.length > 0 && !imgError ? (
          <Image
            src={images[0]}
            alt={ad.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
            unoptimized
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-primary/5 to-primary/10">
            <div className="size-12 rounded-full bg-white/80 flex items-center justify-center">
              <Package className="size-6 text-primary/60" />
            </div>
          </div>
        )}

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Score badge */}
        <div className="absolute top-2 right-2 z-20">
          <ScoreBadge score={ad.bargain_score} size="sm" />
        </div>

        {/* Image count indicator */}
        {images.length > 1 && (
          <div className="absolute bottom-2 right-2 z-20">
            <span className="text-xs font-medium text-white bg-black/60 px-2 py-0.5 rounded-full">
              +{images.length - 1}
            </span>
          </div>
        )}
      </div>

      <CardContent className="p-4 flex flex-col gap-2.5 flex-1">
        <div className="flex flex-col gap-1.5">
          <h3
            className="font-semibold text-foreground line-clamp-2 leading-snug min-h-[2.5em]"
            title={ad.title}
          >
            {ad.title}
          </h3>

          {ad.ai_summary && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed" title={ad.ai_summary}>
              {ad.ai_summary}
            </p>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-xl font-bold text-foreground">{formatPrice(ad.price)}</span>
          {ad.seller_rating !== null && ad.seller_rating !== undefined && (
            <SellerRatingTag rating={ad.seller_rating} size="sm" />
          )}
        </div>

        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(ad.postal_code + " " + ad.city)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 min-w-0 hover:text-link transition-colors cursor-pointer relative z-20"
            onClick={(e) => e.stopPropagation()}
            title={`Auf Google Maps öffnen: ${ad.postal_code} ${ad.city}`}
          >
            <MapPin className="size-3 shrink-0" />
            <span className="truncate">{ad.postal_code} {ad.city}</span>
          </a>
          <span className="text-muted-foreground/40 shrink-0">•</span>
          <span className="shrink-0">{timeAgo(ad.first_seen_at)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

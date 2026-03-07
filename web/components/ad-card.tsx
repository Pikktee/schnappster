"use client"

import { useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Package } from "lucide-react"
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
    <Card className="group relative transition-all hover:shadow-md hover:-translate-y-0.5 cursor-pointer overflow-hidden p-0">
      <Link href={`/ads/${ad.id}`} className="absolute inset-0 z-10" aria-label={`Details für ${ad.title}`} prefetch={false} />

      <div className="aspect-[4/3] relative bg-muted overflow-hidden">
        {images.length > 0 && !imgError ? (
          <Image
            src={images[0]}
            alt={ad.title}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            unoptimized
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
            <Package className="size-10 text-muted-foreground/30" />
            {imgError && <span className="text-xs text-muted-foreground/50">Bild nicht verfügbar</span>}
          </div>
        )}
        <div className="absolute top-2 right-2 z-20">
          <ScoreBadge score={ad.bargain_score} size="sm" />
        </div>
      </div>

      <CardContent className="p-4 flex flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <h3
            className="font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors"
            title={ad.title}
          >
            {ad.title}
          </h3>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-lg font-bold text-foreground">{formatPrice(ad.price)}</span>
        </div>

        <p className="text-xs text-muted-foreground">
          {ad.postal_code} {ad.city} &middot; {timeAgo(ad.first_seen_at)}
        </p>

        {ad.ai_summary && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed" title={ad.ai_summary}>{ad.ai_summary}</p>
        )}

        {ad.seller_name && (
          <div className="flex items-center gap-2 pt-1">
            <span className="text-xs text-muted-foreground truncate" title={ad.seller_name}>{ad.seller_name}</span>
            <SellerRatingTag rating={ad.seller_rating} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

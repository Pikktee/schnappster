"use client"

import { useEffect, useMemo, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
import Image from "next/image"
import {
  ArrowLeft,
  ExternalLink as ExternalLinkIcon,
  Package,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ShieldCheck,
  User,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScoreBadge } from "@/components/score-badge"
import { SellerRatingTag } from "@/components/seller-rating-tag"
import { ExternalLink } from "@/components/external-link"
import { fetchAd, fetchSearch } from "@/lib/api"
import type { AdSearch } from "@/lib/types"
import {
  formatPrice,
  timeAgo,
  parseImageUrls,
} from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export function AdDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const [id, setId] = useState<number>(NaN)

  useEffect(() => {
    const match = window.location.pathname.match(/\/(\d+)\/?$/)
    if (match) setId(Number(match[1]))
  }, [pathname])

  const [ad, setAd] = useState<Awaited<ReturnType<typeof fetchAd>> | null>(null)
  const [search, setSearch] = useState<AdSearch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentImage, setCurrentImage] = useState(0)
  const [showReasoning, setShowReasoning] = useState(false)

  useEffect(() => {
    if (Number.isNaN(id)) return
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const adData = await fetchAd(id)
        setAd(adData)
        try {
          const searchData = await fetchSearch(adData.adsearch_id)
          setSearch(searchData)
        } catch {
          setSearch(null)
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Anzeige konnte nicht geladen werden."
        setError(msg)
        toast.error(msg)
        setAd(null)
        setSearch(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const images = useMemo(() => parseImageUrls(ad?.image_urls ?? null), [ad])

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-48 lg:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    )
  }

  if (error || !ad) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "Anzeige nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/ads")} className="cursor-pointer">
          Zurueck zur Uebersicht
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push("/ads")} className="cursor-pointer">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1 flex items-center justify-between gap-4 flex-wrap">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{ad.title}</h1>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm" className="cursor-pointer">
              <a href={ad.url} target="_blank" rel="noopener noreferrer">
                <ExternalLinkIcon className="size-3.5" />
                Auf Kleinanzeigen ansehen
              </a>
            </Button>
            {/* Backend hat kein DELETE fuer Ads – Button weggelassen */}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Images + Description */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Image Gallery */}
          <Card className="overflow-hidden p-0">
            <div className="aspect-[16/10] relative bg-muted">
              {images.length > 0 ? (
                <Image
                  src={images[currentImage]}
                  alt={ad.title}
                  fill
                  className="object-contain"
                  unoptimized
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Package className="size-16 text-muted-foreground/30" />
                  <span className="text-muted-foreground text-sm absolute mt-24">Kein Bild verfuegbar</span>
                </div>
              )}
            </div>
            {images.length > 1 && (
              <div className="flex gap-2 p-3 overflow-x-auto">
                {images.map((img, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentImage(i)}
                    className={`size-16 rounded-md overflow-hidden shrink-0 border-2 transition-colors cursor-pointer ${
                      i === currentImage ? "border-primary" : "border-transparent hover:border-muted-foreground/30"
                    }`}
                  >
                    <Image
                      src={img}
                      alt={`Bild ${i + 1}`}
                      width={64}
                      height={64}
                      className="size-full object-cover"
                      unoptimized
                    />
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Price + Details */}
          <Card>
            <CardContent className="flex flex-col gap-4 pt-6">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold text-foreground">{formatPrice(ad.price)}</span>
                {search && (
                  <Badge variant="secondary" className="text-xs">
                    {search.name}
                  </Badge>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                {ad.condition && (
                  <div>
                    <span className="text-muted-foreground">Zustand</span>
                    <p className="mt-0.5 text-foreground">{ad.condition}</p>
                  </div>
                )}
                {ad.shipping_cost && (
                  <div>
                    <span className="text-muted-foreground">Versandkosten</span>
                    <p className="mt-0.5 text-foreground">{ad.shipping_cost}</p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">Standort</span>
                  <p className="mt-0.5 text-foreground">{ad.postal_code} {ad.city}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Gefunden</span>
                  <p className="mt-0.5 text-foreground">{timeAgo(ad.first_seen_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Description */}
          {ad.description && (
            <Card>
              <CardHeader>
                <CardTitle>Beschreibung</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                  {ad.description}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Seller + AI Analysis */}
        <div className="flex flex-col gap-6">
          {/* Seller Box */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="size-4" />
                Verkaeufer
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {ad.seller_name && (
                <div>
                  {ad.seller_url ? (
                    <ExternalLink href={ad.seller_url}>{ad.seller_name}</ExternalLink>
                  ) : (
                    <span className="text-sm font-medium text-foreground">{ad.seller_name}</span>
                  )}
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <SellerRatingTag rating={ad.seller_rating} />
                {ad.seller_is_friendly && (
                  <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                    <ThumbsUp className="size-3" />
                    Freundlich
                  </Badge>
                )}
                {ad.seller_is_reliable && (
                  <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
                    <ShieldCheck className="size-3" />
                    Zuverlaessig
                  </Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground">
                {ad.seller_type && <p>Typ: {ad.seller_type}</p>}
                {ad.seller_active_since && <p>Aktiv seit: {ad.seller_active_since}</p>}
              </div>
            </CardContent>
          </Card>

          {/* AI Analysis */}
          <Card className="border-amber-200 bg-amber-50/50">
            <CardHeader>
              <CardTitle className="text-amber-900">KI-Analyse</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {ad.is_analyzed ? (
                <>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-amber-800">Bargain Score</span>
                    <ScoreBadge score={ad.bargain_score} size="lg" />
                  </div>
                  {ad.ai_summary && (
                    <div>
                      <span className="text-xs text-amber-800 font-medium">Zusammenfassung</span>
                      <p className="text-sm text-amber-900 mt-1 leading-relaxed">{ad.ai_summary}</p>
                    </div>
                  )}
                  {ad.ai_reasoning && (
                    <div>
                      <button
                        onClick={() => setShowReasoning(!showReasoning)}
                        className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 cursor-pointer font-medium transition-colors"
                      >
                        {showReasoning ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
                        Begruendung {showReasoning ? "ausblenden" : "anzeigen"}
                      </button>
                      {showReasoning && (
                        <p className="text-sm text-amber-900 mt-2 leading-relaxed">
                          {ad.ai_reasoning}
                        </p>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-6 text-center">
                  <Package className="size-8 text-amber-400" />
                  <p className="text-sm text-amber-700 mt-2">Noch nicht analysiert</p>
                  <p className="text-xs text-amber-600 mt-1">
                    Diese Anzeige wird beim naechsten Durchlauf analysiert.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
